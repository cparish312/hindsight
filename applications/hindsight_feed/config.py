import os

base_dir = os.path.dirname(os.path.abspath(__file__))

FIREFOX_DB_FILE = "/Users/connorparish/Library/Application Support/Firefox/Profiles/vze01ffv.default-release/places.sqlite"
DATA_DIR = os.path.join(base_dir, "data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

DB_TMP_FILE = os.path.join(DATA_DIR, "places.sqlite")
GENERATOR_DATA_DIR = os.path.join(DATA_DIR, "generator_data")

EXA_API_KEY = "6d382b4c-1e88-4e00-958d-1d69182b9c1b"
