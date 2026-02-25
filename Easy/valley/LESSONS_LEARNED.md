# Valley — Lessons Learned

This document captures the key skills and takeaways reinforced by the *Valley* (TryHackMe) walkthrough, focusing on principles you can reuse on other boxes and real environments.

---

## 1) Always scan all ports (non-standard ports matter)

- Don’t assume services run on default ports.
- A full TCP scan helps you catch exposed services that would otherwise be missed (e.g., FTP running on an unusual port).

**Habit to build**
- Start with a full port scan (`-p-`) and record results for later reference.

---

## 2) Web enumeration isn’t optional — it’s the entry point

- Hidden directories and “static” content often reveal development artifacts.
- `/static` commonly contains JavaScript, configuration hints, API endpoints, and links to internal/dev pages.

**What to check**
- Directory brute forcing (common wordlists first, then targeted wordlists)
- Page source, linked JS/CSS files, and any “dev” references
- Anything that looks like a staging area (`/dev`, `/test`, `/staging`, `/beta`)

---

## 3) Treat JavaScript like a secrets file

- Developers sometimes embed credentials, tokens, internal endpoints, or comments in client-side code.
- If a login prompt appears for a dev endpoint, reviewing JS is often high value.

**Actionable technique**
- Download and search JS files for: `user`, `pass`, `token`, `key`, `auth`, `api`, `dev`, `test`.

---

## 4) Credential reuse is a pivot strategy (and a real-world risk)

- If you recover a valid credential pair, try it across other exposed services.
- Security notes like “don’t reuse passwords” are often a hint, but also reflect common real-world behavior.

**Safe, systematic approach**
- Try the same creds across: web logins, FTP/SFTP, SSH, SMB, databases (where relevant).

---

## 5) PCAPs are gold: learn to extract credentials from traffic

- Packet captures can contain plaintext credentials, cookies, tokens, and sensitive endpoints.
- HTTP form POSTs can reveal usernames/passwords directly when traffic is unencrypted.

**What to look for in Wireshark**
- Filters: `http`, `http.request.method == "POST"`
- “Follow HTTP Stream” / inspect request bodies
- URL-encoded form fields (`application/x-www-form-urlencoded`)

**Core lesson**
- POST data is not “hidden.” Without TLS, it’s readable to anyone with capture access.

---

## 6) Prefer SSH for a stable foothold after credential recovery

- When SSH is available, it typically provides the cleanest, most stable interactive access compared to web shells or limited services.
- Credential-derived SSH access is often the fastest path to reliable enumeration and escalation.

---

## 7) When `sudo -l` is empty, look for what runs as root automatically

If you can’t escalate via sudo, switch mindset:

- Who/what executes on a schedule?
- What scripts and binaries run under privileged contexts?

**Targets to enumerate**
- Cron jobs / scheduled scripts
- systemd timers and services
- root-owned scripts in unusual directories

---

## 8) Understand the concept behind the privesc: Python module hijacking

- Python executes code at import time.
- If a privileged Python script imports a module from a location you can modify, you can turn an import into code execution as that privileged user.

**Generalizable idea**
- This isn’t “a base64 trick.” It’s an import-path/control problem that can apply to many modules and many languages.

---

## 9) Use fast binary triage before deep reversing

- Tools/techniques like `strings` can reveal:
  - hardcoded credentials
  - hashes
  - internal URLs/endpoints
  - debugging messages

**Workflow tip**
- Start lightweight (`strings`, metadata, permissions), then move to heavier reversing only if needed.

---

## 10) Writeups improve when you record evidence, not just steps

To make your reports more educational (and reproducible), capture:

- The key scan results (ports/service versions)
- The exact discovery path (e.g., `/static` → `/dev`)
- The source of credentials (JS snippet reference, PCAP frame/stream notes)
- Why each move was made (what hypothesis you tested)

**Good standard**
- “Command → Result → Interpretation → Next step”

---