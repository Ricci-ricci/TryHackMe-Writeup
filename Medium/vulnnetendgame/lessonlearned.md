# VulnNet: Endgame (Medium) — Lessons Learned

This room is a good reminder that “medium” difficulty often means **multiple realistic steps chained together**, not a single hard exploit:

**Subdomain enum → API SQLi → credential reuse/wordlists → admin CMS access → file upload RCE → local credential recovery → capabilities-based privilege escalation**

---

## 1) When the website “requires a domain”, fix name resolution early

### What mattered
The web app is meant to be accessed through `vulnnet.thm` (and later subdomains). If you don’t add the hostnames to `/etc/hosts` (or otherwise resolve them), you’ll waste time chasing “broken” pages.

### Practical takeaway
- Any mention like “available through `something.thm`” means: map the target IP to that hostname.
- Do it immediately so your tools (browser, scanners) behave like the intended environment.

---

## 2) If directory brute forcing fails, pivot to **subdomain enumeration**

### What happened
A normal directory scan against the main site didn’t reveal much. The real entry points were hidden behind subdomains:

- `blog.vulnnet.thm`
- `api.vulnnet.thm`
- `admin1.vulnnet.thm`

### Practical takeaway
For web targets, enumeration isn’t only “directories”; it’s also:
- subdomains
- virtual hosts
- alternate hostnames referenced by the app (JS/API calls)

If content looks thin, assume the real app could be a different vhost.

---

## 3) Watch how the front-end talks to the back-end (API calls reveal attack surface)

### What mattered
The `blog` site made requests into the `api` host using a parameter that controlled data retrieval. That’s a huge hint:

- user-controlled parameter
- backend data fetch
- likely database access

### Practical takeaway
When you see an API request pattern like:
- `/fetch/?something=...`

Treat it as potential injection territory:
- SQLi
- NoSQL injection
- IDOR
- SSRF (depending on functionality)

---

## 4) SQL injection isn’t the “end” — it’s a **credential factory**

### What happened
The SQLi allowed dumping tables from the backend, including user tables (e.g., `be_users`). That provided:

- usernames
- password hashes (and sometimes plaintext passwords)

### Practical takeaway
Don’t just dump everything blindly. Prioritize:
- authentication tables
- admin/back-end user tables
- API keys / tokens
- configuration tables

From an attacker workflow perspective, SQLi is often best used to obtain:
- an admin session
- creds that unlock a new interface (CMS / SSH)

---

## 5) Offline cracking strategy: use **contextual wordlists**, not only rockyou

### What happened
You obtained an Argon2 hash (stronger than older hashes). Instead of starting with huge lists, you used **data extracted from the system** (blog passwords) as a targeted wordlist.

### Practical takeaway
When cracking strong hashes:
- Don’t start with “everything”
- Start with “likely”:
  - passwords found elsewhere in the dump
  - project-specific terms (room name, domain name, company name)
  - user naming conventions
  - previously leaked creds

This is faster, more realistic, and often the intended path.

---

## 6) CMS admin access: the fastest route to RCE is often **upload features**

### What mattered
Once logged into the CMS (TYPO3 in this case), the objective becomes:
- “How do I get server-side code execution?”

A common path:
- upload a webshell / PHP payload
- bypass or relax extension restrictions
- locate the uploaded file under a web-accessible directory

### Practical takeaway
In CMS environments, check for:
- file upload managers
- extension/plugin installation
- theme/templates editors
- misconfigured allowed extensions
- paths like `/fileadmin/`, `/uploads/`, `/media/`

If uploads exist, always ask:
- Can I upload executable content (PHP, phar, phtml)?
- If not, can I change the allow list?
- Is the upload stored under the web root?

---

## 7) Post-exploitation: browsers are credential stores (Firefox profile = secrets)

### What happened
After getting a low-priv shell (`www-data`), you found a user home with a Firefox profile (`.mozilla`). Extracting that profile allowed recovering saved credentials using a decryptor tool.

### Practical takeaway (offense)
When you have local access, consider:
- `.mozilla/firefox/*`
- `~/.config/google-chrome/` / `~/.config/chromium/`
- password managers / keyrings (depending on environment)

Browser profiles regularly contain:
- saved web passwords
- session cookies
- usernames and internal URLs

### Practical takeaway (defense)
- Avoid saving privileged passwords in browsers on servers.
- Lock down home directory permissions.
- Use centralized secrets management where possible.
- Minimize interactive browsing on production hosts.

---

## 8) Privilege escalation: Linux capabilities can be as dangerous as SUID

### What happened
Enumeration showed an `openssl` binary with capabilities (e.g., `cap_*ep`). Capabilities can grant privileges without full root, and some combinations effectively allow root-impact operations.

### The lesson
When `sudo -l` is empty and no obvious SUID path exists, check:
- capabilities (`getcap -r / 2>/dev/null`)
- cron/timers
- writable service files
- exposed internal tools under user directories

Capabilities can create “weird” but powerful privilege boundaries. If a tool can:
- write to sensitive files
- read restricted files
- bind privileged ports
- act with elevated filesystem permissions

…it can become a privesc vector.

---

## 9) “Data → code” transitions are where escalations happen

Across the box, the theme is repeated:
- Input parameter (`blog`) → SQL query → data leak → creds
- CMS settings → upload policy → executable file upload → RCE
- Capability-enabled binary → file manipulation → privilege boundary crossed

### Practical takeaway
At every step ask:
- What **new capability** did this unlock?
- Does it let me affect authentication (passwords/tokens)?
- Does it let me write to a privileged location?
- Does it run as another user / root?

---

## 10) Reusable checklist (VulnNet style boxes)

### Web / discovery
- [ ] Add required hostnames to `/etc/hosts`
- [ ] Directory enumeration
- [ ] Subdomain / vhost enumeration
- [ ] Observe API calls and parameters

### Exploitation
- [ ] Test API parameters for injection
- [ ] Dump only high-value tables first (users/tokens/config)
- [ ] Use recovered data to build targeted wordlists
- [ ] Authenticate to admin panels and find upload/code execution paths

### Post-exploitation & privesc
- [ ] Harvest local creds (configs, history, browser profiles)
- [ ] Check `sudo -l`, SUID, capabilities, cron/systemd timers
- [ ] If a binary has capabilities, treat it as a first-class privesc lead

---

## One-line takeaway
When a box exposes an API and a CMS, your fastest win is often: **enumerate subdomains → SQLi for creds → admin access → CMS upload RCE → privesc via “weird” local privileges like Linux capabilities**.