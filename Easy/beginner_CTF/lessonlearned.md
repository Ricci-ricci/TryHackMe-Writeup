# Beginner CTF (Easy) — Lessons Learned

This room is a great introduction to a real-world attack chain:
**Nmap → default page → robots.txt → CMS version fingerprinting → known exploit → SSH → sudo GTFOBins → root**

---

## 1) The default page is never the final answer

### What happened
Port `80` showed the default Ubuntu/Apache page. A beginner might stop here and assume nothing is running. Instead, directory enumeration revealed hidden endpoints (`/simple`, `/openemr-5_0_1_3`).

### Practical takeaway
A default web page means:
- The real app is likely in a subdirectory
- Directory brute forcing is always worth running
- Check `robots.txt` before investing time in heavy scans

---

## 2) `robots.txt` is a roadmap for attackers

### What happened
`robots.txt` explicitly listed:
- `/openemr-5_0_1_3`
- `/` (disallowed entirely)

This was not hiding anything — it was directly advertising internal paths.

### Why this matters
`robots.txt` is public by design (it's meant for search engine crawlers). Any path listed under `Disallow:` is effectively a list of interesting endpoints from an attacker's perspective.

### Practical takeaway
Always check `/robots.txt` early. It often reveals:
- Admin panels
- Hidden applications
- Internal directory structures
- Version-specific paths (like `/openemr-5_0_1_3` or `/cms-2.2.8`)

**Defense:** Don't use `robots.txt` to "hide" sensitive paths. Use proper access controls instead.

---

## 3) CMS version fingerprinting leads directly to known exploits

### What happened
The `/simple` endpoint revealed a **CMS Made Simple version 2.2.8** installation. Searching for this version online revealed a known SQL injection exploit that could dump usernames, emails, and cracked passwords.

### The pattern
1. Identify the CMS and version
2. Search for known exploits (Exploit-DB, SearchSploit, GitHub)
3. Run the exploit with appropriate parameters
4. Recover credentials

### Practical takeaway
Version numbers in CMS footers, generator meta tags, or URL paths are extremely valuable:
- They immediately narrow down the exploit surface
- Many older CMS versions have public, reliable exploits
- Exploit databases are well-indexed — a version number is often all you need

**Defense:**
- Keep CMS software updated
- Remove version information from public-facing pages
- Use a web application firewall to detect SQLi attempts
- Implement rate limiting on login and search endpoints

---

## 4) SSH on non-standard ports is common

### What happened
SSH was not running on the default port `22` but on port `2222`. A scan that only checks common ports would have missed this entirely.

### Practical takeaway
Always use `-p-` in your Nmap scan to cover all 65535 TCP ports. Non-standard ports are used:
- To avoid casual port scanners
- As a basic obfuscation technique
- In CTFs to add an extra observation step

Connecting to a non-standard SSH port:

```bash
ssh username@<IP_ADDRESS> -p 2222
```

**Defense note:** Moving SSH to a non-standard port reduces automated scan noise but is **not** a security control. Real SSH hardening requires key-based authentication and proper access controls.

---

## 5) `sudo -l` is always the first escalation step

### What happened
After SSH login as the user, checking `sudo -l` revealed that `vim` could be run as root. This is a well-known GTFOBins privilege escalation technique.

### Why vim as sudo = root
`vim` can execute shell commands internally using `:!/bin/sh`. When run as root via `sudo`, this spawns a root shell.

### Practical takeaway
`sudo -l` should be your **first** command after landing on a new user:
- It shows what commands can be run as root
- Many GTFOBins entries correspond to commonly allowed programs
- Even "safe" tools like `vim`, `less`, `find`, `awk` can spawn shells

### Common GTFOBins patterns
- `sudo vim -c ':!/bin/sh'`
- `sudo find . -exec /bin/sh \; -quit`
- `sudo awk 'BEGIN {system("/bin/sh")}'`
- `sudo less /etc/passwd` → press `!` then `/bin/sh`

**Defense:**
- Audit and minimize `sudo` rules (principle of least privilege)
- Never grant sudo access to interactive programs (`vim`, `less`, `more`, `nano`)
- Use `sudoedit` instead of `sudo vim` if file editing is needed
- Regularly review `/etc/sudoers` for overly permissive entries

---

## 6) Reusable checklist for similar rooms

### Discovery
- [ ] Nmap all ports (`-p-`)
- [ ] Check `/robots.txt`
- [ ] Directory brute force
- [ ] Identify CMS/application and version

### Exploitation
- [ ] Search for version-specific exploits
- [ ] Run exploit to recover credentials
- [ ] Try credentials on all available services (SSH, web login)
- [ ] Note non-standard service ports

### Privilege Escalation
- [ ] `sudo -l` immediately
- [ ] Cross-reference with GTFOBins
- [ ] Check SUID binaries, capabilities, cron jobs as fallback

---

## One-line takeaway
Version numbers are free intelligence — find the CMS version, find the exploit, and when you land a shell, `sudo -l` is always your first move.