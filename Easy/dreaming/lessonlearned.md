# Dreaming (Easy) — Lessons Learned

This room is a great example of an “easy” box that still rewards a clean workflow: quick recon, web enumeration, leveraging a known CMS exploit, then escalating through weak operational practices (hardcoded creds, DB access, and unsafe privileged automation).

---

## 1) Default web pages can still hide real apps
Port `80` initially shows the Apache default page, which looks like a dead end. Directory enumeration revealed `/app`, which contained the actual target surface (Pluck CMS).

**Takeaway:** Never trust the first page you see. Always enumerate for:
- hidden apps (`/app`, `/admin`, `/portal`, `/dev`)
- CMS paths and versioned directories
- common admin panels

---

## 2) Enumerate twice: top-level first, then deeper
The first directory brute-force found `/app`. A second scan inside the CMS directory uncovered the important endpoints (notably `admin.php`, `/files`, etc.).

**Takeaway:** Once you find an application directory, re-run enumeration *scoped to that path*. Many apps expose admin panels and upload locations under the app root, not the site root.

---

## 3) Weak credentials are still a real-world foothold
The admin panel accepted a trivial password from a short list of guesses. That immediately changed the game: authenticated admin access on a CMS often equals code execution.

**Takeaway:** Try a small, high-signal password set first (“admin”, “password”, “password123”, case variants). If it works, stop and pivot—don’t waste time brute forcing.

**Defense:** Enforce strong passwords + rate limiting + MFA (where possible) on admin panels.

---

## 4) Versioned CMS + authenticated file upload = predictable RCE
Once Pluck CMS version was known, a public exploit path existed (admin authenticated upload leading to webshell placement). This is a common pattern:
1. Identify CMS + version
2. Search for known exploits
3. Abuse upload / plugin install / theme upload features

**Takeaway:** When you see a known CMS, immediately identify the version and check for:
- authenticated RCE via upload
- insecure plugin/theme installers
- file inclusion issues
- default credentials

**Defense:** Patch, remove unused installers, restrict upload types server-side, store uploads outside the web root.

---

## 5) Shell stability is not optional
After getting a webshell/reverse shell as `www-data`, immediately stabilizing the shell makes post-exploitation faster and safer (less likely to break tooling and command execution).

**Takeaway:** Upgrade your shell early (PTY), then proceed with enumeration.

---

## 6) Post-exploitation: credentials often live in “test” code
From `www-data`, local enumeration found scripts (like `test.py`) containing credentials. Those credentials allowed SSH access as a real user and access to the user flag.

**Takeaway:** Look for:
- `/opt`, `/var/www`, deployment folders
- “test”, “dev”, “backup”, “old” scripts
- hardcoded DB creds, API tokens, SSH passwords

**Defense:** Remove test code from production, use secret managers, and avoid storing plaintext creds in scripts.

---

## 7) Privilege escalation through “data → code” injection (DB-driven execution)
A key escalation was achieved by inserting a crafted record into a database table that was later used by a privileged script. When the script processed the “dream” field, the injected payload caused command execution (e.g., creating a SUID bash for the next user).

**Takeaway:** If you can write to a DB and there is a privileged script reading from that DB, you should consider:
- command injection
- unsafe string concatenation into shell calls
- templating without escaping
- eval-like behavior

**Defense:** Never pass DB data into shell commands without strict validation/escaping. Avoid `os.system()` with untrusted strings.

---

## 8) `sudo -l` is only step one; understand *what* runs and *as whom*
Seeing a script runnable as another user (`sudo -u death ...`) is a clue to inspect:
- what that script reads (files, DB, env vars)
- what it writes (logs, backups)
- whether the data it processes is attacker-controlled

**Takeaway:** Treat “sudo to run a script” as an API surface. The script’s dependencies and data sources are often the exploit.

---

## 9) Python supply-chain style privesc: writable standard libraries are dangerous
The final escalation relied on the fact that a privileged process (cron / automation) imported Python modules from a location writable by a lower-privileged user/group. By modifying a commonly imported module (like `shutil.py`), the attacker gained code execution in the higher-privilege context.

**Takeaway:** If you have write access to files in:
- `/usr/lib/pythonX.Y/`
- `/usr/local/lib/pythonX.Y/`
- or any directory on the Python import path used by privileged jobs  
…you may be able to hijack imports.

**Defense:**
- Ensure system Python libs are owned by `root:root` and not group-writable
- Lock down permissions on site-packages
- Run scheduled jobs with minimal privileges
- Consider virtualenvs with controlled dependencies

---

## 10) Reusable checklist (Dreaming chain)
### Foothold
- [ ] Nmap all ports
- [ ] Web enum (gobuster/dir search)
- [ ] Identify CMS + version
- [ ] Check for default credentials
- [ ] Use known exploit if applicable

### Post-exploitation
- [ ] Stabilize shell (PTY)
- [ ] Enumerate `/opt`, app directories, configs, scripts
- [ ] Extract creds → pivot to SSH

### PrivEsc
- [ ] `sudo -l` and inspect allowed scripts
- [ ] Look for data injection into privileged workflows (DB, files, logs)
- [ ] Check cron/systemd timers
- [ ] Look for writable Python modules on privileged import paths

---

## One-line lesson
Even in “easy” rooms, the fastest path is usually: **enumerate → find a real app → exploit known CMS weakness → pivot with creds → escalate via unsafe automation and writable dependencies**.