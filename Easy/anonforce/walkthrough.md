# TryHackMe — AnonForce (Easy) Walkthrough

> Room: **AnonForce** (Easy)  
> Goal: Gain root access through anonymous FTP and PGP key cracking.

This box is a straightforward chain:
**Nmap → anonymous FTP → download encrypted backup → crack PGP key → decrypt shadow file → crack root password → SSH as root**

---

## 1) Recon (Nmap)

Run a full TCP scan with default scripts and version detection:

```/dev/null/nmap.txt#L1-1
nmap -p- -sC -sV -T4 --min-rate=1000 -oN nmap_scan.txt <IP_ADDRESS>
```

### Results (key ports)

- `21/tcp` — FTP (vsftpd 3.0.3)
  - **Anonymous login allowed**
  - The FTP server is exposing the entire root filesystem (`/`)
- `22/tcp` — SSH (OpenSSH 7.2p2)

**Critical finding:** The FTP service allows anonymous access and has mounted the system root directory, meaning you can browse and download nearly any file on the system.

---

## 2) Anonymous FTP access (browse the filesystem)

Connect to FTP anonymously:

```/dev/null/ftp.txt#L1-3
ftp <IP_ADDRESS>
Name: anonymous
Password: anonymous
```

Once connected, you can navigate the filesystem. Key observations from the Nmap script output:

- Standard Linux directories are visible (`/etc`, `/home`, `/root`, etc.)
- A directory called `/notread` exists (writable, unusual)

Navigate and explore:

```/dev/null/ftp_ls.txt#L1-2
ls
cd /home
```

---

## 3) Download interesting files

### 3.1 User flag

The user flag is accessible directly via FTP. Download it:

```/dev/null/get_user.txt#L1-1
get user.txt
```

### 3.2 PGP-encrypted backup and private key

During exploration, you should find:

- `backup.pgp` (an encrypted file, likely containing sensitive data)
- `private.asc` (a PGP/GPG private key, passphrase-protected)

Download both:

```/dev/null/get_pgp.txt#L1-2
get backup.pgp
get private.asc
```

Exit FTP and work locally on your attacking machine.

---

## 4) Crack the PGP private key passphrase

The private key (`private.asc`) is passphrase-protected. To crack it, convert it to a format John the Ripper understands:

```/dev/null/pgp2john.txt#L1-1
gpg2john private.asc > privatejohn.txt
```

Then crack it with John:

```/dev/null/john_pgp.txt#L1-1
john privatejohn.txt
```

Once John recovers the passphrase, note it down.

---

## 5) Import the key and decrypt the backup

### 5.1 Import the private key into GPG

```/dev/null/gpg_import.txt#L1-1
gpg --import private.asc
```

When prompted, enter the passphrase that John recovered.

### 5.2 Decrypt the backup file

```/dev/null/gpg_decrypt.txt#L1-1
gpg --decrypt backup.pgp
```

The decrypted content is the system's `/etc/shadow` file, which contains password hashes.

---

## 6) Obtain `/etc/passwd` and combine with `/etc/shadow`

To crack the hashes from `/etc/shadow`, you also need `/etc/passwd` (which is readable by anyone and contains usernames/UIDs).

Go back to the FTP server and download `/etc/passwd`:

```/dev/null/ftp_passwd.txt#L1-4
ftp <IP_ADDRESS>
Name: anonymous
Password: anonymous
get /etc/passwd
```

---

## 7) Combine `/etc/passwd` and `/etc/shadow` using `unshadow`

The `unshadow` tool merges the two files into a format John can crack:

```/dev/null/unshadow.txt#L1-1
unshadow passwd shadow > unshadowed.txt
```

---

## 8) Crack the root password hash

Run John against the combined file:

```/dev/null/john_root.txt#L1-1
john --wordlist=/usr/share/wordlists/rockyou.txt unshadowed.txt
```

This recovers the `root` password.

---

## 9) SSH as root and retrieve the root flag

SSH into the box as `root`:

```/dev/null/ssh_root.txt#L1-1
ssh root@<IP_ADDRESS>
```

Enter the cracked password, then read the root flag (commonly `/root/root.txt`).

---

## Summary (attack chain)

1. Nmap → identify FTP with anonymous access + root filesystem exposed
2. FTP anonymous → download `user.txt`, `backup.pgp`, and `private.asc`
3. Crack PGP key passphrase with `gpg2john` + `john`
4. Import key and decrypt `backup.pgp` → reveals `/etc/shadow`
5. Download `/etc/passwd` via FTP
6. Combine with `unshadow` → crack root hash with John
7. SSH as `root` → retrieve root flag

---

## Notes / Defensive takeaways

- **Never expose the root filesystem via anonymous FTP.** This is a catastrophic misconfiguration.
- Restrict FTP access to specific directories (chroot) and disable anonymous login unless absolutely necessary.
- Sensitive files (`/etc/shadow`, private keys) should never be world-readable or accessible via public services.
- Use strong, unique passphrases for PGP keys.
- Regularly audit service configurations and file permissions.