# Lessons Learned: Team Box

This document summarizes the key security concepts and vulnerabilities encountered while exploiting the "Team" box on TryHackMe.

## 1. Web Enumeration is Critical
*   **Fuzzing Extensions:** Standard directory brute-forcing often misses backup files. Using tools like `ffuf` to specifically look for extensions like `.old`, `.bak`, or `.php` is crucial. In this box, finding `script.old` provided the initial foothold.
*   **Virtual Host Routing:** Always check for subdomains and add them to `/etc/hosts`. Many CTF boxes (and real-world applications) route traffic based on the Host header.

## 2. Local File Inclusion (LFI)
*   **Parameter Tampering:** The `page=` parameter in the URL was vulnerable to directory traversal (`../../`).
*   **Impact:** LFI is not just about reading `/etc/passwd`. It can be used to:
    *   Enumerate users on the system.
    *   Read configuration files (Apache, SSH).
    *   Steal SSH keys (id_rsa), leading to direct shell access.
    *   Potentially escalate to Remote Code Execution (RCE) via log poisoning (though not used here).

## 3. SSH Key Hygiene
*   **Formatting Matters:** SSH keys are extremely sensitive to whitespace and line breaks. Copy-pasting from a browser or terminal often corrupts them. Knowing how to repair a PEM-formatted key (headers, 64-char line width, proper newlines) is a valuable skill.
*   **Permissions:** SSH clients will refuse to use a private key if it is too "open". Always run `chmod 600 keyfile` before attempting to connect.

## 4. Linux Privilege Escalation
*   **Sudo Misconfiguration:** The user `gyles` could run a specific script as `admin` without a password.
*   **Input Handling in Scripts:** The `admin_checks` script took user input and executed it directly as a command (`$error`). This is a classic command injection vulnerability. Always sanitize input in bash scripts.
*   **Cron Jobs:**
    *   **Enumeration:** Identifying scripts that run automatically (via `pspy` or checking `/etc/crontab` and `/etc/cron.d`) provides a path to escalation.
    *   **Permissions:** If a cron job runs as root but executes a script that a lower-privileged user can write to (`main_script.sh`), that user effectively has root privileges.

## Summary Checklist for Future Boxes
- [ ] Did I fuzz for backup file extensions?
- [ ] Did I check `/etc/hosts` for subdomains?
- [ ] Did I check LFI parameters for sensitive files (`id_rsa`, `user.txt`, `config.php`)?
- [ ] Did I check `sudo -l` immediately upon gaining access?
- [ ] Are there any writable scripts being executed by root cron jobs?