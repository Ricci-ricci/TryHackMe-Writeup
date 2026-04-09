# JPGChat (Easy) — Lessons Learned

This room demonstrates two focused but impactful vulnerabilities:
**OS command injection via unsanitized shell calls → Python PYTHONPATH hijacking for privilege escalation**

---

## 1) Reading source code is the fastest path to exploitation

### What happened
The service hinted at a public GitHub repository containing its source code. Reading that code immediately revealed:
- User input was passed directly into `os.system()` without any sanitization
- No filtering, escaping, or validation was applied to `your_name` or `report_text`

### Practical takeaway
When a service leaks or references its source code:
- Read it immediately
- Look for dangerous function calls: `os.system()`, `subprocess`, `eval()`, `exec()`
- Look for user input flowing directly into those calls
- The vulnerability is usually obvious once you see the code

---

## 2) OS command injection: `os.system()` with `%s` string formatting is dangerous

### The vulnerable code pattern

```python
os.system("bash -c 'echo %s > /opt/jpchat/logs/report.txt'" % your_name)
```

### Why this is exploitable
The `%s` substitution inserts raw user input directly into a shell command string. There is no:
- Escaping of shell metacharacters
- Quoting of the input value
- Input validation or allowlisting

An attacker can inject shell metacharacters like `;`, `|`, `&&`, or use quote-breaking to terminate the intended command and append their own.

### The payload that worked

```
lore';/bin/bash;echo '
```

**Breaking down what this does:**
- `lore'` → provides a value and closes the opening single quote
- `;` → ends the current shell command
- `/bin/bash` → executes a new shell as the service's user
- `;echo '` → starts another command and opens a new single quote to balance the trailing `'` in the original command string

This cleanly injects a shell command in between the intended `echo` calls.

### Practical takeaway
Any time you see user input concatenated into a shell command string:
- Try to break out of the string context (quotes, semicolons)
- Use `;` or `&&` to chain your own commands
- Single or double quotes can be used to close existing string context
- Test simple payloads first (`; id`, `; whoami`) before escalating to full shells

### Defense
- **Never** pass user input directly to `os.system()` or `subprocess.call(shell=True)`
- Use `subprocess.run()` with a **list** of arguments instead of a shell string
- Validate and allowlist input before processing
- Avoid shell=True unless absolutely necessary

**Safe pattern:**
```python
import subprocess
subprocess.run(["bash", "-c", "echo", sanitized_name], shell=False)
# or even better:
with open("/opt/jpchat/logs/report.txt", "w") as f:
    f.write(your_name + "\n")
```

---

## 3) `sudo -l` revealed a subtle but powerful misconfiguration

### What happened
The sudo rule for user `wes` was:

```
(root) SETENV: NOPASSWD: /usr/bin/python3 /opt/development/test_module.py
```

Two key things stood out:
1. The script could be run as root without a password
2. **`SETENV`** was present, meaning environment variables could be preserved or set when running the command as root

### Why `SETENV` + Python = privilege escalation

Python uses the `PYTHONPATH` environment variable to find modules before searching default locations. If you can:
1. Set `PYTHONPATH` to a directory you control
2. Create a file in that directory with the same name as a module the target script imports
3. Run the script as root

...then Python will import **your** module instead of the real one, executing your code as root.

### The escalation chain

1. Identify what module `test_module.py` imports (in this case `compare`)
2. Create a malicious `compare.py` in a writable directory:

```python
import os
os.system("/bin/bash")
```

3. Set `PYTHONPATH` to that directory:

```bash
export PYTHONPATH=/home/wes
```

4. Run the sudo command:

```bash
sudo /usr/bin/python3 /opt/development/test_module.py
```

Python resolves `import compare` → finds `/home/wes/compare.py` → executes it as root → root shell.

### Practical takeaway
When you see:
- `sudo -l` shows `SETENV` in a rule
- The command runs a Python (or any interpreted language) script
- You have write access to any directory

Assume Python module hijacking is possible. Check what modules the target script imports and create your malicious replacement.

### Defense
- **Avoid `SETENV`** in sudo rules unless strictly necessary
- If Python scripts must run as root via sudo, use `env_reset` and explicitly clear `PYTHONPATH`
- Use absolute imports and verify module integrity if running scripts with elevated privileges
- Consider using virtual environments with fixed, audited dependencies
- Add `Defaults env_reset` and explicitly deny `PYTHONPATH` in `/etc/sudoers`

---

## 4) Two vulnerabilities, two categories — both fundamental

| Stage | Vulnerability | Root Cause |
|---|---|---|
| Initial access | OS command injection | Unsanitized input in `os.system()` |
| Privilege escalation | Python PYTHONPATH hijacking | `SETENV` in sudo + writable directory |

Both are preventable with basic secure coding and proper sudo configuration.

---

## 5) Reusable checklist

### Initial access
- [ ] Connect to exposed service and probe behavior
- [ ] Find/read source code if referenced
- [ ] Look for `os.system()`, `subprocess`, `eval()` with user input
- [ ] Try shell metacharacter injection (`;`, `|`, `&&`, quote breaks)

### Privilege escalation
- [ ] Run `sudo -l`
- [ ] Check for `SETENV` keyword in sudo rules
- [ ] Identify what language/interpreter the allowed script uses
- [ ] Check what modules/libraries the script imports
- [ ] Create a malicious replacement in a writable directory
- [ ] Set the appropriate path variable and run the sudo command

---

## One-line takeaway
Unsanitized shell calls give you a user shell; `SETENV` in a Python sudo rule gives you root — both are simple bugs with severe consequences.