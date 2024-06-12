import os
import platform
import shutil
import queue
import threading
from threading import Lock
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify
import pandas as pd

from db import HindsightDB
from config import RAW_SCREENSHOTS_DIR

if platform.system() == 'Darwin': # OCR only available for MAC currently
    import run_ocr

app = Flask(__name__)

HOME = Path.home()
SCREENSHOTS_TMP_DIR = HOME / ".hindsight_server/raw_screenshots_tmp"
SSL_CERT = HOME / ".hindsight_server/server.crt"
SSL_KEY = HOME / ".hindsight_server/server.key"

def make_dir(d):
    if not os.path.exists(d):
        os.makedirs(d)

image_processing_queue = queue.Queue()
make_dir(SCREENSHOTS_TMP_DIR)

db = HindsightDB()

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
            make_dir(destdir)
            filepath = os.path.abspath(os.path.join(destdir, filename))
            shutil.move(tmp_file, filepath)
            print(f"File saved to {filepath}")

            # Insert into db and run OCR
            frame_id = db.insert_frame(timestamp, filepath, application)
            if platform.system() == 'Darwin':
                run_ocr.run_ocr(frame_id=frame_id) # run_ocr inserts results into db
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Error processing file: {e}")
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
    
@app.route('/ping', methods=['GET'])
def ping_server():
    return jsonify({'status': 'success', 'message': 'Server is reachable'}), 200

if __name__ == '__main__':
    num_threads = os.cpu_count() - 2 
    threads = []
    try:
        for i in range(num_threads):
            thread = threading.Thread(target=process_image_queue)
            thread.start()
            threads.append(thread)
        app.run(debug=True, host='0.0.0.0', port=6000, ssl_context=(SSL_CERT, SSL_KEY))
    finally:
        for _ in range(num_threads):  # Signal all threads to stop
            image_processing_queue.put(None)
        for thread in threads:
            thread.join()
