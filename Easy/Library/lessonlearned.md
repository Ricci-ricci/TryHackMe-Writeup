# Lessons Learned - Library

## 1. Thorough Enumeration Pays Off
The initial foothold was entirely dependent on careful reading of the web content. Tools like `nmap` and `gobuster` are essential, but manual inspection is just as critical.
*   **Lesson:** Always read blog posts, comments, and "About Us" pages. They often contain usernames, emails, or context about the target. In this case, spotting the username `meliodas` was the turning point.

## 2. Never Ignore `robots.txt`
The `robots.txt` file is designed to tell search engine crawlers what *not* to index, but for attackers, it's a treasure map.
*   **Lesson:** Always check `/robots.txt`. It explicitly hinted at the wordlist to use (`rockyou`), narrowing down the brute-force scope significantly.

## 3. Privilege Escalation via Writable Scripts
The root compromise was possible because a user had `sudo` rights to run a script they also owned and could modify.
*   **Lesson:** If `sudo -l` shows you can run a script as root, immediately check the permissions of that script (`ls -l`). If you have write access (W) to the file or the directory it resides in, you can replace the legitimate code with a malicious payload (like a reverse shell or spawning `/bin/bash`).
*   **Remediation:** Administrators should ensure that scripts run via sudo are owned by root and are not writable by standard users.

## 4. SSH Brute Forcing
While often noisy and slow, brute forcing is viable when you have a valid username and a specific wordlist.
*   **Lesson:** Once a username is confirmed, targeted brute-forcing (especially with hints like "rockyou") is a valid path forward.