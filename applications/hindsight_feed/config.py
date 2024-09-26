import os

base_dir = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(base_dir, "data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

DB_TMP_FILE = os.path.join(DATA_DIR, "places.sqlite")
GENERATOR_DATA_DIR = os.path.join(DATA_DIR, "generator_data")
