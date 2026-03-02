# TryHackMe — Tokyo Ghoul (Medium) Walkthrough

> Room: **Tokyo Ghoul** (Medium)  
> Goal: Get a foothold, retrieve the user flag, then escalate to root.

This room takes inspiration from the Tokyo Ghoul anime (S1/S2 spoilers). The machine may take a bit of time to fully boot.

---

## 1) Recon (Nmap)

Start with a full TCP scan to identify exposed services:

```/dev/null/nmap.txt#L1-1
nmap -p- -sC -sV -T4 --min-rate=1000 -oN nmap_scan.txt <IP_ADDRESS>
```

### Results (key ports)

From the scan we have 3 open ports:

- `21/tcp` — FTP (`vsftpd 3.0.3`)  
  - Anonymous login is enabled
  - There is a directory named `need_Help?`
- `22/tcp` — SSH (`OpenSSH 7.2p2 Ubuntu`)
- `80/tcp` — HTTP (`Apache 2.4.18`)

**TryHackMe questions covered here**
- **How many ports are open?** → `3` (21, 22, 80)  
- **What OS is likely running?** → Ubuntu/Linux (based on service banners)

---

## 2) Web (Port 80) — identify a hint

Visit:

- `http://<IP_ADDRESS>/`

The room nudges you to look around. Check the page source and you’ll find a hint referencing an HTML file (ex: `jasonroom.html`) which points you toward the FTP service.

---

## 3) FTP (Port 21) — anonymous access

Login with anonymous FTP:

```/dev/null/ftp.txt#L1-3
ftp <IP_ADDRESS>
Name: anonymous
Password: anonymous
```

Browse to the directory shown in the Nmap scripts output (ex: `need_Help?`) and download the available files.

You should find:
- an image (`.jpg`)
- an executable file
- a note that hints you should run the executable

---

## 4) Executable + Stego — extract the hidden data

### 4.1 Quick triage with `strings`
Before running unknown binaries, it’s useful to look for obvious strings:

```/dev/null/strings.txt#L1-1
strings <executable_name>
```

One of the useful strings is a name:

- `kamishiro`

### 4.2 Run the executable (to obtain the passphrase)
Execute it and provide the discovered input (`kamishiro`) when prompted. The program returns a message that acts as the passphrase for the next step.

### 4.3 Extract embedded content from the image (steghide)
Use `steghide` with the image you downloaded:

```/dev/null/steghide.txt#L1-1
steghide extract -sf <image_name>.jpg
```

When prompted for the passphrase, enter the message obtained from running the executable.

This extracts data containing **Morse code**.

---

## 5) Decode chain (Morse → Hex → Base64 → URL path)

Take the extracted Morse code into CyberChef (or decode manually) and apply:

1. Morse Decode → output becomes **hex**
2. From Hex → output becomes **base64**
3. From Base64 → output becomes a web path / endpoint

Final result should be an endpoint like:

- `d1r3c70ry_center`

---

## 6) Web endpoint — Local File Inclusion attempt

Go to:

- `http://<IP_ADDRESS>/d1r3c70ry_center`

There’s an interaction where you can “accept power” or not; either way, the page itself isn’t very helpful. The useful part is the URL behavior: there’s a parameter that loads content, e.g.:

```/dev/null/url.txt#L1-1
?view=gallery.gif
```

This suggests a file include / directory traversal possibility.

### 6.1 Attempt traversal
Try:

```/dev/null/lfi.txt#L1-1
?view=../../../../../../../etc/passwd
```

It responds with a warning like “no no no don’t do that”, which indicates input filtering.

### 6.2 Bypass with URL encoding
URL-encode the traversal sequence (`../`), then retry. With encoding applied, the target returns the contents of `/etc/passwd`.

---

## 7) Crack the discovered hash → SSH

In the `/etc/passwd` output, near the `kamishiro` user entry there is a hash-like value. Save it into `hash.txt` and crack with `john` + `rockyou`:

```/dev/null/john.txt#L1-1
john --wordlist=/usr/share/wordlists/rockyou.txt hash.txt
```

This reveals the SSH password.

---

## 8) SSH login → user flag

SSH in with the recovered creds:

```/dev/null/ssh.txt#L1-1
ssh kamishiro@<IP_ADDRESS>
```

Locate and read the **user flag** (commonly in the user’s home directory).

---

## 9) Privilege escalation — Python jail escape via `sudo`

During local enumeration, you find a Python “jail” script that is runnable as root via `sudo`.

The script structure is roughly:

- prints prompts
- blocks certain keywords (like `eval`, `exec`, `import`, `open`, `os`, `system`, etc.)
- otherwise it executes the provided input

Even though it blocks common dangerous keywords, the filter is shallow (simple substring checks). You can often bypass these by:
- accessing builtins indirectly
- rebuilding blocked words dynamically (e.g., using `.lower()`)

### 9.1 Run the jail with sudo
Run the script the way the sudo rule allows (example path shown in the original notes):

```/dev/null/sudo_jail.txt#L1-1
sudo /usr/bin/python3 /home/kamishiro/jail.py
```

### 9.2 Payload: import `os` and spawn a root shell
Enter this payload inside the jail prompt:

```/dev/null/payload.txt#L1-1
__builtins__.__dict__['__IMPORT__'.lower()]('OS'.lower()).__dict__['SYSTEM'.lower()]('/bin/bash')
```

If successful, this spawns a **root shell**.

---

## 10) Root flag

With the root shell:

- read the root flag (commonly `/root/root.txt`)

---

## Summary (attack chain)

1. Nmap → identify FTP/SSH/HTTP
2. Web source hint → pivot to FTP
3. FTP anonymous → download image + executable + note
4. Executable → obtain stego passphrase
5. `steghide` → extract Morse code
6. Decode Morse → Hex → Base64 → endpoint
7. Endpoint parameter → LFI via URL-encoded traversal → leak `/etc/passwd` + user/hash
8. Crack hash with `john` → SSH access
9. `sudo` Python jail → builtins bypass → root shell
10. Grab flags

---