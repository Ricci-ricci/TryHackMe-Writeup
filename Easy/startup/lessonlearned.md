# Startup (Easy) — Lessons Learned

This room demonstrates a common web exploitation pattern:
**anonymous FTP with write access → webshell upload → packet capture credential harvesting → script-based privilege escalation**

---

## 1) Anonymous FTP with write permissions is a critical vulnerability

### What happened
The FTP service allowed anonymous login and had a directory (`/ftp`) that was:
- world-writable
- accessible via the web server at `/files/ftp/`

This creates a direct path to remote code execution: upload a webshell via FTP, then trigger it through the web interface.

### Practical takeaway
Anonymous FTP should **never** have write permissions to web-accessible directories. This combination essentially gives any attacker the ability to upload and execute arbitrary code.

**Defense:**
- Disable anonymous FTP write access
- If file uploads are needed, implement proper authentication and validation
- Ensure uploaded files cannot be executed by the web server
- Use separate, non-web-accessible directories for FTP uploads

---

## 2) Web directory enumeration reveals upload paths

### What mattered
Directory enumeration discovered `/files/`, which mapped directly to the FTP upload directory. This revealed the connection between the FTP service and web-accessible content.

### Practical takeaway
When you find both an upload mechanism (FTP) and a web server:
- Always enumerate web directories to find where uploads might be accessible
- Look for common paths like `/files/`, `/uploads/`, `/ftp/`, `/media/`
- Test if uploaded files are directly executable via HTTP

---

## 3) Packet captures can contain plaintext credentials

### What happened
After gaining initial access, a packet capture file was found in an `/incidents/` directory. Analyzing this file in Wireshark revealed plaintext credentials for the user `lennie`.

### Why this is realistic
Incident response often involves:
- Network traffic captures during security events
- Storing forensic evidence in accessible locations
- Capturing unencrypted protocols that leak credentials

### Practical takeaway (offense)
When you have file system access, look for:
- `.pcap`, `.pcapng`, `.cap` files
- Log directories (`/var/log/`, `/logs/`, `/incidents/`)
- Backup directories that might contain sensitive data
- Any files related to security monitoring or incident response

### Practical takeaway (defense)
- Store packet captures in secure, access-controlled locations
- Use encrypted protocols (HTTPS, SSH, etc.) to prevent credential leakage
- Implement proper log rotation and secure disposal of sensitive forensic data
- Limit access to incident response artifacts

---

## 4) Script-based privilege escalation through file ownership chains

### What happened
The privilege escalation involved a root-owned script (`planner.sh`) that:
1. Had read and execute permissions for the current user
2. Called another script (`/etc/print.sh`) that was owned by the user
3. Since the user could modify the called script, they could inject commands that would run as root

### The vulnerability pattern
```bash
#!/bin/bash
echo $LIST > /home/lennie/scripts/startup_list.txt
/etc/print.sh  # This script is user-writable!
```

Even though `planner.sh` runs as root, it calls a script that can be modified by a lower-privileged user.

### Practical takeaway (offense)
When looking for privilege escalation:
- Find scripts that run as root (cron jobs, sudo rules, SUID scripts)
- Trace what files/scripts they call
- Check if you have write access to any of those dependencies
- If yes, inject your payload (reverse shell, add SSH keys, etc.)

### Practical takeaway (defense)
- Ensure all scripts called by privileged processes are owned by root and not writable by other users
- Use absolute paths in scripts to prevent PATH hijacking
- Implement proper file permission auditing
- Consider using `sudo` with specific command restrictions instead of SUID scripts

---

## 5) Reusable workflow for similar boxes

### Discovery & Initial Access
- [ ] Nmap scan → identify FTP, SSH, HTTP
- [ ] Check if FTP allows anonymous login with write access
- [ ] Enumerate web directories to find upload paths
- [ ] Upload webshell via FTP
- [ ] Execute via web interface

### Post-exploitation
- [ ] Search for packet captures and log files
- [ ] Analyze captures with Wireshark for credentials
- [ ] Use recovered credentials for lateral movement (SSH)

### Privilege Escalation
- [ ] Look for root-owned scripts in user directories or common locations
- [ ] Trace script dependencies and file calls
- [ ] Check write permissions on called scripts/files
- [ ] Modify writable dependencies to inject privileged commands

---

## 6) Why this attack chain is realistic

This isn't just a CTF scenario. Real-world environments where this pattern appears:
- Development servers with loose FTP configurations
- Staging environments that mirror production file structures
- Legacy systems with inherited misconfigurations
- Small organizations without dedicated security teams

The combination of:
- Anonymous services (FTP)
- Web-accessible upload directories
- Incident response artifacts stored insecurely
- Poor script permission management

...creates multiple attack vectors that compound into full system compromise.

---

## One-line takeaway
Anonymous FTP + web uploads + insecure script dependencies = a complete compromise chain that's both common and preventable with basic security hygiene.