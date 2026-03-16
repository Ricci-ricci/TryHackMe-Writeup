# ColdBox (Easy) — Lessons Learned

This room is a good “classic web-to-root” chain:
**enumerate a WordPress site → gain code execution via admin access → pivot to SSH via config creds → escalate with weak sudo rules**.

---

## 1) Don’t ignore “non-standard” ports
The SSH service was not on `22`, it was on `4512`.

**Takeaway:** Always scan full ports and actually try the discovered service. Non-standard ports are common and often intentional.

---

## 2) WordPress enumeration is mostly process, not luck
Once the scan identified **WordPress** (generator header), the next step is systematic enumeration:

- Identify WordPress version (useful for known CVEs, but not always required)
- Enumerate users (`-e u`)
- Enumerate plugins/themes if needed
- Attack authentication if it’s in-scope (common in THM rooms when combined with hints/weak passwords)

**Takeaway:** WordPress is a predictable stack; use a repeatable checklist instead of random guessing.

---

## 3) Getting “admin” on WordPress often equals RCE
With WordPress admin credentials, a common path to code execution is:

- Edit a theme template (often `404.php`, `header.php`, etc.)
- Insert a reverse shell payload
- Trigger the page from the browser
- Catch the callback with a listener

**Why this works:** Theme templates are server-side PHP. If you can edit them in the admin panel and the web server executes them, you’ve effectively gained **remote code execution**.

**Takeaway:** Admin panels are not “just admin pages”—they’re often code execution surfaces if misconfigured or if editing features are enabled.

**Defense notes:**
- Disable file editing in WordPress (`DISALLOW_FILE_EDIT`)
- Restrict admin access (MFA, IP allowlist, strong credentials)
- Keep WordPress core and plugins updated

---

## 4) Pivot to real users using `wp-config.php`
After landing as `www-data`, the best move was reading WordPress configuration:

- `wp-config.php` commonly contains database credentials
- In CTF-style environments, those credentials often get reused for:
  - SSH
  - local user accounts
  - other services

**Takeaway:** The fastest upgrade from a fragile web shell is commonly **SSH**, and WordPress configs are a frequent credential source.

**Defense note:** Avoid credential reuse between DB and system accounts; use secrets management and least-privilege DB accounts.

---

## 5) Privilege escalation is usually “sudo rules + GTFOBins”
Once you had SSH as a real user, `sudo -l` is the most important command.

In this room, sudo permissions allowed running tools like:
- `vim`
- `chmod`
- `ftp`

Some of these are trivially abusable because they can spawn shells or run commands.

Examples of the pattern:
- `vim` running as root can execute shell commands (GTFOBins technique)
- `ftp` can sometimes escape to a shell via `!` (if allowed)
- `chmod` as root is dangerous because it can be used to change permissions on sensitive binaries/files, enabling future escalation

**Takeaway:** If `sudo -l` shows you can run an interactive program as root, assume it’s exploitable and check GTFOBins.

**Defense notes:**
- Do not grant sudo access to interactive programs unless absolutely necessary
- Use `sudo` with explicit command restrictions and safe wrappers
- Review sudo rules for “utility” binaries that can execute commands or alter permissions

---

## 6) Reusable checklist for boxes like this
### Initial access
- [ ] Nmap all ports
- [ ] Identify app stack (WordPress)
- [ ] Enumerate WP users
- [ ] Obtain credentials (brute-force if intended)
- [ ] Use admin to gain RCE (theme edit or upload vector)

### Post-exploitation
- [ ] Read `wp-config.php` for creds
- [ ] Try SSH with discovered creds
- [ ] Stabilize shell (PTY if needed)

### PrivEsc
- [ ] `sudo -l`
- [ ] Map allowed commands to GTFOBins
- [ ] Prefer clean root shell methods over noisy file permission changes

---

## One-line takeaway
WordPress admin access is often “game over” for a host, and sloppy `sudo` rules finish the job.