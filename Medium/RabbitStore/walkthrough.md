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
