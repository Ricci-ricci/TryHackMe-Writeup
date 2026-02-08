# Soupedecode - Mission Briefing & Analysis

**Target:** `DC01.SOUPEDECODE.LOCAL` (Windows Domain Controller)
**Objective:** Compromise the domain controller, retrieve user and root flags.
**Key Techniques:** SMB Enumeration, RID Cycling, Password Spraying, Kerberoasting, Sensitive Data Exposure, Pass-the-Hash.

---

### The Attack Chain

#### 1. Reconnaissance & Enumeration
*   **Port Scan:** Nmap revealed a standard Domain Controller profile (DNS, Kerberos, RPC, SMB, LDAP).
*   **SMB Guest Access:** Identified that the `Guest` account was enabled on SMB, allowing unauthenticated listing of shares.
*   **User Enumeration:** Leveraging the guest access, Metasploit's `lookupsid` module (RID Cycling) was used to dump a list of **1,069 domain users**.

#### 2. Initial Access
*   **Password Spraying:** Armed with the user list, performed a specific spray attack testing for "Username as Password" (`user:user`).
*   **Success:** The user `ybob317` was found using the password `ybob317`.
*   **Flag Retrieval:** Accessing the `Users` share with these credentials provided the `user.txt` flag.

#### 3. Lateral Movement & Privilege Escalation
*   **Kerberoasting:** Used `impacket-GetUserSPNS` to request Service Principal Name (SPN) tickets. Successfully captured hashes for several services.
*   **Cracking:** Using John the Ripper, cracked the password for the `file_svc` account.
*   **Data Exfiltration:** Accessing the `backup` SMB share as `file_svc`, downloaded a critical file: `backup.extract.txt`.
*   **Hash Extraction:** This backup file contained NTLM hashes. Cleaned the data to create a user list and a hash list.
*   **Pass-the-Hash (PtH):** Sprayed the extracted hashes against the extracted users using `NetExec`. Found a match for the high-privileged `FileServer` account.
*   **Domain Compromise:** Using `impacket-psexec` with the discovered hash, obtained a system shell and retrieved `root.txt`.

---

###Lessons Learned & Security Concepts

This box demonstrates several critical misconfigurations common in Active Directory environments:

#### 1. The Danger of Guest Access
*   **The Flaw:** Leaving the Guest account enabled on SMB allows attackers to query the Domain Controller without valid credentials.
*   **The Impact:** This allowed mapping of shares and RID Cycling to dump the entire list of usernames. Without this list, the subsequent password spray would have been nearly impossible.
*   **Fix:** Disable the Guest account and restrict anonymous enumeration of SAM accounts and shares.

#### 2. Weak Password Policies
*   **The Flaw:** The user `ybob317` had a password identical to their username.
*   **The Impact:** This is the "low-hanging fruit" for attackers. Even without complex brute-forcing, a simple check of `user:user` or `user:password` often grants entry.
*   **Fix:** Enforce strong password complexity policies and prevent passwords that contain the username.

#### 3. Kerberoasting is Deadly Effective
*   **The Flaw:** Service accounts (like `file_svc`) often have privileges but weak passwords.
*   **The Concept:** Any authenticated user can request a ticket for a service account. If the service account has a weak password, the ticket can be cracked offline.
*   **Fix:** Service accounts should have randomly generated, 25+ character passwords that are rotated frequently (or use Managed Service Accounts - gMSA).

#### 4. Improper Handling of Backups
*   **The Flaw:** A backup file containing sensitive NTLM hashes (`backup.extract.txt`) was stored on a share accessible to the `file_svc` user.
*   **The Impact:** This is a "Toxic Pipeline" scenario. A lower-privileged service account was used to find credentials for a higher-privileged account.
*   **Fix:** Backups containing credential data must be strictly secured. They should never be readable by standard service accounts or users.

#### 5. NTLM Hashes are as Good as Passwords
*   **The Flaw:** Windows authentication protocols often allow the use of the NTLM hash directly without knowing the cleartext password.
*   **The Concept:** This is "Pass-the-Hash." Once the hash was found in the backup file, it didn't need to be cracked. It was simply passed to `impacket-psexec` to authenticate.
*   **Fix:** Disable NTLM where possible (move to Kerberos-only), use "Protected Users" groups, and implement Tiered Administration models to prevent credential overlap.
