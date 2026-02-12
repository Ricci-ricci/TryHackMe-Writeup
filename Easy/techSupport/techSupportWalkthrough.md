# TryhackMe-Writeup/Easy/techSupport/techSupportWalkthrough.md

# Tech Support Walkthrough (Easy Difficulty)

Hey there! Welcome to my walkthrough for the "Tech Support" room on TryHackMe. This is an easy-level challenge, so it's a great starting point if you're new to penetration testing. We'll cover reconnaissance, enumeration, exploitation, and privilege escalation. I'll explain each step along the way so you can learn the "why" behind the "how." Let's dive in!

## Step 1: Reconnaissance with Nmap
First things first: We need to figure out what's running on the target machine. Reconnaissance is crucial in pentesting—it helps us identify open ports, services, and potential vulnerabilities without alerting the target.

We'll use Nmap for this. It's a powerful network scanner that can detect open ports, service versions, and even run basic scripts.

Command:
```
nmap -p- -sC -sV -T4 --min-rate=1000 <IP_ADDRESS>
```

- `-p-`: Scan all 65,535 ports (not just the top 1,000).
- `-sC`: Run default NSE scripts for more info (e.g., detecting vulnerabilities).
- `-sV`: Detect service versions (e.g., is it Apache 2.4.18?).
- `-T4`: Faster timing (aggressive but not too noisy).
- `--min-rate=1000`: Send at least 1,000 packets per second to speed things up.

Results:
- **22/tcp (SSH)**: OpenSSH 7.2p2 on Ubuntu. We might use this later for login.
- **80/tcp (HTTP)**: Apache 2.4.18. A web server—let's check it out.
- **139/tcp and 445/tcp (SMB)**: Samba (file sharing). SMB can be vulnerable if misconfigured.
- **4385/tcp**: Filtered (probably not useful).

Host details: Linux (Ubuntu), hostname "TECHSUPPORT". SMB is set to guest access, which is a red flag—guest accounts can sometimes lead to unauthorized access.

Visiting http://<IP_ADDRESS> shows the default Apache page. Nothing exciting yet, but we'll dig deeper.

## Step 2: Enumerating SMB Shares
SMB (Server Message Block) is for file sharing. Since Nmap showed guest access is enabled, let's see what shares are available. This is like checking if the front door is unlocked.

We'll use `smbmap` for enumeration. It lists shares and permissions.

Command:
```
smbmap -H <IP_ADDRESS> -u '' -p '' -R --depth 30
```

- `-H`: Target host.
- `-u '' -p ''`: Anonymous (guest) login.
- `-R --depth 30`: Recursively list files up to 30 levels deep.

Results:
- `print$`: No access (printer drivers).
- `websvr`: Read-only access! Inside, there's an `enter.txt` file.

Let's grab that file:
```
smbmap -H <IP_ADDRESS> -u '' -p '' -R -A 'enter.txt'
```

Content: It mentions "cooked with magical formula" and some creds. Looks like a hash! We'll decode it later. It also hints at Subrion CMS (a content management system).

## Step 3: Web Directory Enumeration with Gobuster
The web server on port 80 might have hidden directories. We saw a default page, but there could be more (like WordPress or Subrion).

Gobuster is a directory brute-forcer. It tries common paths from a wordlist.

Command:
```
gobuster dir -u http://<IP_ADDRESS> -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt -t 50
```

- `dir`: Directory mode.
- `-u`: Target URL.
- `-w`: Wordlist (medium-sized for balance).
- `-t 50`: 50 threads for speed.

Results:
- `/test`: A test directory (nothing interesting).
- `/wordpress`: A WordPress site (seems incomplete or abandoned).

Visiting `/wordpress` shows a "supposed to be deleted" page. Weird, but note it for later.

Back to the hash from `enter.txt`: Paste it into CyberChef (an online tool for decoding). Use the "Magic" operation—it auto-detects formats. We get credentials! (Spoiler: It's for Subrion.)

## Step 4: Exploiting Subrion CMS for Remote Code Execution (RCE)
Subrion is a CMS, and the creds from the hash let us log in at `http://<IP_ADDRESS>/subrion/panel`.

Dashboard shows Subrion v4.2.1. Quick search: CVE-2018-19422 is an RCE vulnerability in this version. RCE means we can execute code remotely—basically, run commands on the server.

Exploit it (details vary; use a public PoC script). We get a shell!

Navigate to `/wordpress` and find `wp-config.php`. It has database creds, including a password for user "scamsite" (odd name, but okay).

## Step 5: SSH Login and Privilege Escalation
Use the password to SSH in as "scamsite":
```
ssh scamsite@<IP_ADDRESS>
```

We're in! No user.txt (this box skips it), so straight to root.

Check `sudo -l`: We can run `/usr/bin/iconv` as root without a password. Iconv converts text encodings—harmless, right? Wrong! GTFOBins shows how to abuse it for file reads.

Command to read root.txt:
```
sudo /usr/bin/iconv -f 8859_1 -t 8859_1 /root/root.txt
```

Boom! Root flag. For a full shell, use the same trick to read `/root/.ssh/id_rsa` and SSH as root.

## Lessons Learned
This room was a fun intro to common pentesting techniques. Here are the key takeaways:

- **Recon is king**: Always start with Nmap. Knowing open ports and services guides your next moves.
- **Enumerate everything**: SMB guest access, web directories, and CMS versions can reveal creds or vulns. Tools like smbmap and gobuster are your friends.
- **Hashes and creds**: Decode them with tools like CyberChef. Weak/default configs (e.g., guest SMB) are common pitfalls.
- **Exploits matter**: Know CVEs for popular software (e.g., Subrion RCE). RCE is powerful—use it wisely (ethically!).
- **Privesc via sudo**: GTFOBins is a lifesaver for abusing "harmless" binaries. Always check `sudo -l`.
- **General tips**: Document steps, learn tool flags, and practice safe hacking. If stuck, research or ask the community—pentesting is collaborative.

If you followed along, congrats! Try harder rooms next. Questions? Hit me up. Happy hacking! 🚀
