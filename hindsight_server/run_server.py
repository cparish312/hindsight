"""Script for running the Hindsight Server."""
import os
import logging
from pathlib import Path
from random import randrange
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, abort, Blueprint

from config import SERVER_LOG_FILE, SECRET_API_KEY, HINDSIGHT_SERVER_DIR
import utils
from db import HindsightDB

main_app = Blueprint('main', __name__)

HOME = Path.home()
SCREENSHOTS_TMP_DIR = HINDSIGHT_SERVER_DIR / "raw_screenshots_tmp"
SSL_CERT = HINDSIGHT_SERVER_DIR / "server.crt"
SSL_KEY = HINDSIGHT_SERVER_DIR / "server.key"

utils.make_dir(SCREENSHOTS_TMP_DIR)

db = HindsightDB()

def create_app(*args, **kwargs):
    app = Flask(__name__)
    app.register_blueprint(main_app)

    handler = logging.FileHandler(SERVER_LOG_FILE)
    handler.setLevel(logging.DEBUG)
    formatter = logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    return app

def verify_api_key():
    api_key = request.headers.get('Hightsight-API-Key')
    return api_key == SECRET_API_KEY

@main_app.route('/upload_image', methods=['POST'])
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
        print("Saved", filename)
        return jsonify({"status": "success", "message": "File successfully uploaded"}), 200

@main_app.route('/post_query', methods=['POST'])
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
    db.insert_query(query=data['query'], context_start_timestamp=context_start_timestamp, context_end_timestamp=context_end_timestamp)
    return jsonify({"status": "success", "message": "Data received"}), 200

@main_app.route('/get_queries', methods=['GET'])
def get_queries():
    if not verify_api_key():
        abort(401)
    active_queries = db.get_active_queries().sort_values(by='timestamp', ascending=False)
    queries = list()
    for i, row in active_queries.iterrows():
        queries.append({"query": row['query'], "result": row['result']})
    print("Successully sent queries.")
    return jsonify(queries[:6])

@main_app.route('/get_last_timestamp', methods=['GET'])
def get_last_timestamp():
    if not verify_api_key():
        abort(401)

    table = request.args.get('table')
    if not table:
        return jsonify({"status": "error", "message": "Missing table parameter"}), 400
    
    try:
        last_timestamp = db.get_last_timestamp(table)
    except:
        return jsonify({"status": "error", "message": f"Couldn't retrieve last timestamp for table {table}"}), 400
    
    print(f"Successfully sent last timestamp for {table}.")
    return jsonify({"last_timestamp": last_timestamp})

@main_app.route('/sync_db', methods=['POST'])
def sync_db():
    if not verify_api_key():
        abort(401)
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400
    
    annotations = data.get('annotations', [])
    locations = data.get('locations', [])
    
    try:
        ingested_annotations_timestamps = set(db.get_annotations()['timestamp'])
        annotations = [a for a in annotations if a['timestamp'] not in ingested_annotations_timestamps]
        # Insert annotations
        db.insert_annotations(annotations)
        
        ingested_locations_timestamps = set(db.get_locations()['timestamp'])
        locations = [l for l in locations if l['timestamp'] not in ingested_locations_timestamps]
        # Insert locations
        db.insert_locations(locations)
    except:
        return jsonify({'status': 'error', 'message': 'Failed annotations or locations ingestion'}), 400

    return jsonify({'status': 'success', 'message': 'Database successfully synced'})
    
@main_app.route('/ping', methods=['GET'])
def ping_server():
    if not verify_api_key():
        abort(401)
    return jsonify({'status': 'success', 'message': 'Server is reachable'}), 200

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=6000, ssl_context=(SSL_CERT, SSL_KEY))
