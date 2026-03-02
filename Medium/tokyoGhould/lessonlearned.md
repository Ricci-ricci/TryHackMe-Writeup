# Tokyo Ghoul (Medium) — Lessons Learned

This room is a good reminder that medium boxes are often about chaining multiple “small” wins (FTP → steg → web vuln → cred crack → privesc), not a single magic exploit.

---

## 1) Don’t stop at “3 ports open”
Finding `21/ftp`, `22/ssh`, and `80/http` is only the starting point. The important part is what each service *allows*:
- FTP allowed **anonymous login**, which is almost always a deliberate entry point.
- HTTP hinted at checking FTP (source code / page clues).

**Takeaway:** When a service is exposed *and* misconfigured (like anonymous FTP), prioritize it. It’s commonly the intended path.

---

## 2) Read the hints, but still verify everything yourself
The room provides questions/hints that guide you (“find the note”, “ghoul left something”, etc.). Those hints reduce guessing, but you still need to verify artifacts:
- Inspect web page source when content seems “too empty”.
- Enumerate FTP directories and download everything interesting (images, executables, notes).

**Takeaway:** Use hints to save time, but always validate with your own enumeration so you don’t miss side artifacts.

---

## 3) Executables are often “password or key or clue generators”
Running the downloaded executable prompted for input. Using `strings` first revealed a potential keyword (`kamishiro`), which then produced a message used later.

**Takeaway:** Before executing unknown binaries, do quick static triage:
- `file`, `strings`, and basic behavior checks can reveal embedded secrets, names, file paths, or expected input.
- In CTFs, executables frequently exist just to output a key/passphrase for the next step.

---

## 4) Steganography: treat it as “extract, then recurse”
The image required a passphrase to extract embedded content (via `steghide`). After extraction, the output wasn’t the final answer—it was an encoded chain:
- Morse → Hex → Base64 → URL/endpoint

**Takeaway:** With steg/encoding tasks:
- Expect multiple layers.
- Keep your decoding workflow tidy (CyberChef is perfect for this).
- Write down each intermediate output so you can reproduce the chain.

---

## 5) When you see `?view=...`, think “LFI / path traversal”
A parameter like `view=gallery.gif` is a classic signal to test Local File Inclusion / traversal:
- Direct traversal attempts were blocked at first.
- URL encoding bypassed naive filtering and allowed reading files like `/etc/passwd`.

**Takeaway:** Input filters are often substring-based and bypassable.
- Try URL encoding, double-encoding, and alternate path formats.
- If the app responds with “don’t do that”, it’s still valuable feedback: you’re on the right track.

---

## 6) Hashes in system files usually mean “crack and pivot”
Pulling `/etc/passwd` (or similar data) revealed a user and a hash. Cracking it with `john` + `rockyou` led to SSH credentials.

**Takeaway:** Once you have a hash:
- Identify the type if possible, but try a standard cracking workflow first.
- A cracked password is most valuable when it enables a *new interface* (SSH is ideal).

---

## 7) Python “jails” are weak when they rely on keyword blacklists
The privilege escalation hinged on a Python script that blocks certain substrings (`eval`, `import`, `os`, `system`, etc.) but then calls `exec(text)`.

That’s fundamentally unsafe: you can build blocked words dynamically and still reach restricted functionality through `__builtins__`.

**Takeaway (offense):**
- Blacklists are brittle. Look for ways to:
  - construct strings dynamically (`'__IMPORT__'.lower()`)
  - access builtins indirectly (`__builtins__.__dict__[...]`)
- If you see `exec()` on user input, assume escape is possible.

**Takeaway (defense):**
- Never run `exec()` on user-controlled input.
- If you need restricted execution, use real sandboxing, not substring filtering.

---

## 8) Workflow discipline matters (and saves time)
This box reinforces a clean workflow:
1. Enumerate (`nmap`, manual web review)
2. Harvest artifacts (FTP downloads)
3. Extract clues (strings / steg)
4. Decode layers (CyberChef)
5. Exploit web flaw (LFI traversal + bypass)
6. Crack creds (John)
7. SSH for stability
8. Privesc (Python jail escape)

**Reusable checklist:** After each win, ask: “What did this unlock that I couldn’t do before?”
- New endpoint?
- New file read?
- A credential?
- A new shell?
- Higher privileges?

---