import os
from pathlib import Path

base_dir = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(base_dir, "data")
RAW_SCREENSHOTS_DIR = os.path.join(DATA_DIR, "raw_screenshots")
SERVER_LOG_FILE = os.path.join(DATA_DIR, "hindsight_server.log")

HOME = Path.home()
api_key_file = HOME / ".hindsight_server/secret_api_key.txt"
if os.path.exists(api_key_file):
    with open(api_key_file, 'r') as infile:
        SECRET_API_KEY = infile.read().strip()
else:
    SECRET_API_KEY = "NONE"