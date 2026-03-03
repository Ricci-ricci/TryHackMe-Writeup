# GamingServer (Easy) — Lessons Learned

This room is a clean example of how an “easy” box often boils down to two things:

1. **Find the hidden entry point** (web enumeration → key material).
2. **Recognize a dangerous local privilege** (LXD/LXC access → host filesystem mount → root).

---

## 1) Enumeration mindset: the default page is rarely the app

Even though the web service is “just Apache”, directory brute forcing quickly revealed endpoints like:

- `/secret/`
- `/uploads/`
- `/robots.txt`

**Lesson:** If port `80` is open, always do at least:
- manual browsing + page source review
- directory enumeration (wordlist-based)
- check `robots.txt`

Many CTF-style boxes hide the entire initial access path behind one non-linked directory.

---

## 2) SSH keys are credentials — treat them like passwords

The box gave an **encrypted private SSH key**. That changes the approach:

- You don’t brute force SSH directly.
- You crack the key’s **passphrase** (offline), then use the key normally.

**What this reinforces:**
- “Encrypted private key” doesn’t mean “safe” if the passphrase is weak.
- Offline cracking is fast and quiet compared to online brute force.

**Practical workflow (high-level):**
- Convert key into a crackable format (e.g., “SSH key → hash format”).
- Run a wordlist attack on the passphrase.
- Use the key with `ssh -i`.

**Defense takeaway:** Use strong passphrases (long, unique) *or* prefer modern hardware-backed keys. Weak passphrases turn key encryption into a speed bump.

---

## 3) When you land a user shell: immediately ask “what groups am I in?”

After SSH access, the critical check isn’t flashy exploitation — it’s Linux basics:

- `id`
- `groups`
- `sudo -l`
- running services / local tooling

This room’s privilege escalation hinges on LXD/LXC. Typically, the user is in a group like:
- `lxd`

**Lesson:** Group membership can be a privilege escalation vector all by itself. If you’re in a high-impact group, you might already be “one command away” from root.

---

## 4) Deep dive: Why LXD/LXC access is basically root

### 4.1 LXD vs LXC (mental model)
- **LXD** is a system daemon that manages containers (like a lightweight VM manager).
- **LXC** is the container technology / client tooling used to interact with LXD.

The important part: **containers can be configured with powerful mounting and device options**. If a low-privileged user is allowed to control LXD, they can often:

- create a privileged container
- mount the host filesystem inside it
- access host files as root
- edit host files (including `/etc/shadow`, SSH keys, sudoers, etc.)

### 4.2 The core vulnerability: host filesystem mount
The standard escalation is:

1. Import an image (commonly an Alpine Linux rootfs tarball).
2. Create/start a container.
3. Attach a disk device that maps the host filesystem into the container.
4. Enter the container.
5. Read or modify host files through the mounted path.

Inside the container you appear as `root` *in the container*, but the reason this matters is the **mounted host path**:
- if you mount host `/` to something like `/mnt/root`, you’re effectively browsing the host filesystem with elevated access.

### 4.3 What “privileged container” means here
A “privileged container” in this context usually means container processes that can act with elevated privileges relative to the host namespace mappings. Misconfiguration or overly-permissive LXD usage allows mounting host disks and bypassing normal user permission boundaries.

**Practical takeaway:** If you can do `lxc image import`, `lxc init`, `lxc config device add`, and `lxc exec` as your current user, you’re very likely able to escalate.

---

## 5) Proof-of-impact: what you can do once host `/` is mounted

Once host root is mounted inside the container, you can:

- read root-only files (flags, configs, backups)
- grab host SSH keys from `/root/.ssh/`
- reset passwords by editing `/etc/shadow` (if you know what you’re doing)
- add a new sudoer entry (dangerous, noisy)
- drop an SSH public key into `/root/.ssh/authorized_keys` for persistence (also noisy)

In the room, the intended path is simply:
- mount the host root filesystem
- locate and read the root flag under the mounted directory

**Lesson:** Many privesc paths don’t require a kernel exploit. They require noticing that you already have a “management interface” permission that is equivalent to root.

---

## 6) Common pitfalls with LXD/LXC escalation (so you don’t get stuck)

- **You imported an image but can’t start the container:** ensure the image alias is correct and the container name exists.
- **Mount command fails:** verify the container exists and is stopped when adding devices (depending on config).
- **You’re root in container but can’t read host files:** you may not have actually mounted host `/` or the mount path is wrong.
- **Networking confusion:** image transfer is easiest via a simple HTTP server + `wget/curl` from the target.

---

## 7) Defensive lessons (what would prevent this in a real environment)

- Do not add normal users to the `lxd` group unless absolutely required.
- Treat LXD administrators as equivalent to `root`.
- Audit group memberships regularly.
- Restrict LXD usage to trusted operators and hardened hosts.
- Monitor for container creation and unusual disk device attachments.

---

## One-line takeaway
If your shell user can manage LXD/LXC, privilege escalation isn’t “maybe” — it’s usually **mount host `/` into a container and you effectively become root**.