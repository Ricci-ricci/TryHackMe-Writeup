# RabbitStore (Medium) — Lessons Learned

This document summarizes the key takeaways from the RabbitStore box, with special focus on the “last part” (RabbitMQ/Erlang) so you don’t get lost.

---

## 1) Web → RCE: Template Injection mindset

### What mattered
- When you see user-controlled input getting rendered inside a server-side template, you should immediately think **SSTI (Server-Side Template Injection)**.
- The win condition is usually “prove code execution,” then “turn it into a shell.”

### Practical takeaways
- If you can evaluate expressions (e.g., `{{ ... }}`), test for basic arithmetic first (`{{7*7}}`) to confirm evaluation.
- Once confirmed, pivot to **command execution** through template internals (framework-dependent).
- Prefer payloads that are:
  - Short
  - Easy to verify (`id`, `whoami`)
  - Then upgrade to a reverse shell

### For stability
- After you land a shell, immediately stabilize it:
  - Spawn a PTY (`python3 -c 'import pty; pty.spawn("/bin/bash")'`)
  - Fix terminal settings (`stty raw -echo; fg`)
  - Set `TERM=xterm`

---

## 2) Enumeration: don’t guess, measure

### What mattered
- Running an enumeration script (like `linpeas`) is useful, but the real skill is interpreting the output.
- You’re looking for:
  - Unexpected services listening
  - Internal-only services exposed externally
  - Credentials/config files
  - Sudo rules / capabilities / cron jobs

### Practical takeaways
- Always note **what ports are listening & on which interface**.
  - “Listening on localhost” is very different from “listening on 0.0.0.0”.
- If you see RabbitMQ/Erlang ports exposed, that’s not “just another port.” It often implies **remote node control** if you can authenticate.

---

## 3) RabbitMQ/Erlang privilege escalation: the mental model (the part people get lost on)

This section explains the *why* and the *flow*.

### 3.1 RabbitMQ runs on Erlang: what EPMD is
RabbitMQ is written in Erlang. Erlang nodes (including RabbitMQ nodes) use a distributed protocol. The **Erlang Port Mapper Daemon (`epmd`)** helps nodes find each other and negotiate distribution ports.

If Erlang distribution is reachable and you can authenticate, you can often interact with the RabbitMQ node remotely.

### 3.2 The Erlang cookie is the key
Erlang nodes authenticate with a shared secret called the **Erlang cookie**.

- Think of the cookie as a “cluster password.”
- If you have the cookie that the RabbitMQ node uses, tools like `rabbitmqctl` can talk to the broker as a trusted peer.

Common cookie locations on Linux:
- `~/.erlang.cookie`
- `/var/lib/rabbitmq/.erlang.cookie` (very common for RabbitMQ)
- `/root/.erlang.cookie` (usually not readable)

**Important:** You need the cookie that matches the target RabbitMQ node you’re querying.

### 3.3 Why you edited `/etc/hosts`
RabbitMQ node names look like:

- `rabbit@forge`

That `forge` must resolve to the box IP from *where you’re running the command*. If DNS doesn’t know `forge`, your tooling fails in confusing ways.

So you add:
- `<TARGET_IP> forge`

This is not a “hack”—it’s just making sure the node name resolves correctly.

### 3.4 Using `rabbitmqctl` against a remote node
Once:
- `forge` resolves
- you have the Erlang cookie
- the Erlang/RabbitMQ ports are reachable

…then you can run something like:

- `rabbitmqctl --erlang-cookie 'COOKIE' --node rabbit@forge list_users`

This asks the *RabbitMQ broker* to list its users. On many boxes, that reveals:
- an administrator user
- possibly a stored password hash (or password-derived value)

---

## 4) Understanding the RabbitMQ password format (most common confusion)

### 4.1 What you actually get back
RabbitMQ can store password hashes internally in a format that often appears as a base64 blob.

A common scheme (as referenced in the walkthrough) is conceptually:

- `base64( salt(4 bytes) + sha256( salt(4 bytes) + password ) )`

So the base64 data contains:
1) First 4 bytes: the **salt**
2) Remaining bytes: the **SHA-256 digest**

### 4.2 What you *can* and *cannot* do
- You **cannot** “decrypt” SHA-256.
- To recover the original password, you typically need:
  - a wordlist attack (guess passwords)
  - recompute `sha256(salt + guess)`
  - compare with the digest

That’s cracking, not decryption.

### 4.3 Extracting the salt correctly
If you save the base64 string to `password.txt`, decoding gives raw bytes.

A correct mental model:
- Base64 decode → raw bytes
- First 4 bytes → salt
- Remaining 32 bytes → sha256 digest (since SHA-256 = 32 bytes)

A common pitfall:
- extracting the wrong number of characters (hex vs bytes confusion)
- including an extra character when cutting output

In hex:
- 4 bytes = 8 hex characters
So when you look at a hex dump, the salt is the first **8 hex chars**.

### 4.4 What “success” looks like
Once you’ve got the credential (whether recovered via intended weakness or cracking), the final step is straightforward:
- `su root`
- enter password
- read `root.txt`

---

## 5) Defensive lessons (optional, but useful)

### For developers / ops
- Never expose Erlang distribution ports or `epmd` publicly.
- Treat `.erlang.cookie` like a private key:
  - strict permissions
  - rotate if leaked
- For RabbitMQ:
  - bind management and distribution interfaces appropriately
  - firewall internal services
  - use strong admin passwords

---

## 6) Checklist you can reuse in future boxes

### Initial access
- [ ] Confirm SSTI (or other injection) with a harmless test
- [ ] Convert to command execution
- [ ] Get a stable shell (PTY + terminal fixes)

### Local enumeration
- [ ] Identify listening services and exposed ports
- [ ] Search for credential files, cookies, tokens, configs
- [ ] Check misconfigurations that enable lateral/admin access

### RabbitMQ/Erlang-specific
- [ ] Does `rabbit@<hostname>` resolve?
- [ ] Can you obtain `.erlang.cookie`?
- [ ] Can you query with `rabbitmqctl`?
- [ ] If a salted hash is shown: extract salt + digest correctly
- [ ] Crack/derive password using the correct hashing formula

---

## 7) One-line “lesson learned”
If a box exposes RabbitMQ/Erlang services, the privilege escalation often isn’t a kernel exploit—it’s **authentication reuse via the Erlang cookie** paired with **admin tooling** (`rabbitmqctl`) and correct understanding of how the stored password blob is structured.