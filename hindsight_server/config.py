import os
from pathlib import Path

BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
ANDROID_IDENTIFIERS_ALIAS_FILE = os.path.join(BASE_DIR, "res/android_identifiers.json")

HOME = Path.home()
HINDSIGHT_SERVER_DIR = HOME / ".hindsight_server"
DATA_DIR = os.path.join(HINDSIGHT_SERVER_DIR, "data")
RAW_SCREENSHOTS_DIR = os.path.join(DATA_DIR, "raw_screenshots")
SERVER_LOG_FILE = os.path.join(DATA_DIR, "hindsight_server.log")

API_KEY_FILE = HINDSIGHT_SERVER_DIR / "secret_api_key.txt"
if os.path.exists(API_KEY_FILE):
    with open(API_KEY_FILE, 'r') as infile:
        SECRET_API_KEY = infile.read().strip()
else:
    SECRET_API_KEY = "NONE"

"""Should be able to run any LLMs in huggingface mlx-community."""
MLX_LLM_MODEL = "mlx-community/Meta-Llama-3-8B-Instruct-8bit"

"""Should be able to run any embedding models here:
https://github.com/taylorai/mlx_embedding_models/blob/main/src/mlx_embedding_models/registry.py
"""
MLX_EMBDEDDING_MODEL = "bge-large"