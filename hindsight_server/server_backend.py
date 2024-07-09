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
    ocr_results_df = db.get_frames_with_ocr(frame_ids=frame_ids)
    run_chroma_ingest_batched(db=db, df=frames_df, ocr_results_df=ocr_results_df, chroma_collection=chroma_collection)

def check_all_frames_ingested():
    """Ensures that all screenshots in the RAW_SCREENSHOTS_DIR are s
    ingested in the frames table
    """
    pass


if __name__ == "__main__":
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
