import os
import hashlib
import requests
from bs4 import BeautifulSoup
from bs4.element import Comment
from urllib.parse import urljoin
import numpy as np
import pandas as pd

import tzlocal
from zoneinfo import ZoneInfo

from config import HISTORY_PAGES_DIR

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

def html_to_text(body):
    soup = BeautifulSoup(body, 'html.parser')
    texts = soup.findAll(text=True)
    visible_texts = filter(tag_visible, texts)  
    texts = list()
    for t in visible_texts:
        t = t.strip()
        texts.append(t)
    return u" ".join(texts).strip()