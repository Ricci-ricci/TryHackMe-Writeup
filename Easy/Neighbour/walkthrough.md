# TryHackMe — Neighbour (Easy) Walkthrough

> Room: **Neighbour** (Easy)  
> Goal: Exploit an Insecure Direct Object Reference (IDOR) vulnerability to access other users' profiles.

This box demonstrates a classic web application vulnerability:
**IDOR (Insecure Direct Object Reference) → access admin profile → retrieve sensitive information**

---

## 1) Understanding the Target Application

### 1.1 Application description
The room describes a cloud authentication service called "Authentication Anywhere" that allows users to:
- Log in from anywhere with username/password
- Access their user profiles
- Store personal information securely (supposedly)

### 1.2 The vulnerability hint
The description suggests: "You definitely wouldn't be able to find any secrets that other people have in their profile, right?"

This is a strong hint pointing toward an **IDOR vulnerability** where you can access other users' data.

---

## 2) Initial Access and Exploration

### 2.1 Access the application
Navigate to the provided URL to access the authentication service.

### 2.2 Create or use provided credentials
Either register a new account or use any provided test credentials to log into the application.

### 2.3 Explore your profile
After logging in, examine:
- Your profile page
- The URL structure
- Any user-specific identifiers in the URL
- What information is displayed

---

## 3) Identifying the IDOR Vulnerability

### 3.1 Analyze the URL structure
Look for patterns in the URL when viewing your profile, such as:
- `?user=yourname`
- `?id=123`
- `/profile/user123`
- `/users/yourname`

### 3.2 Understand the vulnerability
IDOR occurs when an application:
1. Uses direct references to objects (like usernames or IDs)
2. Fails to properly verify that the current user should have access to the requested object
3. Allows attackers to modify the reference to access other users' data

---

## 4) Exploiting the IDOR Vulnerability

### 4.1 The simple exploit
Based on the walkthrough hint, the exploitation is straightforward:

**Change the URL parameter to target the admin user:**

If the URL structure is:
```
http://example.com/profile?user=yourname
```

Simply change it to:
```
http://example.com/profile?user=admin
```

### 4.2 Alternative parameter names
If `user=admin` doesn't work, try other common variations:
- `?username=admin`
- `?id=admin`
- `?account=admin`
- `?profile=admin`

### 4.3 Numeric IDs
If the application uses numeric user IDs, try:
- `?id=1` (admin is often user ID 1)
- `?id=0`
- Increment through numbers: `?id=2`, `?id=3`, etc.

---

## 5) Accessing the Admin Profile

### 5.1 Direct URL manipulation
The most direct approach:
1. Identify your current profile URL
2. Replace your username/ID with `admin`
3. Navigate to the modified URL

### 5.2 Expected results
If successful, you should:
- See the admin user's profile information
- Find sensitive data that regular users shouldn't access
- Discover flags, credentials, or other secrets

---

## 6) Information Gathering

### 6.1 Document findings
Record any sensitive information discovered in the admin profile:
- Personal information
- System credentials
- Internal documentation
- Flags or secrets
- Configuration details

### 6.2 Explore other users
Once you've confirmed the IDOR vulnerability works, try accessing other user profiles:
- Common usernames: `administrator`, `root`, `test`, `guest`
- Sequential user IDs if numeric
- Service accounts: `service`, `system`, `api`

---

## 7) Complete the Objectives

### 7.1 Submit findings
Use any discovered information to complete the room's objectives, which may include:
- Specific user data
- Hidden flags
- Credentials for other systems

---

## 8) Alternative Exploitation Methods

### 8.1 Burp Suite interception
If direct URL manipulation doesn't work:
1. Use Burp Suite to intercept profile requests
2. Modify the user parameter in the HTTP request
3. Forward the modified request

### 8.2 Cookie manipulation
Some applications store user identifiers in cookies:
1. Examine cookies after login
2. Look for user IDs or usernames
3. Modify cookie values to target other users

### 8.3 POST request manipulation
If profile access uses POST requests:
1. Intercept the POST request with Burp Suite
2. Modify user parameters in the request body
3. Forward the modified request

---

## Summary (attack methodology)

1. **Access** → log into the application with valid credentials
2. **Analyze** → examine URL structure and user identification methods
3. **Identify** → recognize IDOR vulnerability in user profile access
4. **Exploit** → modify URL parameter to `user=admin`
5. **Extract** → gather sensitive information from admin profile
6. **Complete** → use discovered information to finish objectives

---

## Notes / Technical Details

### What makes this an IDOR vulnerability
- **Direct reference**: URL directly references user objects
- **Insecure**: No access control verification
- **Predictable**: Admin username is easily guessable

### Why this is dangerous in real applications
- Access to sensitive personal data
- Potential privilege escalation
- Privacy violations and data breaches
- Compliance violations (GDPR, HIPAA, etc.)

---

## Defense recommendations

### For developers
- **Implement access controls**: Verify user permissions before displaying data
- **Use indirect references**: Map internal IDs to session-specific identifiers
- **Validate authorization**: Check if current user should access requested resource
- **Audit logging**: Log all profile access attempts for monitoring

### For security teams
- **Regular testing**: Include IDOR testing in security assessments
- **Code review**: Look for direct object references in access control logic
- **Penetration testing**: Test parameter manipulation during security audits
- **User education**: Train developers on secure coding practices