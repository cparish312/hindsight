import os
import socket
from pathlib import Path

base_dir = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(base_dir, "data")
RAW_SCREENSHOTS_DIR = os.path.join(DATA_DIR, "raw_screenshots")
SERVER_LOG_FILE = os.path.join(DATA_DIR, "hindsight_server.log")

HOME = Path.home()
HINDSIGHT_SERVER_DIR = HOME / ".hindsight_server"
API_KEY_FILE = HINDSIGHT_SERVER_DIR / "secret_api_key.txt"
if os.path.exists(API_KEY_FILE):
    with open(API_KEY_FILE, 'r') as infile:
        SECRET_API_KEY = infile.read().strip()
else:
    SECRET_API_KEY = "NONE"
