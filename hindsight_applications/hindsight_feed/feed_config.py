import os

base_dir = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(base_dir, "data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

DB_TMP_FILE = os.path.join(DATA_DIR, "places.sqlite")
GENERATOR_DATA_DIR = os.path.join(DATA_DIR, "generator_data")
RANKER_DATA_DIR = os.path.join(DATA_DIR, "rankers_data")

HISTORY_PAGES_DIR = os.path.join(DATA_DIR, "history_pages")
os.makedirs(HISTORY_PAGES_DIR, exist_ok=True)

exa_api_key_f = os.path.join(DATA_DIR, "exa_api.key")
if os.path.exists(exa_api_key_f):
    with open(exa_api_key_f, 'r') as infile:
        EXA_API_KEY = infile.read().strip()
else:
    raise(ValueError(f"Missing {exa_api_key_f}"))