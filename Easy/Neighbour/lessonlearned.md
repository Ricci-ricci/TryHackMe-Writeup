# Neighbour (Easy) — Lessons Learned

This room demonstrates one of the simplest yet most common web vulnerabilities:
**Insecure Direct Object Reference (IDOR) leading to unauthorized access to other users' profiles**

---

## 1) IDOR: when URL parameters control access without validation

### What happened
The application used a simple URL parameter to determine which user's profile to display:
- Normal user access: `?user=normaluser`
- Admin access: `?user=admin`

The application trusted the URL parameter without validating whether the current user should have access to the requested profile.

### Why this is dangerous
This is a classic **Insecure Direct Object Reference (IDOR)** vulnerability where:
- The application uses predictable identifiers (usernames)
- No access control checks verify if the current user can access the requested resource
- An attacker can simply modify the URL to access other users' data

### Practical takeaway
IDOR vulnerabilities are extremely common because they're easy to introduce during development:
- Developers focus on functionality, not access control
- URL parameters feel "internal" but are user-controllable
- Testing often focuses on happy paths, not unauthorized access attempts

---

## 2) Predictable identifiers make enumeration trivial

### The pattern
Using predictable identifiers like:
- `user=admin` 
- `user=john`
- `user=alice`
- `id=1`, `id=2`, `id=3`

Makes it trivial for attackers to:
- Guess other valid users
- Enumerate all user profiles
- Target specific high-value accounts (admin, root, etc.)

### Common predictable patterns
- Sequential numbers: `id=1,2,3...`
- Common usernames: `admin`, `administrator`, `root`, `test`
- Email formats: `user@domain.com`
- Employee IDs: `emp001`, `emp002`

### Defense: use unpredictable identifiers
Instead of predictable IDs, use:
- UUIDs: `550e8400-e29b-41d4-a716-446655440000`
- Random tokens: `a8f7b2c9d1e3f4g5h6j7k8l9`
- Hashed values with salt

---

## 3) Access control must be server-side, not client-side

### What the application probably did wrong
The vulnerable application likely:
1. Retrieved user data based solely on the URL parameter
2. Did not check if the current session/user has permission to view that data
3. Assumed URL parameters were "internal" and trusted

### Correct access control implementation
Every request should verify:
1. **Authentication**: Is this user logged in?
2. **Authorization**: Can this authenticated user access this specific resource?
3. **Resource ownership**: Does this user own/have rights to this data?

### Example of proper access control
```php
// BAD: Direct access without validation
$username = $_GET['user'];
$profile = getProfile($username);
displayProfile($profile);

// GOOD: Validate access rights
$requestedUser = $_GET['user'];
$currentUser = getCurrentAuthenticatedUser();

if (!canUserAccessProfile($currentUser, $requestedUser)) {
    return "Access Denied";
}

$profile = getProfile($requestedUser);
displayProfile($profile);
```

---

## 4) "Easy" vulnerabilities are often the most impactful

### Why IDOR is dangerous despite being simple
- **High impact**: Direct access to sensitive user data
- **Easy to exploit**: No special tools or complex techniques required
- **Scalable**: Can enumerate all users' data systematically
- **Hard to detect**: Looks like legitimate application usage in logs

### Real-world impact examples
- Healthcare: Access to other patients' medical records
- Banking: View other customers' account information
- Social media: Access private profiles and messages
- Corporate: Read other employees' sensitive documents

---

## 5) Testing methodology for IDOR vulnerabilities

### Manual testing approach
1. **Identify parameters**: Look for ID parameters in URLs, forms, API calls
2. **Note your own identifier**: Record your legitimate user ID/name
3. **Try other values**: Modify the parameter to access other resources
4. **Test systematically**: Try predictable values (admin, test, 1, 2, 3)
5. **Check all endpoints**: Test every page that accepts user identifiers

### Automated testing
- Use Burp Suite's Intruder to enumerate ID ranges
- Write scripts to test common username/ID patterns
- Use OWASP ZAP's active scan rules for IDOR detection

### Common locations to test
- Profile pages: `?user=`, `?profile=`, `?id=`
- Document access: `?doc=`, `?file=`, `?document_id=`
- API endpoints: `/api/user/{id}`, `/api/profile/{username}`
- Admin panels: `?admin_user=`, `?view_user=`

---

## 6) Defense strategies

### Technical controls
- **Use unpredictable identifiers** (UUIDs, random tokens)
- **Implement proper access control** on every endpoint
- **Validate user permissions** server-side for every request
- **Use indirect object references** (map user-provided IDs to internal IDs)

### Development practices
- **Secure by default**: Require explicit permission grants rather than denying access
- **Principle of least privilege**: Users should only access what they need
- **Code reviews**: Specifically look for access control in code reviews
- **Security testing**: Include IDOR testing in security test plans

### Monitoring and detection
- **Log access patterns**: Monitor for users accessing unusual resources
- **Rate limiting**: Prevent rapid enumeration attempts  
- **Anomaly detection**: Flag users accessing many different profiles
- **Regular security scans**: Automated testing for IDOR vulnerabilities

---

## 7) Why this room is valuable despite being "easy"

### Real-world prevalence
IDOR vulnerabilities are among the most common web security issues because:
- They're easy to introduce during development
- They're often overlooked in testing
- They can exist in every part of an application that handles user data

### Learning value
This "easy" room teaches:
- How simple vulnerabilities can have major impact
- The importance of access control validation
- That security isn't always about complex exploits
- How to think like an attacker when testing applications

---

## One-line takeaway
The simplest security test—changing a URL parameter—often reveals the biggest vulnerabilities, making proper access control validation essential for every user-accessible resource.