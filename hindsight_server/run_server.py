import os
import atexit
import time
import logging
import platform
import shutil
import queue
import threading
from threading import Lock
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, abort
import pandas as pd

from run_chromadb_ingest import get_chroma_collection, run_chroma_ingest
from db import HindsightDB
from config import RAW_SCREENSHOTS_DIR, SERVER_LOG_FILE, SECRET_API_KEY, HINDSIGHT_SERVER_DIR
import query
import utils

if platform.system() == 'Darwin': # OCR only available for MAC currently
    import run_ocr

app = Flask(__name__)

# Set up logging to a file
handler = logging.FileHandler(SERVER_LOG_FILE)
handler.setLevel(logging.DEBUG)
formatter = logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')
handler.setFormatter(formatter)
app.logger.addHandler(handler)

threads = list()

HOME = Path.home()
SCREENSHOTS_TMP_DIR = HINDSIGHT_SERVER_DIR/ "raw_screenshots_tmp"
SSL_CERT = HINDSIGHT_SERVER_DIR / "server.crt"
SSL_KEY = HINDSIGHT_SERVER_DIR / "server.key"

image_processing_queue = queue.Queue()
utils.make_dir(SCREENSHOTS_TMP_DIR)

db = HindsightDB()
frames_to_process = list()
frames_to_process_lock = Lock()

# def process_images_batched():
#     """Made since chromadb insert is much more efficient in batches"""
#     while True:
#         with frames_to_process_lock:
#             if len(frames_to_process) == 0:
#                 continue
#             processing_frames = frames_to_process.copy()
#             frames_to_process.clear()

#         print(f"Running process_images_batched on {len(processing_frames)} frames")
#         chroma_collection = get_chroma_collection()
#         frames_df = db.get_frames(frame_ids=processing_frames)
#         ocr_results_df = db.get_frames_with_ocr(frame_ids=processing_frames)
#         run_chroma_ingest(df=frames_df, ocr_results_df=ocr_results_df, chroma_collection=chroma_collection)
#         app.logger.info(f"Ran process_images_batched on {len(processing_frames)} frames")
#         time.sleep(120)

def process_image_queue():
    while True:
        try:
            item = image_processing_queue.get(timeout=20)
            if item is None:
                break  # Allows the thread to be stopped
            filename, tmp_file = item
            filename_s = filename.replace(".jpg", "").split("_")
            application = filename_s[0]
            timestamp = int(filename_s[1])
            timestamp_obj = pd.to_datetime(timestamp / 1000, unit='s', utc=True)
            destdir = os.path.join(RAW_SCREENSHOTS_DIR, f"{timestamp_obj.strftime('%Y/%m/%d')}/{application}/")
            utils.make_dir(destdir)
            filepath = os.path.abspath(os.path.join(destdir, filename))
            shutil.move(tmp_file, filepath)
            print(f"File saved to {filepath}")

            # Insert into db and run OCR
            frame_id = db.insert_frame(timestamp, filepath, application)
            if platform.system() == 'Darwin':
                run_ocr.run_ocr(frame_id=frame_id, path=filepath) # run_ocr inserts results into db
                # with frames_to_process_lock:
                #     frames_to_process.append(frame_id)

        except queue.Empty:
            continue
        except Exception as e:
            print(f"Error processing file: {e}")
            app.logger.error(f"Error processing file: {e}")
        else:
            image_processing_queue.task_done()

@app.route('/upload_image', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400
    if file:
        filename = secure_filename(file.filename)
        tmp_file = os.path.join(SCREENSHOTS_TMP_DIR, filename)
        file.save(tmp_file)
        image_processing_queue.put((filename, tmp_file))
        return jsonify({"status": "success", "message": "File successfully uploaded"}), 200
    
@app.route('/post_query', methods=['POST'])
def post_query():
    if not request.is_json:
        return jsonify({"status": "error", "message": "Missing JSON in request"}),

    data = request.get_json()
    if 'query' not in data:
        return jsonify({"status": "error", "message": "Missing data in JSON"}), 400
    
    query_id = db.insert_query(query=data['query'])
    start_time = data['start_time'] if "start_time" in data else None
    end_time = data['end_time'] if "end_time" in data else None
    
    query_thread = threading.Thread(target=query.query, 
                                    args=(query_id, data['query'], None, start_time, end_time))

    query_thread.start()
    return jsonify({"status": "success", "message": "Data received"}), 200

def verify_api_key():
    api_key = request.headers.get('Hightsight-API-Key')
    return api_key == SECRET_API_KEY

@app.route('/get_queries', methods=['GET'])
def get_queries():
    if not verify_api_key():
        abort(401)
    active_queries = db.get_active_queries().sort_values(by='timestamp', ascending=False)
    queries = list()
    for i, row in active_queries.iterrows():
        queries.append({"query": row['query'], "result": row['result']})
    print("Successully sent queries.")
    return jsonify(queries[:6])
    
    
@app.route('/ping', methods=['GET'])
def ping_server():
    return jsonify({'status': 'success', 'message': 'Server is reachable'}), 200

def process_tmp_dir():
    """If the server fails to process images some may remain in the SCREENSHOTS_TMP_DIR.
    Add them to the image_processing_queue."""
    for f in os.listdir(SCREENSHOTS_TMP_DIR):
        file_path = os.path.join(SCREENSHOTS_TMP_DIR, f)
        image_processing_queue.put((f, file_path))

def setup_threads():
    global threads
    num_threads = os.cpu_count() - 2 
    for i in range(num_threads):
        thread = threading.Thread(target=process_image_queue)
        thread.start()
        threads.append(thread)
    # process_images_batched_thread = threading.Thread(target=process_images_batched)
    # process_images_batched_thread.start()
    # threads.append(process_images_batched_thread)

def initialize():
    process_tmp_dir() # Since runs for each gunicorn worker will throw errors since files will be moved but can be ignored
    setup_threads()

with app.app_context():
    initialize()

def cleanup():
    print("Cleaning up threads")
    global threads
    for _ in range(len(threads) - 1):  # Signal all threads to stop
        image_processing_queue.put(None)
    for thread in threads:
        thread.join()

atexit.register(cleanup)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=6000, ssl_context=(SSL_CERT, SSL_KEY))
