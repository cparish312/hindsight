import os
import json
import hashlib
import numpy as np
import pandas as pd
from collections import defaultdict
from statistics import mean
from datetime import timedelta

import tzlocal
from zoneinfo import ZoneInfo

local_timezone = tzlocal.get_localzone()
video_timezone = ZoneInfo("UTC")

from config import ANDROID_IDENTIFIERS_ALIAS_FILE

def make_dir(d):
    if not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

remove_applications = {"com-google-android-inputmethod-latin"}
def impute_applications(df):
    df_copy = df.copy()
    
    last_non_keyboard = None
    for index, row in df_copy.iterrows():
        if row["application"] in remove_applications:
            if last_non_keyboard is not None:
                df_copy.loc[index, "application"] = last_non_keyboard
        else:
            last_non_keyboard = row["application"]
    
    return df_copy

def add_datetimes(df):
    """Adds UTC datetime and local datetime columns to a DataFrame with a UTC timestamp in milliseconds"""
    df['datetime_utc'] = pd.to_datetime(df['timestamp'] / 1000, unit='s', utc=True)
    df['datetime_local'] = df['datetime_utc'].apply(lambda x: x.replace(tzinfo=video_timezone).astimezone(local_timezone))
    return df

def add_usage_ids(df, new_usage_threshold=timedelta(seconds=120)):
    """Adds a column that identifies what 'usage' the frame belongs to. A new usage is defined
    by a time difference of new_usage_threshold
    """
    df = df.sort_values(by='datetime_utc')
    df['time_difference'] = df['datetime_utc'].diff()
    new_usage_start = (df['time_difference'] > new_usage_threshold)
    df['usage_id'] = new_usage_start.cumsum()
    return df

def add_sep_ids(df, new_threshold, var_name):
    """Adds seperations based on y distance between OCR results."""
    df['y_difference'] = df['y'].diff()
    new_var_start = (df['y_difference'] > new_threshold)
    df[var_name] = new_var_start.cumsum()
    return df

text_split_str = "\n" +  "-" * 20 + "\n"
def convert_to_continuos_str(df, newline_threshold):
    """Converts a paragraph DataFrame into a str. It tries to maintain relative spaces and tabs."""
    para_df = df.copy()
    para_df['char_width'] = para_df['w'] / para_df['text'].str.len()
    average_char_width = para_df['char_width'].mean()
    para_df = add_sep_ids(para_df, new_threshold=newline_threshold, var_name="line_id")
    
    para_df['x'] = para_df['x'].round(4)
    para_df['y'] = para_df['y'].round(4)
    df_sorted = para_df.sort_values(by=['line_id', 'x'], ascending=True).reset_index(drop=True)

    # Space and tab thresholds
    space_width = average_char_width
    tab_threshold = space_width * 4  # Four times the space width for a tab
    def get_gap_str(gap):
        if gap > tab_threshold:
            num_tabs = int(np.round(gap / tab_threshold))
            tabs_str = ' ' * max(1, num_tabs)  # Ensure at least one space
            return tabs_str
        elif gap > space_width:
            num_spaces = int(np.round(gap / space_width))
            space_str = ' ' * max(1, num_spaces)  # Ensure at least one space
            return space_str
        return ''

    # Initialize variables
    min_x = min(df_sorted['x'])
    final_text = []
    for line_id in df_sorted.line_id.unique():
        line_df = df_sorted.loc[df_sorted['line_id'] == line_id]
        line_text = ""
        prev_x = min_x
        for i, row in line_df.iterrows():
            line_text += get_gap_str(row['x'] - prev_x)
            prev_x = row['x']
            line_text += row['text']
        final_text.append(line_text)        
    return "\n".join(final_text)

def ocr_results_to_str(ocr_result, text_conf_thresh=0.7):
    """Converts OCR results for a frame into paragraphs based on y distance. Converts each
    paragraph into a str and finally combines all of the paragraph strs into a single str
    to represent the OCR results of the frame.
    """
    ocr_result = ocr_result.copy()
    ocr_result = ocr_result.loc[ocr_result['conf'] >= text_conf_thresh]
    if set(ocr_result['text']) == {None} or len(ocr_result) == 0:
        return ""
    avg_h = mean(ocr_result['h'])
    new_para_thresh = avg_h * 2

    ocr_result = ocr_result.sort_values(by=['y', 'x'])
    
    ocr_result = add_sep_ids(ocr_result, new_para_thresh, "para_id")

    frame_total_text = ""
    for para_id in ocr_result.para_id.unique():
        para_df = ocr_result.loc[ocr_result['para_id'] == para_id]
        para_str = convert_to_continuos_str(para_df, newline_threshold=avg_h/2)
        frame_total_text += para_str
        frame_total_text += text_split_str
    return frame_total_text

known_applications_d = {""} # Could convert the android identifiers to normal application names
def get_screenshot_preprompt(application, timestamp):
    return f"""Description: Text from a screenshot of {application} with UTC timestamp {timestamp}:""" + text_split_str

def get_preprompted_text(ocr_result, application, timestamp):
    """Used for preprompting chromadb documents and preprompting before feeding to an LLM."""
    frame_cleaned_text = ocr_results_to_str(ocr_result)
    frame_text = get_screenshot_preprompt(application, timestamp) + frame_cleaned_text
    return frame_text

def get_context_around_frame_id(frame_id, frames_df, db, context_buffer=5):
    """Used by the Long Context Querying method. Pulls context_buffer frames before and after 
    the provided frame_id and combines them into a single str. It does some deduplication but
    keeps the entire text of the frame_id passed.
    """
    frame_application = frames_df.loc[frames_df['id'] == frame_id].iloc[0]['application']
    application_df = frames_df.loc[frames_df['application'] == frame_application].reset_index(drop=True)
    frame_index = int(application_df.index.get_loc(application_df[application_df['id'] == frame_id].index[0]))
    application_df = application_df.iloc[frame_index-context_buffer:frame_index+context_buffer]
    ocr_results_df = db.get_frames_with_ocr(frame_ids=set(application_df['id']))
    text_list = list()
    for i, row in application_df.iterrows():
        ocr_res = ocr_results_df.loc[ocr_results_df['frame_id'] == row['id']]
        cleaned_res = get_preprompted_text(ocr_res, row['application'], row['timestamp'])
        for t in cleaned_res.split(text_split_str):
            if t not in text_list or row['id'] == frame_id:
                text_list.append(t)
    return text_split_str.join(text_list)

def get_identifiers_to_alias():
    if not os.path.exists(ANDROID_IDENTIFIERS_ALIAS_FILE):
        return {}
    
    with open(ANDROID_IDENTIFIERS_ALIAS_FILE, 'r') as infile:
        id_to_alias = json.load(infile)

    id_to_alias_cleaned = {}
    for k, v in id_to_alias.items():
        if v is None:
            id_to_alias_cleaned[k] = k
        else:
            id_to_alias_cleaned[k] = v
    return id_to_alias_cleaned

def get_aliases_identifiers(aliases):
    id_to_alias = get_identifiers_to_alias()
    identifiers = set()
    for i, a in id_to_alias.items():
        if a in aliases:
            identifiers.add(i)
    return identifiers

def save_identifiers_to_alias(id_to_alias):
    with open(ANDROID_IDENTIFIERS_ALIAS_FILE, 'w') as outfile:
        json.dump(id_to_alias, outfile, indent=4)

BUF_SIZE = 65536
def hash_file(f_path):
    md5 = hashlib.md5()

    with open(f_path, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            md5.update(data)
    
    return md5.hexdigest()