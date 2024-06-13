import os
import glob
import multiprocessing
from ocrmac import ocrmac
import pandas as pd

from PIL import Image

import tzlocal
from zoneinfo import ZoneInfo

from config import RAW_SCREENSHOTS_DIR
from db import HindsightDB

local_timezone = tzlocal.get_localzone()
video_timezone = ZoneInfo("UTC")

db = HindsightDB()

def get_images_df(screenshots_dir):
        images_l = list()
        for f in glob.glob(f"{screenshots_dir}/*/*/*/*/*.jpg"):
            filename = f.split('/')[-1]
            filename_s = filename.replace(".jpg", "").split("_")
            application = filename_s[0]
            timestamp = int(filename_s[1])
            images_l.append({"path" : f, "timestamp" : timestamp, "app" : application})
        images_df = pd.DataFrame(images_l)
        images_df['datetime_utc'] = pd.to_datetime(images_df['timestamp'] / 1000, unit='s', utc=True)
        images_df['datetime_local'] = images_df['datetime_utc'].apply(lambda x: x.replace(tzinfo=video_timezone).astimezone(local_timezone))
        return images_df.sort_values(by='datetime_local', ascending=False)

def extract_text_from_frame(path):
    ocr_res = ocrmac.OCR(Image.open(path), recognition_level='accurate').recognize(px=True) # px converts to pil coordinates
    # x, y, w, h, text, conf
    ocr_res = [(r[2][0], r[2][1], r[2][2]-r[2][0], r[2][3]-r[2][1], r[0], r[1]) for r in ocr_res]
    if len(ocr_res) == 0:
        ocr_res = [[0, 0, 0, 0, None, 0]]
    return ocr_res

def run_ocr(frame_id, path=None):
    path = db.get_frames(frame_ids=[frame_id]).iloc[0]['path'] if path is None else path
    ocr_res = extract_text_from_frame(path)
    db.insert_ocr_results(frame_id, ocr_res)
    print(f"Inserted ocr results for {path}")
    return ocr_res

if __name__ == "__main__":
    images_df = get_images_df(RAW_SCREENSHOTS_DIR)
    frames_df = db.get_frames()
    no_frames_df = images_df.loc[~images_df['path'].isin(set(frames_df['path']))]

    for i, row in no_frames_df.iterrows():
        db.insert_frame(row['timestamp'], row['path'], row['app'])

    frames_df = db.get_frames()
    images_frames_df = images_df.merge(frames_df, on=['path', 'timestamp'])
    no_frames_df = images_frames_df.loc[images_frames_df['id'].isnull()]
    assert len(no_frames_df) == 0

    ocr_results_df = db.get_ocr_results()
    images_without_ocr_df = images_frames_df.loc[~(images_frames_df['id'].isin(set(ocr_results_df['frame_id'])))]
    print("Images without OCR:", len(images_without_ocr_df))
    path_to_run_ocr = list()
    for i, row in images_without_ocr_df.iterrows():
        path_to_run_ocr.append(row['id'])

    with multiprocessing.Pool(os.cpu_count() - 2) as p:
        p.map(run_ocr, path_to_run_ocr)
