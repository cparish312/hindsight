"""Script for running the Hindsight Server."""
import os
import logging
from pathlib import Path
from random import randrange
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, abort, Blueprint
from celery import Celery

from config import SERVER_LOG_FILE, SECRET_API_KEY, HINDSIGHT_SERVER_DIR
import utils
import query
from db import HindsightDB

threads = list()

HOME = Path.home()
SCREENSHOTS_TMP_DIR = HINDSIGHT_SERVER_DIR/ "raw_screenshots_tmp"
SSL_CERT = HINDSIGHT_SERVER_DIR / "server.crt"
SSL_KEY = HINDSIGHT_SERVER_DIR / "server.key"

utils.make_dir(SCREENSHOTS_TMP_DIR)

db = HindsightDB()

app = Flask(__name__)

handler = logging.FileHandler(SERVER_LOG_FILE)
handler.setLevel(logging.DEBUG)
formatter = logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')
handler.setFormatter(formatter)
app.logger.addHandler(handler)
app.config.update(
    CELERY_BROKER_URL='redis://localhost:6379/0',
    CELERY_RESULT_BACKEND='redis://localhost:6379/0'
)

def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL']
    )
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

celery = make_celery(app)
from server_tasks import run_query

def verify_api_key():
    api_key = request.headers.get('Hightsight-API-Key')
    return api_key == SECRET_API_KEY

@app.route('/upload_image', methods=['POST'])
def upload_image():
    if not verify_api_key():
        abort(401)
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400
    if file:
        filename = secure_filename(file.filename)
        tmp_file = os.path.join(SCREENSHOTS_TMP_DIR, filename)
        file.save(tmp_file)
        return jsonify({"status": "success", "message": "File successfully uploaded"}), 200

@app.route('/post_query', methods=['POST'])
def post_query():
    if not verify_api_key():
        abort(401)
    if not request.is_json:
        return jsonify({"status": "error", "message": "Missing JSON in request"}),

    data = request.get_json()
    if 'query' not in data:
        return jsonify({"status": "error", "message": "Missing data in JSON"}), 400
    
    context_start_timestamp = data['context_start_timestamp'] if "context_start_timestamp" in data else None
    context_end_timestamp = data['context_end_timestamp'] if "context_end_timestamp" in data else None
    query_id = db.insert_query(query=data['query'], context_start_timestamp=context_start_timestamp, context_end_timestamp=context_end_timestamp)
    run_query(query_id=query_id, query_text=data['query'], context_start_timestamp=context_start_timestamp, context_end_timestamp=context_end_timestamp)
    return jsonify({"status": "success", "message": "Data received"}), 200

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
    if not verify_api_key():
        abort(401)
    return jsonify({'status': 'success', 'message': 'Server is reachable'}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=6000, ssl_context=(SSL_CERT, SSL_KEY))
