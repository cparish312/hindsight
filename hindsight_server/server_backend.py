"""This contains the heavy processes of the hindsight server."""
import os
import glob
import shutil
import time
import platform
import multiprocessing
import pandas as pd

from db import HindsightDB
from run_chromadb_ingest import get_chroma_collection, run_chroma_ingest_batched
from run_server import SCREENSHOTS_TMP_DIR
from config import RAW_SCREENSHOTS_DIR
import query
import utils
import run_ocr

db = HindsightDB()

def process_queries(unprocessed_queries: pd.DataFrame):
    """Processes all unprocessed queries."""
    for i, row in unprocessed_queries.iterrows():
        query.query_and_insert(query_id=row['id'], query_text=row['query'], source_apps=row['context_applications'], 
                                       utc_milliseconds_start_date=row['context_start_timestamp'], 
                                       utc_milliseconds_end_date=row['context_end_timestamp'])
        
def ingest_image(tmp_image_path):
    """Moves image into RAW_SCREENSHOTS_DIR, ingests into frames table, 
    runs OCR and ingests results.
    """
    filename = tmp_image_path.split('/')[-1]
    filename_s = filename.replace(".jpg", "").split("_")
    application = filename_s[0]
    timestamp = int(filename_s[1])
    timestamp_obj = pd.to_datetime(timestamp / 1000, unit='s', utc=True)
    destdir = os.path.join(RAW_SCREENSHOTS_DIR, f"{timestamp_obj.strftime('%Y/%m/%d')}/{application}/")
    utils.make_dir(destdir)
    filepath = os.path.abspath(os.path.join(destdir, filename))
    shutil.move(tmp_image_path, filepath)
    print(f"File saved to {filepath}")

    # Insert into db and run OCR
    frame_id = db.insert_frame(timestamp, filepath, application)
    if platform.system() == 'Darwin':
        run_ocr.run_ocr(frame_id=frame_id, path=filepath) # run_ocr inserts results into db

def chromadb_process_images(frames_df):
    """Ingests frames into chromadb."""
    frame_ids = set(frames_df['id'])
    print(f"Running process_images_batched on {len(frame_ids)} frames")
    chroma_collection = get_chroma_collection()
    run_chroma_ingest_batched(db=db, df=frames_df, chroma_collection=chroma_collection)

def check_all_frames_ingested():
    """Ensures that all screenshots in the RAW_SCREENSHOTS_DIR are
    ingested in the frames table.
    """
    frames = db.get_frames()
    screenshot_paths = glob.glob(f"{RAW_SCREENSHOTS_DIR}/*/*/*/*/*.jpg")
    missing_screenshots = set(screenshot_paths) - set(frames['path'])
    if len(missing_screenshots) > 0:
        print(f"Ingesting {len(missing_screenshots)} screenshots missing from frames table.")
        for ms_path in missing_screenshots:
            filename = ms_path.split('/')[-1]
            filename_s = filename.replace(".jpg", "").split("_")
            application = filename_s[0]
            timestamp = int(filename_s[1])
            # Insert into db and run OCR
            frame_id = db.insert_frame(timestamp, ms_path, application)
            if platform.system() == 'Darwin':
                run_ocr.run_ocr(frame_id=frame_id, path=ms_path) # run_ocr inserts results into db

def update_android_identifiers_file():
    """Adds any missing android identifiers to the android identifers json"""
    id_to_alias = utils.get_identifiers_to_alias()
    frames = db.get_frames()
    new_applications = set(frames['application_org']) - set(id_to_alias.keys())
    if len(new_applications) == 0:
        return
    for a in new_applications:
        id_to_alias[a] = None
    utils.save_identifiers_to_alias(id_to_alias)
    print(f"{len(new_applications)} new application identifiers added to alias file.")

if __name__ == "__main__":
    check_all_frames_ingested()
    update_android_identifiers_file()
    print("Finished Backend setup")

    while True:
        unprocessed_queries = db.get_unprocessed_queries()
        if len(unprocessed_queries) > 0:
            process_queries(unprocessed_queries)

        unprocessed_image_paths = [os.path.join(SCREENSHOTS_TMP_DIR, f) for f in os.listdir(SCREENSHOTS_TMP_DIR)]
        if len(unprocessed_image_paths) > 0:
            print(f"Ingesting {len(unprocessed_image_paths)} images.")
            with multiprocessing.Pool(os.cpu_count() - 2) as p:
                p.map(ingest_image, unprocessed_image_paths)

        non_chromadb_processed_frames_df = db.get_non_chromadb_processed_frames_with_ocr().sort_values(by='timestamp', ascending=True)
        if len(non_chromadb_processed_frames_df) > 0:
            chromadb_process_images(non_chromadb_processed_frames_df)
            
        time.sleep(10)
