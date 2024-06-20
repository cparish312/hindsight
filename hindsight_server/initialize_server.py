import os
import socket
import string
import secrets
import subprocess
from pathlib import Path

from config import API_KEY_FILE, HINDSIGHT_SERVER_DIR

import utils

base_dir = Path(os.path.dirname(os.path.abspath(__file__)))

INTERNET_URL = "" # Insert ngrok URL

def generate_random_key(length=30):
    # Define the possible characters to include in the key
    characters = string.ascii_letters + string.digits
    # Generate a random string of the specified length
    random_key = ''.join(secrets.choice(characters) for _ in range(length))
    return random_key

def get_local_ip():
    try:
        # Create a socket connection to a public DNS server
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        print("Error getting localurl", e)
    

def getinterneturl():
    return INTERNET_URL

def fill_in_file(file_path, dest_file_path, placeholder, replacement):
    with open(file_path, 'r') as file:
        file_contents = file.read()
    
    file_contents = file_contents.replace(placeholder, replacement)
    
    with open(dest_file_path, 'w') as file:
        file.write(file_contents)

def create_android_preferences(prefs):
    set_vars_str = ""
    for v, k in prefs.items():
        if isinstance(k, bool):
            if k:
                set_vars_str += f"""
        if (!prefs.contains({v})) {{
            prefs.edit().putBoolean({v}, true).apply()
        }}
        """
            else:
                set_vars_str += f"""
        if (!prefs.contains({v})) {{
            prefs.edit().putBoolean({v}, false).apply()
        }}
        """
        elif isinstance(k, int):
            set_vars_str += f"""
        if (!prefs.contains({v})) {{
            prefs.edit().putInt({v}, {k}).apply()
        }}
        """
        elif isinstance(k, str):
            if v in {"apikey", "localurl", "interneturl"}:
                set_vars_str += f"""
        prefs.edit().putString({v}, "{k}").apply()
        """
            else:
                set_vars_str += f"""
        if (!prefs.contains({v})) {{
            prefs.edit().putString({v}, "{k}").apply()
        }}
        """

    fill_in_file(base_dir / "res/Preferences_template.kt", base_dir / "../hindsight_android/app/src/main/java/com/connor/hindsight/utils/Preferences.kt", 
                "PYTHON_CONFIG_INSERT_HERE", set_vars_str)


def create_ssl_keys(local_ip):
    fill_in_file("./res/san.cnf", HINDSIGHT_SERVER_DIR / "san.cnf", 
                "PYTHON_CONFIG_INSERT_IP_HERE", local_ip)
    
    subprocess.call(["openssl", "req", "-new", "-nodes", "-keyout", HINDSIGHT_SERVER_DIR / "server.key", "-out",
                    HINDSIGHT_SERVER_DIR / "server.csr", "-config", HINDSIGHT_SERVER_DIR / "san.cnf"])
    
    subprocess.call(["openssl", "x509", "-req", "-days", "365", "-in", HINDSIGHT_SERVER_DIR / "server.csr",
                    "-signkey", HINDSIGHT_SERVER_DIR / "server.key", "-out", HINDSIGHT_SERVER_DIR / "server.crt",
                    "-extensions", "v3_ca", "-extfile", HINDSIGHT_SERVER_DIR / "san.cnf"])
    
    der_dest = base_dir / "../hindsight_android/app/src/main/res/raw/hindsight_server.der"
    subprocess.call(["openssl", "x509", "-outform", "der", "-in", HINDSIGHT_SERVER_DIR / "server.crt", "-out",
                    der_dest])

# Write to server info to 
# /Users/connorparish/code/hindsight/hindsight_android/app/src/main/java/com/connor/hindsight/utils/Preferences.kt
def initialize_server():
    utils.make_dir(HINDSIGHT_SERVER_DIR)
    local_ip = get_local_ip()
    prefs = {"screenrecordingenabled" : False,
         "recordwhenactive" : False,
         "screenshotsperautoupload" : 100,
         "apikey" : generate_random_key(),
         "localurl" : f"""https://{local_ip}:6000/""",
         "interneturl" : getinterneturl() 
         }
    
    create_android_preferences(prefs)
    
    with open(API_KEY_FILE, 'w') as outfile:
        outfile.write(prefs["apikey"])
    
    create_ssl_keys(local_ip)

    utils.make_dir(HINDSIGHT_SERVER_DIR / "raw_screenshots_tmp")

if __name__ == "__main__":
    initialize_server()