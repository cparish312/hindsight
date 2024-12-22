"""This contains the heavy processes of the hindsight server."""
import os
import glob
import shutil
import time
import multiprocessing
import pandas as pd
from datetime import datetime, timedelta

from db import HindsightDB
from chromadb_tools import get_chroma_collection, run_chroma_ingest_batched
from config import RAW_SCREENSHOTS_DIR, SCREENSHOTS_TMP_DIR, RUNNING_PLATFORM
import hindsight_server.query.query as query
import utils
import run_ocr

from hindsight_applications.hindsight_feed.feed_generator import FeedGenerator
from hindsight_applications.hindsight_feed.rankers.sentence_transformers_linear_reg import SentenceTransformersLinearRegRanker

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
    filename = os.path.basename(tmp_image_path)
    filename_s = filename.replace(".jpg", "").split("_")
    application = filename_s[0]
    timestamp = int(filename_s[1])
    timestamp_obj = pd.to_datetime(timestamp / 1000, unit='s', utc=True)
    destdir = os.path.join(RAW_SCREENSHOTS_DIR, f"{timestamp_obj.strftime('%Y/%m/%d')}/{application}/")
    utils.make_dir(destdir)
    filepath = os.path.abspath(os.path.join(destdir, filename))
    if not os.path.exists(filepath):
        shutil.move(tmp_image_path, filepath)
        print(f"File saved to {filepath}")
    elif os.path.exists(tmp_image_path):
        os.remove(tmp_image_path)

    # Insert into db
    frame_id = db.insert_frame(timestamp, filepath, application)
    if RUNNING_PLATFORM == 'Darwin':
        run_ocr.run_ocr_mac(frame_id=frame_id, frame_path=filepath) # run_ocr inserts results into db

def run_grouped_ocr():
    """Run OCR on all frames without OCR results"""
    frames_without_ocr = db.get_frames_without_ocr()
    if len(frames_without_ocr) == 0:
        return
    
    print(f"Running OCR on {len(frames_without_ocr)} frames")
    if RUNNING_PLATFORM == 'Darwin':
        frame_id_path = [(frame_id, filepath) for frame_id, filepath in zip(frames_without_ocr['id'], frames_without_ocr['path'])]
        with multiprocessing.Pool(os.cpu_count() - 2) as p:
            p.starmap(run_ocr.run_ocr_mac, frame_id_path)
        return
    
    run_ocr.run_ocr_batched(df=frames_without_ocr, batch_size=20)

def chromadb_process_images(frames_df):
    """Ingests frames into chromadb."""
    frame_ids = set(frames_df['id'])
    print(f"Running ChromaDB ingest on {len(frame_ids)} frames")
    chroma_collection = get_chroma_collection()
    run_chroma_ingest_batched(db=db, df=frames_df, chroma_collection=chroma_collection)

def check_all_frames_ingested():
    """Ensures that all screenshots in the RAW_SCREENSHOTS_DIR are
    ingested in the frames table.
    """
    frames = db.get_frames()
    screenshot_paths = {os.path.abspath(f) for f in glob.glob(os.path.join(RAW_SCREENSHOTS_DIR, '*', '*', '*', '*', '*.jpg'))}
    missing_screenshots = screenshot_paths - set(frames['path'])
    if len(missing_screenshots) > 0:
        print(f"Ingesting {len(missing_screenshots)} screenshots missing from frames table.")

        sorted_screenshots = sorted(
            ((int(os.path.basename(path).split('_')[1].split(".")[0]), path) for path in missing_screenshots),
            key=lambda x: x[0]
        )

        for timestamp, ms_path in sorted_screenshots:
            application = os.path.basename(ms_path).split('_')[0]
            # Insert into db and run OCR
            db.insert_frame(timestamp, ms_path, application)

    uncompressed_screenshots = frames.loc[frames['video_chunk_id'].isnull()]
    screenshots_missing_paths = set(uncompressed_screenshots['path']) - screenshot_paths
    if len(screenshots_missing_paths) > 0:
        print(f"Screenshots missing path: {screenshots_missing_paths}")

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

def run_applications():
    """Heartbeat for applications."""
    feed_generator = FeedGenerator()
    feed_generator.generate_content()

    ranker = SentenceTransformersLinearRegRanker()
    if os.path.exists(ranker.model_save_path):
        ranker_last_modified_time = os.path.getmtime(ranker.model_save_path)
        ranker_last_modified_date = datetime.fromtimestamp(ranker_last_modified_time)
        # If it has been over 24 hours since rankings have been updated generate
        if (datetime.now() - ranker_last_modified_date) > timedelta(hours=24):
            ranker.generate_rankings()
    else:
        ranker.generate_rankings()

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

        run_grouped_ocr() # Run OCR on any frames missing ocr results

        non_chromadb_processed_frames_df = db.get_non_chromadb_processed_frames_with_ocr().sort_values(by='timestamp', ascending=True)
        if len(non_chromadb_processed_frames_df) > 0:
            chromadb_process_images(non_chromadb_processed_frames_df)

        run_applications()
            
        time.sleep(10)
