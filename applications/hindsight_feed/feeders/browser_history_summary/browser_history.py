import os
from sys import platform
import shutil
import sqlite3
from pathlib import Path
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import webbrowser

import tzlocal
from zoneinfo import ZoneInfo

# Local timezone setup
local_timezone = tzlocal.get_localzone()
video_timezone = ZoneInfo("UTC")

from utils import positive_hash
from config import DATA_DIR

# Function to create directory if it doesn't exis

def find_firefox_profile():
    if platform == "linux" or platform == "linux2":
        profile_path = Path(os.path.expanduser("~/.mozilla/firefox"))
    elif platform == "darwin":
        profile_path = Path(os.path.expanduser("~/Library/Application Support/Firefox/Profiles"))
    elif platform == "win32":
        profile_path = Path(os.path.expanduser(r"~\AppData\Roaming\Mozilla\Firefox\Profiles"))

    profiles = list(profile_path.glob("*.default-release"))
    if profiles:
        return max(profiles, key=os.path.getmtime)
    return None

firefox_profile = find_firefox_profile()
if firefox_profile:
    FIREFOX_HISTORY_FILE = firefox_profile / "places.sqlite"
else:
    FIREFOX_HISTORY_FILE = None

# Define paths based on the operating system
if platform == "linux" or platform == "linux2":
    CHROME_HISTORY_FILE = Path(os.path.expanduser("~/.config/google-chrome/Default/History"))
    BRAVE_HISTORY_FILE = Path(os.path.expanduser("~/.config/BraveSoftware/Brave-Browser/Default/History"))
    ARC_HISTORY_FILE = Path(os.path.expanduser("~/.arc/User Data/Default/History"))
elif platform == "darwin":
    CHROME_HISTORY_FILE = Path(os.path.expanduser("~/Library/Application Support/Google/Chrome/Default/History"))
    BRAVE_HISTORY_FILE = Path(os.path.expanduser("~/Library/Application Support/BraveSoftware/Brave-Browser/Default/History"))
    ARC_HISTORY_FILE = Path(os.path.expanduser("~/Library/Application Support/Arc/User Data/Default/History"))
elif platform == "win32":
    CHROME_HISTORY_FILE = Path(os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data\Default\History"))
    BRAVE_HISTORY_FILE = Path(os.path.expanduser(r"~\AppData\Local\BraveSoftware\Brave-Browser\User Data\Default\History"))
    ARC_HISTORY_FILE = Path(os.path.expanduser(r"~\AppData\Local\Arc\User Data\User Data\Default\History"))

# Temporary files for processing history
FIREFOX_TMP_FILE = Path(os.path.join(DATA_DIR, "firefox_history.sqlite"))
CHROME_TMP_FILE = Path(os.path.join(DATA_DIR, "chrome_history.sqlite"))
BRAVE_TMP_FILE = Path(os.path.join(DATA_DIR, "brave_history.sqlite"))
ARC_TMP_FILE = Path(os.path.join(DATA_DIR, "arc_history.sqlite"))

# Function to add datetime information to DataFrame
def add_datetime(df):
    df = df.copy()
    df['datetime_utc'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)
    df['datetime_local'] = df['datetime_utc'].apply(lambda x: x.replace(tzinfo=video_timezone).astimezone(local_timezone))
    return df

# Function to retrieve Firefox browsing history
def get_firefox_history(db_file=FIREFOX_HISTORY_FILE, db_file_tmp=FIREFOX_TMP_FILE):
    """Retrieves Firefox browsing history."""
    if db_file is None or not db_file.exists():
        return pd.DataFrame()
    shutil.copy(db_file, db_file_tmp)
    conn = sqlite3.connect(db_file_tmp)
    history = pd.read_sql("SELECT * FROM moz_places", con=conn)

    # Drop entries with missing titles
    history = history.dropna(subset=['title'])

    # Process history data
    history['timestamp'] = history['last_visit_date'].fillna(0) / 1000000
    history['description'] = history['description'].fillna("No description")
    history['title_description'] = history.apply(lambda row: row["title"] + ":" + row['description'], axis=1)
    history['browser'] = "Firefox"
    print(f"{len(history)} urls from Firefox")
    return history

# Function to retrieve Chrome browsing history
def get_chrome_history(db_file=CHROME_HISTORY_FILE, db_file_tmp=CHROME_TMP_FILE):
    """Retrieves Chrome browsing history."""
    if not db_file.exists():
        return pd.DataFrame()
    
    # Copy the database to avoid locking issues
    shutil.copy(db_file, db_file_tmp)
    conn = sqlite3.connect(db_file_tmp)

    # Query the history database
    query = """
    SELECT 
        urls.url, 
        urls.title, 
        visits.visit_time/1000000 - 11644473600 AS timestamp 
    FROM urls, visits 
    WHERE urls.id = visits.url;
    """
    
    history = pd.read_sql(query, con=conn)

    # Drop entries with missing titles
    history = history.dropna(subset=['title'])

    # Process history data
    history['description'] = history['title'].fillna("No description")
    history['title_description'] = history.apply(lambda row: row["title"] + ":" + row['description'], axis=1)
    history['browser'] = "Chrome"
    print(f"{len(history)} urls from Chrome")
    return history

# Function to retrieve Brave browsing history
def get_brave_history(db_file=BRAVE_HISTORY_FILE, db_file_tmp=BRAVE_TMP_FILE):
    """Retrieves Brave browsing history."""
    if not db_file.exists():
        return pd.DataFrame()
    
    # Copy the database to avoid locking issues
    shutil.copy(db_file, db_file_tmp)
    conn = sqlite3.connect(db_file_tmp)

    # Query the history database
    query = """
    SELECT 
        urls.url, 
        urls.title, 
        visits.visit_time/1000000 - 11644473600 AS timestamp 
    FROM urls, visits 
    WHERE urls.id = visits.url;
    """
    
    history = pd.read_sql(query, con=conn)

    # Drop entries with missing titles
    history = history.dropna(subset=['title'])

    # Process history data
    history['description'] = history['title'].fillna("No description")
    history['title_description'] = history.apply(lambda row: row["title"] + ":" + row['description'], axis=1)
    history['browser'] = "Brave"
    print(f"{len(history)} urls from Brave")
    return history

# Function to retrieve Arc browsing history
def get_arc_history(db_file=ARC_HISTORY_FILE, db_file_tmp=ARC_TMP_FILE):
    """Retrieves Arc browsing history."""
    if not db_file.exists():
        return pd.DataFrame()
    
    # Copy the database to avoid locking issues
    shutil.copy(db_file, db_file_tmp)
    conn = sqlite3.connect(db_file_tmp)

    # Query the history database
    query = """
    SELECT 
        urls.url, 
        urls.title, 
        visits.visit_time/1000000 - 11644473600 AS timestamp 
    FROM urls, visits 
    WHERE urls.id = visits.url;
    """
    
    history = pd.read_sql(query, con=conn)

    # Drop entries with missing titles
    history = history.dropna(subset=['title'])

    # Process history data
    history['description'] = history['title'].fillna("No description")
    history['title_description'] = history.apply(lambda row: row["title"] + ":" + row['description'], axis=1)
    history['browser'] = "Arc"
    print(f"{len(history)} urls from Arc")
    return history

# Function to retrieve and preprocess browser history from all browsers
def get_browser_history(kw_filter=True):
    """Retrieves and pre-processes browser history from all found browsers."""
    histories = list()
    histories.append(get_firefox_history())
    histories.append(get_chrome_history())
    histories.append(get_brave_history())
    histories.append(get_arc_history())
    
    history = pd.concat(histories)
    if len(history) == 0:
        print("No history found")
        return history
    history = add_datetime(history)
    history = history.sort_values(by='timestamp', ascending=True)

    # Drop duplicate URLs
    history = history.drop_duplicates(subset=['url'], keep='last')

    # Apply keyword filtering if enabled
    if kw_filter:
        filter_keywords = ["Inbox", "Gmail", "ChatGPT", "Home", "LinkedIn", "Sign In", "Google Slides", "Google Search"]
        for kw in filter_keywords:
            history = history.loc[~(history['title_description'].str.lower().str.contains(kw.lower()))]

    history = history.loc[~(history['url'].str[:8] == "file:///")]

    history['url_hash'] = history['url'].apply(lambda u : positive_hash(u)) # Positive hash
    return history
