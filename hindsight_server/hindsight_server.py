import os
import shutil
import queue
import threading
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify
import pandas as pd

app = Flask(__name__)

base_dir = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(base_dir, "data")
RAW_SCREENSHOTS_DIR = os.path.join(DATA_DIR, "raw_screenshots")

HOME = Path.home()
SCREENSHOTS_TMP_DIR = HOME / ".hindsight_server/raw_screenshots_tmp"
SSL_CERT = HOME / ".hindsight_server/server.crt"
SSL_KEY = HOME / ".hindsight_server/server.key"

def make_dir(d):
    if not os.path.exists(d):
        os.makedirs(d)

image_processing_queue = queue.Queue()
make_dir(SCREENSHOTS_TMP_DIR)

def process_image_queue():
    while True:
        try:
            item = image_processing_queue.get()
            if item is None:
                break  # Allows the thread to be stopped
            filename, tmp_file = item
            filename_s = filename.replace(".jpg", "").split("_")
            application = filename_s[0]
            timestamp = int(filename_s[1])
            timestamp_obj = pd.to_datetime(timestamp / 1000, unit='s', utc=True)
            destdir = os.path.join(RAW_SCREENSHOTS_DIR, f"{timestamp_obj.strftime('%Y/%m/%d')}/{application}/")
            make_dir(destdir)
            filepath = os.path.join(destdir, filename)
            shutil.move(tmp_file, filepath)
            print(f"File saved to {filepath}")
            image_processing_queue.task_done()
        except Exception as e:
            print(f"Error processing file: {e}")
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

if __name__ == '__main__':
    try:
        image_processor_thread = threading.Thread(target=process_image_queue)
        image_processor_thread.start()
        app.run(debug=True, host='0.0.0.0', port=6000, ssl_context=(SSL_CERT, SSL_KEY))
    finally:
        image_processing_queue.put(None)
        image_processor_thread.join()
