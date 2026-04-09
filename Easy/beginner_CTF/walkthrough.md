# TryHackMe — Beginner CTF (Easy) Walkthrough

> Room: **Beginner CTF** (Easy)  
> Goal: Follow the guided questions to find the user flag and escalate to root.

This box is a beginner-friendly chain:
**Nmap → web enumeration → robots.txt → CMS detection → SQLi exploit → SSH → sudo GTFOBins privesc**

---

## 1) Recon (Nmap)

Run a full TCP scan with default scripts and version detection:

```/dev/null/nmap.txt#L1-1
nmap -p- -sC -sV -T4 --min-rate=1000 -oN nmap_scan.txt <IP_ADDRESS>
```

### Results (key ports)

- `80/tcp` — HTTP (Apache — default Ubuntu page)
- `2222/tcp` — SSH (non-standard port)

**Takeaway:** SSH is on port `2222`, not the default `22`. Always scan all ports to catch this.

---

## 2) Web enumeration

### 2.1 Check the landing page

Visit:

```/dev/null/visit.txt#L1-1
http://<IP_ADDRESS>/
```

Only the default Apache Ubuntu page is visible — nothing immediately useful.

### 2.2 Check robots.txt

Always check `robots.txt` early — it is designed to hide paths from search engines, which makes it a useful resource for attackers:

```/dev/null/robots.txt#L1-1
http://<IP_ADDRESS>/robots.txt
```

The file contains a `Disallow` entry that reveals a hidden path:

- `/openemr-5_0_1_3`

### 2.3 Directory brute force (Gobuster)

```/dev/null/gobuster.txt#L1-1
gobuster dir -u http://<IP_ADDRESS>/ -w /usr/share/wordlists/dirb/common.txt -t 50
```

Notable discovery:

- `/simple` — a CMS Made Simple installation

---

## 3) Identify the CMS and find an exploit

### 3.1 Access the CMS

Visit:

```/dev/null/cms_visit.txt#L1-1
http://<IP_ADDRESS>/simple/
```

The footer or admin panel typically reveals the version. In this room, the CMS is:

- **CMS Made Simple version 2.2.8**

### 3.2 Search for a known exploit

CMS Made Simple 2.2.8 has a known **SQL injection vulnerability** that can extract credentials.

Search for it:

```/dev/null/searchsploit.txt#L1-1
searchsploit cms made simple 2.2.8
```

You should find a Python exploit script that uses time-based SQL injection to extract:
- username
- email
- password hash (and optionally crack it)

---

## 4) Run the exploit

Use the exploit script with a wordlist to crack the password directly:

```/dev/null/exploit.txt#L1-1
python3 exploit.py -u http://<IP_ADDRESS>/simple/ --crack -w /usr/share/wordlists/rockyou.txt
```

**What the exploit does:**
- Exploits a time-based SQL injection in the CMS
- Extracts username, email, and password hash from the database
- Optionally cracks the hash using the provided wordlist

**Result:** You recover a valid username and plaintext password.

---

## 5) SSH login → user flag

SSH into the target using the recovered credentials (note the non-standard port):

```/dev/null/ssh.txt#L1-1
ssh <USERNAME>@<IP_ADDRESS> -p 2222
```

Retrieve the user flag from the user's home directory.

---

## 6) Privilege escalation to root (sudo + GTFOBins)

Check what the current user can run as root:

```/dev/null/sudo_l.txt#L1-1
sudo -l
```

In this room, `vim` is listed as a sudoable binary.

### 6.1 Escape to root shell via vim

```/dev/null/vim_root.txt#L1-1
sudo vim -c ':!/bin/sh'
```

**Why this works:**
- `vim` is allowed to run as root via `sudo`
- The `-c` flag executes a vim command on startup
- `:!/bin/sh` tells vim to run `/bin/sh` as a shell command
- Since vim is running as root, the spawned shell is also root

Verify:

```/dev/null/verify_root.txt#L1-2
whoami
id
```

Retrieve the root flag from `/root/root.txt`.

---

## Summary (attack chain)

1. Nmap → find HTTP on `80` and SSH on port `2222`
2. `robots.txt` → reveals hidden path `/openemr-5_0_1_3`
3. Gobuster → discovers `/simple` (CMS Made Simple)
4. Identify version `2.2.8` → find SQLi exploit
5. Run exploit with rockyou wordlist → recover credentials
6. SSH on port `2222` → user flag
7. `sudo -l` → `vim` allowed → `sudo vim -c ':!/bin/sh'` → root shell → root flag

---

## Notes / Defensive takeaways

- `robots.txt` should not be used to hide sensitive paths from attackers — it's publicly readable.
- Keep CMS software patched and updated; version 2.2.8 had a known critical SQLi vulnerability.
- Avoid exposing SSH on non-standard ports as a security measure — it provides obscurity, not security.
- Never grant sudo access to interactive programs like `vim`, `less`, `nano` — they can all spawn shells.
- Use GTFOBins as a reference for what not to put in sudoers rules.