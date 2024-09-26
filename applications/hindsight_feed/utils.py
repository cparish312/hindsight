import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import numpy as np
import pandas as pd

import tzlocal
from zoneinfo import ZoneInfo

local_timezone = tzlocal.get_localzone()
video_timezone = ZoneInfo("UTC")

def make_dir(d):
    if not os.path.exists(d):
        os.makedirs(d)

def get_thumbnail_url(source_url, html_content=None):
    if html_content is None:
        try:
            response = requests.get(source_url)
            html_content = response.content
        except Exception as e:
            print(f"Failed to get thumbnail for {source_url} with error: {e}")
            return None
        if response.status_code != 200:
            return None  # Ensure the request was successful

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