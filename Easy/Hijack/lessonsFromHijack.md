# Hijack - Mission Briefing & Analysis

**Target:** `Hijack` (Linux Box)
**Objective:** Compromise the web server, pivot to a user, and escalate privileges to root.
**Key Techniques:** NFS Enumeration, ID Spoofing, Session Hijacking (Cookie Forging), Command Injection, Library Hijacking (`LD_LIBRARY_PATH`).

---

### The Attack Chain

#### 1. Reconnaissance & Enumeration
*   **Port Scan:** Nmap identified standard services (FTP, SSH, HTTP) and significantly, NFS (Network File System) on port 2049.
*   **NFS Enumeration:** Using `showmount`, a share `/mnt/share` was discovered.
*   **ID Spoofing:** Accessing the share revealed files owned by a specific User ID (UID 1003). By creating a local user with the matching UID (`sudo useradd -u 1003`), we bypassed file permission restrictions to read sensitive data.

#### 2. Information Gathering
*   **FTP Credentials:** The NFS share contained credentials for the FTP service.
*   **Sensitive Data Exposure:** Inside the FTP server, two critical files were found: a message from the admin (`from_admin.txt`) hinting at password policies, and a wordlist (`password.txt`).

#### 3. Initial Access (Web)
*   **Session Analysis:** The web application used a custom, insecure session management mechanism. The cookie was generated using `Base64(username:MD5(password))`.
*   **Session Hijacking:** Instead of brute-forcing the login form (which had rate limiting), we essentially brute-forced the *session cookie*. A Python script was written to generate valid cookies for the `admin` user using the passwords found in the FTP share until access was granted.
*   **Command Injection:** The administration panel had a "Service Status" feature. This input was not sanitized, allowing for command injection (e.g., `command && reverse_shell`) to gain a shell as `www-data`.

#### 4. Lateral Movement & Privilege Escalation
*   **Config Analysis:** Enumerating the web root revealed `config.php` containing hardcoded credentials for the user `rick`.
*   **SSH Access:** These credentials allowed SSH access as `rick`.
*   **Sudo Misconfiguration:** `sudo -l` revealed `rick` could run Apache2 with specific environment variables set.
*   **Library Hijacking:** The sudo entry allowed setting `LD_LIBRARY_PATH`. We compiled a malicious shared object (`.so`) file that executes a shell, pointed `LD_LIBRARY_PATH` to its location, and executed Apache. This forced Apache to load our malicious library as root, granting a root shell.

---

### Lessons Learned & Security Concepts

This box demonstrates how a chain of seemingly minor misconfigurations can lead to full system compromise.

#### 1. NFS Access Control Vulnerabilities
*   **The Flaw:** The NFS share was exported with weak permissions, relying only on UID matching for security.
*   **The Concept:** NFS often trusts the client machine's user IDs. If `root_squash` is not enabled or if specific users are targeted, an attacker can simply create a user on their *own* machine with the target UID to impersonate the file owner.
*   **Fix:** Restrict NFS exports to specific IP addresses. Use `root_squash` (usually default) and consider Kerberos authentication for NFS (NFSv4) to validate user identity beyond simple UIDs.

#### 2. "Roll Your Own" Crypto/Session Management
*   **The Flaw:** The developer created a custom session cookie format (`Base64(User:MD5(Pass))`) instead of using standard, random session IDs (like PHPSESSID handled by PHP natively).
*   **The Concept:** Security through obscurity fails. Once the pattern is identified, the session token becomes predictable. If an attacker has a list of potential passwords, they can generate valid tokens offline without interacting with the login form, bypassing lockouts and rate limits.
*   **Fix:** Always use established libraries and frameworks for session management. Use high-entropy, random strings for session tokens.

#### 3. Command Injection via Unsanitized Input
*   **The Flaw:** The administration panel took user input and passed it directly to a system shell command (likely using `exec()` or `system()`) without sanitization.
*   **The Concept:** If an application constructs a system command using user input, an attacker can append their own commands using delimiters like `&&`, `;`, or `|`.
*   **Fix:** Avoid making system calls if possible. If necessary, use functions that separate the command from arguments (like `subprocess.run` in Python with `shell=False`) or strictly validate/sanitize input against an allowlist.

#### 4. Environment Variable Injection (LD_LIBRARY_PATH)
*   **The Flaw:** The `sudo` configuration preserved the `LD_LIBRARY_PATH` environment variable or allowed the user to set it while running a command as root.
*   **The Concept:** `LD_LIBRARY_PATH` tells the dynamic linker where to look for shared libraries *before* looking in standard system locations. By setting this to a folder like `/tmp` and placing a malicious library there (e.g., hijacking a library Apache needs), the program executes the attacker's code with root privileges upon startup.
*   **Fix:** When configuring `sudo` (via `visudo`), use `env_reset` to clear environment variables. explicitly prevent `LD_LIBRARY_PATH` from being preserved or set (`env_keep`). Never allow `SETENV` tag for commands unless absolutely necessary and strictly scoped.
