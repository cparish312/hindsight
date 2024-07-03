"""This contains the heavy processes of the hindsight server."""
import time

from db import HindsightDB
import query
from run_server import celery

db = HindsightDB()

@celery.task(time_limit=100000, soft_time_limit=90000)
def run_query(query_id, query_text, context_start_timestamp=None, context_end_timestamp=None):
    """Runs query."""
    running_query = True
    while running_query:
        if db.acquire_lock("chromadb"):
            try:
                query.query_and_insert(query_id=query_id, query_text=query_text, source_apps=None, 
                                       utc_milliseconds_start_date=context_start_timestamp, utc_milliseconds_end_date=context_end_timestamp)
            finally:
                db.release_lock("chromadb")
                running_query = False
        else:
            time.sleep(20)


# def chromadb_process_images():
#     """Ingests frames into chromadb with OCR results that haven't been ingested already."""
#     global last_image_upload
#     time.sleep(randrange(120)) # Make offsync when multiple
#     while True:
#         if datetime.now() - last_image_upload < timedelta(minutes=2):
#             time.sleep(120)
#             continue
#         if db.acquire_lock("chromadb"): # Lock to ensure only one ingest occurs at a time
#             try:
#                 frames_df = db.get_non_chromadb_processed_frames_with_ocr().sort_values(by='timestamp', ascending=True)
#                 frame_ids = set(frames_df['id'])
#                 if len(frame_ids) == 0:
#                     db.release_lock("chromadb")
#                     time.sleep(120)
#                     continue
#                 print(f"Running process_images_batched on {len(frame_ids)} frames")
#                 mlx.core.metal.clear_cache()
#                 chroma_collection = get_chroma_collection()
#                 ocr_results_df = db.get_frames_with_ocr(frame_ids=frame_ids)
#                 run_chroma_ingest_batched(db=db, df=frames_df, ocr_results_df=ocr_results_df, chroma_collection=chroma_collection)
#                 app.logger.info(f"Ran process_images_batched on {len(frame_ids)} frames")
#                 db.release_lock("chromadb")
#                 gc.collect()
#                 mlx.core.metal.clear_cache()
#                 time.sleep(120)
#             finally:
#                 db.release_lock("chromadb")
#         else:
#             time.sleep(120)

# def process_image_queue():
#     """Copies frame into correct directory in screenshot_dir. Inserts frame into frames table.
#     Runs OCR on frame and inserts results in ocr_results table.
#     """
#     global last_image_upload
#     while True:
#         if not db.check_lock("chromadb"): # Ensure OCR doesn't happen at the same time as chromadb
#             time.sleep(30)
#             continue
#         try:
#             item = image_processing_queue.get(timeout=20)
#             if item is None:
#                 break  # Allows the thread to be stopped
#             filename, tmp_file = item
#             filename_s = filename.replace(".jpg", "").split("_")
#             application = filename_s[0]
#             timestamp = int(filename_s[1])
#             timestamp_obj = pd.to_datetime(timestamp / 1000, unit='s', utc=True)
#             destdir = os.path.join(RAW_SCREENSHOTS_DIR, f"{timestamp_obj.strftime('%Y/%m/%d')}/{application}/")
#             utils.make_dir(destdir)
#             filepath = os.path.abspath(os.path.join(destdir, filename))
#             shutil.move(tmp_file, filepath)
#             print(f"File saved to {filepath}")

#             # Insert into db and run OCR
#             frame_id = db.insert_frame(timestamp, filepath, application)
#             if platform.system() == 'Darwin':
#                 run_ocr.run_ocr(frame_id=frame_id, path=filepath) # run_ocr inserts results into db

#         except queue.Empty:
#             continue
#         except Exception as e:
#             print(f"Error processing file: {e}")
#             app.logger.error(f"Error processing file: {e}")
#         else:
#             last_image_upload = datetime.now()
#             image_processing_queue.task_done()

# def process_tmp_dir():
#     """If the server fails to process images some may remain in the SCREENSHOTS_TMP_DIR.
#     Add them to the image_processing_queue."""
#     for f in os.listdir(SCREENSHOTS_TMP_DIR):
#         file_path = os.path.join(SCREENSHOTS_TMP_DIR, f)
#         image_processing_queue.put((f, file_path))


# def setup_threads():
#     global threads
#     num_image_process_threads = 2
#     for i in range(num_image_process_threads):
#         thread = threading.Thread(target=process_image_queue)
#         thread.start()
#         threads.append(thread)
#     process_images_batched_thread = threading.Thread(target=chromadb_process_images)
#     process_images_batched_thread.start()
#     threads.append(process_images_batched_thread)
#     process_query_thread = threading.Thread(target=process_query_queue)
#     process_query_thread.start()
#     threads.append(process_query_thread)

# def initialize():
#     setup_threads()

# def cleanup():
#     print("Cleaning up threads")
#     global threads
#     for _ in range(len(threads) - 1):  # Signal all threads to stop
#         image_processing_queue.put(None)
#     for thread in threads:
#         thread.join()

# atexit.register(cleanup)

# query_queue.put((query_id, data['query'], start_time, end_time))

# executor.submit(query.query_and_insert, query_id, data['query'], None, start_time, end_time)

# query_thread = threading.Thread(target=query.query_and_insert, 
#                                     args=(query_id, data['query'], None, start_time, end_time))

# query_thread.start()