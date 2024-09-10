import os
import platform
from pathlib import Path

BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))

HOME = Path.home()

HINDSIGHT_SERVER_DIR = HOME / ".hindsight_server"
DATA_DIR = HINDSIGHT_SERVER_DIR / "data"
SCREENSHOTS_TMP_DIR = DATA_DIR / "raw_screenshots_tmp"
RAW_SCREENSHOTS_DIR = DATA_DIR / "raw_screenshots"
SERVER_LOG_FILE = DATA_DIR / "hindsight_server.log"
ANDROID_IDENTIFIERS_ALIAS_FILE = DATA_DIR / "android_identifiers.json"

API_KEY_FILE = HINDSIGHT_SERVER_DIR / "secret_api_key.txt"
if os.path.exists(API_KEY_FILE):
    with open(API_KEY_FILE, 'r') as infile:
        SECRET_API_KEY = infile.read().strip()
else:
    SECRET_API_KEY = "NONE"

RUNNING_PLATFORM = platform.system()

"""Should be able to run any LLMs in huggingface mlx-community if mac. Otherwise, any transformers LLAMA model"""
if RUNNING_PLATFORM == 'Darwin':
    LLM_MODEL_NAME = "mlx-community/Meta-Llama-3-8B-Instruct-8bit"
else:
    LLM_MODEL_NAME = "meta-llama/Meta-Llama-3.1-8B-Instruct" # For non-mac

"""Should be able to run any embedding models here:
https://github.com/taylorai/mlx_embedding_models/blob/main/src/mlx_embedding_models/registry.py
"""
MLX_EMBDEDDING_MODEL = "bge-large"
