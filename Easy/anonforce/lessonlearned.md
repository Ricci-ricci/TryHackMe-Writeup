# AnonForce (Easy) — Lessons Learned

This room demonstrates a classic misconfiguration chain:
**anonymous FTP with excessive access → encrypted backup extraction → GPG key cracking → shadow file recovery → password cracking → root SSH**

---

## 1) Anonymous FTP is a critical misconfiguration when it exposes the filesystem

### What happened
The FTP service allowed anonymous login and exposed the **entire filesystem root** (`/`), including:
- `/etc/` (config files)
- `/home/` (user data)
- `/root/` (root's home directory)

This is not "FTP with a few files"—this is "read-only root filesystem access."

### Practical takeaway
If anonymous FTP is enabled:
- It should be **jailed** to a specific, non-sensitive directory (e.g., `/var/ftp/pub/`)
- It should **never** expose system directories like `/etc/`, `/home/`, or `/root/`
- Treat it as if you're handing an attacker a complete file listing of your system

**Defense:**
- Disable anonymous FTP unless absolutely required
- Use `chroot` jails for FTP users
- Audit what's accessible and remove sensitive files
- Prefer SFTP (SSH-based) with key authentication over FTP

---

## 2) Encrypted backups are only as strong as the key's passphrase

### What happened
The box contained a PGP-encrypted backup file (`backup.pgp`) and the private key (`private.asc`) needed to decrypt it. The private key itself was passphrase-protected.

The workflow was:
1. Extract the PGP private key
2. Convert it to a crackable format (`gpg2john` / `pgp2john`)
3. Crack the passphrase with John + wordlist
4. Import the key with the recovered passphrase
5. Decrypt the backup

### Practical takeaway (offense)
Encrypted files are only as safe as:
- the strength of the key's passphrase
- whether the key is accessible alongside the encrypted data (as it was here)

If you find:
- `.asc`, `.gpg`, `.pgp` files (keys)
- encrypted archives or backups
- both in the same location

…you have a crackable chain.

### Practical takeaway (defense)
- **Never store private keys and encrypted data together** on the same system
- Use strong, unique passphrases for key material
- Prefer hardware tokens or key management systems for sensitive keys
- Regularly audit backup storage for leaked key material

---

## 3) `/etc/shadow` alone is not enough; you need `/etc/passwd` too

### What mattered
After decrypting the backup, you obtained `/etc/shadow` (password hashes). To crack those hashes with John, you also needed `/etc/passwd` (which maps usernames to UIDs and provides context for `unshadow`).

The workflow:
1. Obtain `/etc/shadow` (from decrypted backup)
2. Obtain `/etc/passwd` (from FTP)
3. Combine them using `unshadow`
4. Crack with John

### Why this pattern exists
- `shadow` contains the hashes, but doesn't always have full username context in older formats
- `passwd` provides usernames, UIDs, home directories, shells
- `unshadow` merges them into a format John can process efficiently

### Practical takeaway
If you get one file but not the other:
- `/etc/shadow` alone: you can still try cracking if you know the usernames, but `unshadow` is cleaner
- `/etc/passwd` alone: no hashes, but you learn valid usernames (useful for brute-force or social engineering)

**Defense:**
- Protect both `/etc/passwd` and `/etc/shadow` (shadow should already be `root:shadow` `0640`)
- Never back up `/etc/shadow` in plaintext or with weak encryption
- Use centralized auth (LDAP/SSO) on sensitive systems where possible

---

## 4) Root with a weak password = game over

### What happened
Once the combined `shadow` + `passwd` was cracked, you recovered the **root password**. SSH was open, so direct root login was possible.

### Practical takeaway
This is a reminder that even strong system hardening fails if:
- root has a weak/reused password
- root SSH login is enabled
- the password appears in common wordlists

**Defense:**
- Disable root SSH login (`PermitRootLogin no`)
- Enforce SSH key authentication
- Use strong, unique passwords (or disable password auth entirely)
- Monitor failed SSH attempts and rate-limit

---

## 5) Reusable workflow: FTP → GPG → unshadow → root

### Checklist for similar boxes
#### Discovery
- [ ] Nmap all ports
- [ ] Check if FTP allows anonymous login
- [ ] If yes, enumerate accessible directories

#### Exploitation
- [ ] Download interesting files (configs, backups, keys)
- [ ] If you find encrypted backups + private keys, crack the key passphrase
- [ ] Decrypt the backup
- [ ] Combine shadow + passwd with `unshadow`
- [ ] Crack with John + wordlist
- [ ] SSH with recovered credentials

---

## 6) Why this is realistic (and scary)

This isn't just a CTF gimmick. Real-world scenarios where this pattern shows up:
- Backup servers with anonymous/misconfigured FTP
- Dev/test environments with "temporary" weak access controls
- Legacy systems where "security by obscurity" was assumed
- Archived virtual machines or disk images with old credentials

---

## One-line takeaway
Anonymous FTP exposing the filesystem + encrypted backups stored with weak-key-passphrase GPG keys = trivial root compromise.