# Red (Easy) — Lessons Learned

This room ties together four practical skills that show up constantly in real engagements and CTFs:

- Spotting and exploiting **LFI (Local File Inclusion)** signals
- Turning leaked info into credentials via **password mutation rules**
- Using **process monitoring** to catch unintended shells and callbacks
- Understanding the risk of **pkexec** (PwnKit) style local privilege escalation

---

## 1) LFI: the `?page=` parameter is a big signal

### What I noticed
The site uses a pattern like:

- `/index.php?page=home.html`

Whenever you see user-controlled file paths (`page=`, `file=`, `template=`, `include=`), you should immediately test for **LFI**.

### What didn’t work (and why that’s useful)
A direct traversal attempt like `../../../../etc/passwd` failing doesn’t mean “no LFI”.
It often means:

- there’s filtering (e.g., blocking `../`)
- the app is prepending a base directory
- the app is only allowing certain extensions
- the app is normalizing paths

### The key technique: `php://filter` for source + content exfil
A very reliable next step is the PHP filter wrapper:

- `php://filter/convert.base64-encode/resource=...`

Why it matters:
- Even if the response is not directly printed as plain text, base64 encoding lets you safely retrieve it and decode locally.
- This is useful both for reading sensitive files and reading *PHP source* without executing it.

### Practical takeaway
When an LFI looks “partially blocked”, test alternative primitives:

- `php://filter/convert.base64-encode/resource=FILE`
- different traversal depths
- absolute vs relative paths (when possible)
- extension tricks depending on how the include is built

---

## 2) Leaked shell history = attacker gold

### What mattered
Once LFI worked, the fastest path wasn’t exotic exploitation — it was **reading the right files**.

Reading:
- `/etc/passwd` gave valid usernames (`blue`, `red`)
- A user’s `.bash_history` exposed operational behavior (commands run previously)

### Practical takeaway
If you have file read (LFI), prioritize:

- `/etc/passwd` (users)
- `/home/*/.bash_history` (commands / mistakes)
- `/var/www/html/*` (app code, config)
- `.ssh/` (keys, known hosts)
- application config files (`.env`, `config.php`, etc.)

---

## 3) Password mutation rules: don’t brute force blindly

### What happened
History showed use of hashcat rules (`best64.rule`) combined with a base phrase (`.reminder` content like `sup3r_p@s$w0rd!`) to generate a wordlist.

That’s an important real-world lesson:

- Users do not pick random passwords.
- Users start from a base password and apply “mutations” (case flips, suffixes, leetspeak, etc.).

### The real lesson
Brute forcing is much more effective when it’s **targeted**:
- Start with a base secret you found
- Use common mutation rules to generate realistic candidates
- Then test those candidates (SSH, web login, etc.)

### Defensive takeaway
If your “base password” leaks anywhere (notes, reminders, scripts), the attacker can generate thousands of likely variants quickly.
Security controls should assume password *patterns* are predictable.

---

## 4) Process monitoring: `ps aux` can reveal your next pivot

### What mattered
When enumeration stalled, checking running processes exposed something critical:

- a reverse shell running as user `red`, attempting to connect to a hostname (`redrules.thm`) on port `9001`.

This is a powerful reminder: sometimes the box is already configured to call out, and you just need to **catch** it.

### Key idea: hijacking name resolution safely
If a process connects to a hostname you control via attacker-side name resolution (like adding a hosts entry for `redrules.thm`), you can redirect the callback to yourself.

### Practical takeaway checklist
When you get a shell and don’t instantly have a path forward:

- `ps aux` / `ps -ef` — look for odd jobs, scripts, callbacks
- `ss -lntp` — see what’s listening and who owns it
- `crontab -l` and `/etc/crontab` — scheduled execution points

---

## 5) pkexec (PwnKit) privilege escalation: why it’s dangerous

### What happened
The escalation involved a vulnerable `pkexec` binary (CVE-2021-4034), commonly known as **PwnKit**.

### Why this is important
`pkexec` is part of PolicyKit and is often present by default on many Linux distributions. The vulnerability allowed local privilege escalation without needing a password under certain conditions (on unpatched systems).

### The subtle but important detail from the box
The binary wasn’t necessarily in the standard location expected by a public exploit script. You had to adjust the exploit to point at the correct path.

### Practical takeaway
When using public exploits:
- Validate assumptions (paths, versions, architecture)
- Read the exploit and understand what it calls
- Adapt carefully to the environment

### Defensive takeaway
- Patch PolicyKit (`pkexec`) promptly (this vulnerability was widely exploited)
- Reduce local attack surface where possible
- Monitor for suspicious compilation/execution in user-writable locations

---

## 6) Reusable workflow you can apply to future rooms

### If you see `?page=` or any include parameter
- [ ] Try basic traversal
- [ ] If blocked, try `php://filter` base64 trick
- [ ] Use file reads to harvest usernames + history

### If you recover a “base password”
- [ ] Generate mutated candidates (rules-based)
- [ ] Test against the most valuable service (SSH is ideal)

### If you’re stuck after user foothold
- [ ] Check processes (`ps aux`)
- [ ] Check listeners (`ss -lntp`)
- [ ] Check scheduled tasks (cron/systemd timers)

### For root escalation
- [ ] Enumerate SUID binaries and versions
- [ ] Check for known high-impact local vulns (like pkexec on unpatched systems)
- [ ] Adapt exploit assumptions to the target

---

## One-line lesson
File read (LFI) plus human password habits plus poor process hygiene can be enough to own a box — and an unpatched `pkexec` turns “user” into “root” fast.