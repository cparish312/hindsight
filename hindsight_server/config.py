import os
import platform
import json
from pathlib import Path

BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))

HOME = Path.home()

HINDSIGHT_SERVER_DIR = HOME / ".hindsight_server"

DATA_DIR = HINDSIGHT_SERVER_DIR / "data"
USER_SETTINGS_FILE = HINDSIGHT_SERVER_DIR / "user_settings.json"
API_KEY_FILE = HINDSIGHT_SERVER_DIR / "secret_api_key.txt"

SCREENSHOTS_TMP_DIR = DATA_DIR / "raw_screenshots_tmp"
RAW_SCREENSHOTS_DIR = DATA_DIR / "raw_screenshots"
SERVER_LOG_FILE = DATA_DIR / "hindsight_server.log"
ANDROID_IDENTIFIERS_ALIAS_FILE = DATA_DIR / "android_identifiers.json"

if os.path.exists(API_KEY_FILE):
    with open(API_KEY_FILE, 'r') as infile:
        SECRET_API_KEY = infile.read().strip()
else:
    SECRET_API_KEY = "NONE"

RUNNING_PLATFORM = platform.system()

"""Should be able to run any LLMs in huggingface mlx-community if mac. Otherwise, any transformers LLAMA model"""
if RUNNING_PLATFORM == 'Darwin':
    LLM_MODEL_NAME = "mlx-community/Llama-3.2-3B-Instruct"
else:
    LLM_MODEL_NAME = "meta-llama/Llama-3.2-3B-Instruct" # For non-mac

"""Should be able to run any embedding models here:
https://github.com/taylorai/mlx_embedding_models/blob/main/src/mlx_embedding_models/registry.py
"""
MLX_EMBDEDDING_MODEL = "bge-large"

if os.path.isfile(USER_SETTINGS_FILE):
    with open(USER_SETTINGS_FILE) as user_file:
        user_settings = json.load(user_file)
        print('Applying user settings to configuration:', user_settings)
        LLM_MODEL_NAME = user_settings['LLM_MODEL_NAME']
else:
    print('Using default configuration')
