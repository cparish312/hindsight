import os
import re
import json
import html
import unicodedata
import hashlib
import requests
from sys import platform
from bs4 import BeautifulSoup
from bs4.element import Comment
from urllib.parse import urljoin
import numpy as np
import pandas as pd
from datetime import datetime, timezone

import tzlocal
from zoneinfo import ZoneInfo

from hindsight_applications.hindsight_feed.feed_config import HISTORY_PAGES_DIR, DATA_DIR, RESOURCES_DIR

local_timezone = tzlocal.get_localzone()
video_timezone = ZoneInfo("UTC")

def make_dir(d):
    if not os.path.exists(d):
        os.makedirs(d)

def positive_hash(obj):
    # Convert the object to string and encode to bytes
    obj_str = str(obj).encode()
    hash_object = hashlib.sha256(obj_str)  # Using SHA-256 hash function
    hash_digest = hash_object.digest()  # Get the bytes of the hash
    # Convert bytes to a positive integer
    hash_int = int.from_bytes(hash_digest, 'big') 
    return int(hash_int % ((1 << 61) - 1))

def get_html(url):
    url_hash = positive_hash(url)
    html_path = os.path.join(HISTORY_PAGES_DIR, f"{url_hash}.html")
    if os.path.exists(html_path):
        with open(html_path, 'r') as infile:
            return infile.read()
    try:
        response = requests.get(url, timeout=5)
        html_content = response.text.encode("utf-8")
    except:
        print(f"Failed request for {url}")
        html_content = ""
    with open(html_path, 'w') as outfile:
        outfile.write(str(html_content))
    return html_content

def get_thumbnail_url(source_url, html_content=None):
    if html_content is None:
        html_content = get_html(source_url)
    
    if html_content == "":
        return None
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # First, try to find the 'og:image' content
    og_image = soup.find('meta', property='og:image')
    if og_image and og_image.get('content'):
        image_url = og_image['content']
        # Convert relative URL to absolute URL using urljoin
        return urljoin(source_url, image_url)
    
    # If 'og:image' is not found, fall back to the first 'img' tag
    image_tag = soup.find('img')
    if image_tag and 'src' in image_tag.attrs:
        image_url = image_tag['src']
        # Convert relative URL to absolute URL using urljoin
        return urljoin(source_url, image_url)
    
    return None  # Return None if no suitable image is found

def add_datetime(df):
    df = df.copy()

    df['timestamp'] = df['timestamp'].fillna(0)

    df['datetime_utc'] = pd.to_datetime(df['timestamp'] / 1000000, unit='s', utc=True)
    df['datetime_local'] = df['datetime_utc'].apply(lambda x: x.replace(tzinfo=video_timezone).astimezone(local_timezone))
    return df

def is_local_url(url):
    # Define criteria for a local URL (could be refined based on your requirements)
    if url.startswith('http://') or url.startswith('https://'):
        return False
    if url.startswith('/local/docs/'):
        return True
    return not (":" in url or "//" in url)

def tag_visible(element):
    if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
        return False
    if isinstance(element, Comment):
        return False
    return True

def clean_text(text):
    # Replace escape sequences '\\n', '\\t', '\\r' with their actual characters
    text = text.replace('\\n', '\n').replace('\\t', ' ').replace('\\r', ' ')
    
    # Attempt to decode unicode escape sequences
    try:
        text = text.encode('utf-8').decode('unicode_escape')
    except UnicodeDecodeError:
        pass  # If decoding fails, leave the text as is
    
    text = html.unescape(text)
    
    # Replace multiple newlines in a row with a single newline
    text = re.sub(r'\n\s*\n+', '\n', text)
    
    # Remove multiple spaces
    text = re.sub(' +', ' ', text)
    
    # Normalize unicode characters
    text = unicodedata.normalize('NFC', text)
    
    # Remove any remaining non-printable characters except newline
    text = ''.join(c for c in text if c.isprintable() or c == '\n')
    
    # Strip leading and trailing whitespace and newlines
    text = text.strip()
    
    return text

def html_to_text(body, clean=True):
    soup = BeautifulSoup(body, 'html.parser')
    texts = soup.findAll(text=True)
    visible_texts = filter(tag_visible, texts)  
    texts = list()
    for t in visible_texts:
        t = t.strip()
        texts.append(t)
    text = u" ".join(texts).strip()
    if clean:
        text = clean_text(text)
    return text

def path_to_url(path: str):
    if platform == "win32":
        return path.replace('\\', '/')
    return path

def url_to_path(url: str):
    if platform == "win32":
        return url.replace('/', '\\')
    return url

def datetime_to_utc_timestamp(date):
    if isinstance(date, datetime):
        # Ensure the datetime is in UTC before converting to timestamp
        if date.tzinfo is None:
            # If the datetime is naive (no timezone), assume it is UTC
            date = date.replace(tzinfo=timezone.utc)
        else:
            # Convert it to UTC if it has a timezone
            date = date.astimezone(timezone.utc)

        # Convert to Unix timestamp in milliseconds
        date = int(date.timestamp()) * 1000
    return date

def get_allow_urls():
    allow_urls_file = os.path.join(RESOURCES_DIR, 'allow_multiple_urls.json')
    if not os.path.exists(allow_urls_file):
        return set()
    with open(allow_urls_file, 'r') as file:
        data = json.load(file)
        allow_urls = data['allow_urls']
    return set(allow_urls)

def content_to_df(content):
    content_list = list()
    for c in content:
        d = c.__dict__.copy()
        if "content_generator_id" in d: # is content
            gen_spec_data = c.content_generator_specific_data.copy()
            del gen_spec_data['score']
            del gen_spec_data['id']
            d.update(gen_spec_data)
        content_list.append(d)
    return pd.DataFrame(content_list)