import numpy as np
import pandas as pd
from statistics import mean

import tzlocal
from zoneinfo import ZoneInfo

local_timezone = tzlocal.get_localzone()
video_timezone = ZoneInfo("UTC")

def add_datetimes(df):
    """Adds UTC datetime and local datetime columns to a DataFrame with a UTC timestamp in milliseconds"""
    df['datetime_utc'] = pd.to_datetime(df['timestamp'] / 1000, unit='s', utc=True)
    df['datetime_local'] = df['datetime_utc'].apply(lambda x: x.replace(tzinfo=video_timezone).astimezone(local_timezone))
    return df

def add_sep_ids(df, new_threshold, var_name):
        df['y_difference'] = df['y'].diff()
        new_var_start = (df['y_difference'] > new_threshold)
        df[var_name] = new_var_start.cumsum()
        return df

def convert_to_continuos_str(df, newline_threshold):
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

def ocr_results_to_str(ocr_result):
    ocr_result = ocr_result.copy()
    if set(ocr_result['text']) == {None}:
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
        frame_total_text += "\n" +  "-" * 20 + "\n"
    return frame_total_text