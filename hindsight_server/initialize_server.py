import socket
import string
import secrets

from config import API_KEY_FILE

INTERNET_URL = "" # Insert ngrok URL

def generate_random_key(length=30):
    # Define the possible characters to include in the key
    characters = string.ascii_letters + string.digits
    # Generate a random string of the specified length
    random_key = ''.join(secrets.choice(characters) for _ in range(length))
    return random_key

def getlocalurl():
    try:
        # Create a socket connection to a public DNS server
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        localip = s.getsockname()[0]
        s.close()
        return f"""https://{localip}:6000/"""
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

# Write to server info to 
# /Users/connorparish/code/hindsight/hindsight_android/app/src/main/java/com/connor/hindsight/utils/Preferences.kt
def initialize_server():
    prefs = {"screenrecordingenabled" : False,
         "recordwhenactive" : False,
         "screenshotsperautoupload" : 100,
         "apikey" : generate_random_key(),
         "localurl" :  getlocalurl(),
         "interneturl" : getinterneturl() 
         }
    
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

    fill_in_file("./res/Preferences_template.kt", "../hindsight_android/app/src/main/java/com/connor/hindsight/utils/Preferences.kt", 
                "PYTHON_CONFIG_INSERT_HERE", set_vars_str)
    
    with open(API_KEY_FILE, 'w') as outfile:
        outfile.write(prefs["apikey"])

if __name__ == "__main__":
    initialize_server()