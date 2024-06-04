import pandas as pd

import tzlocal
from zoneinfo import ZoneInfo

local_timezone = tzlocal.get_localzone()
video_timezone = ZoneInfo("UTC")

def add_datetimes(df):
    """Adds UTC datetime and local datetime columns to a DataFrame with a UTC timestamp in milliseconds"""
    df['datetime_utc'] = pd.to_datetime(df['timestamp'] / 1000, unit='s', utc=True)
    df['datetime_local'] = df['datetime_utc'].apply(lambda x: x.replace(tzinfo=video_timezone).astimezone(local_timezone))
    return df