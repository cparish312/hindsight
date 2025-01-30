"""Script for running the Hindsight Server."""
import os
import logging
from pathlib import Path
from random import randrange
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, abort, Blueprint
from gevent.pywsgi import WSGIServer
from gevent import monkey
monkey.patch_all()

from config import SERVER_LOG_FILE, SECRET_API_KEY, HINDSIGHT_SERVER_DIR, SCREENSHOTS_TMP_DIR, VIDEO_FILES_DIR
import utils
from db import HindsightDB

from hindsight_applications.hindsight_feed.hindsight_feed_db import from_app_update_content, fetch_contents, fetch_newly_viewed_content

main_app = Blueprint('main', __name__)

HOME = Path.home()
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
    """Saves images to SCREENSHOTS_TMP_DIR"""
    if not verify_api_key():
        abort(401)
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400
    if file:
        filename = secure_filename(file.filename)
        tmp_file_path = os.path.join(SCREENSHOTS_TMP_DIR, filename)
        try:
            with open(tmp_file_path, 'wb') as tmp_file:
                file.save(tmp_file)
            print("Saved", filename)
            return jsonify({"status": "success", "message": "File successfully uploaded"}), 200
        except Exception as e:
            print(f"Error saving file: {e}")
            return jsonify({"status": "error", "message": "Failed to save file"}), 500
    return jsonify({"status": "error", "message": "No file"}), 400

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
    
    print(f"Successfully sent last timestamp {last_timestamp} for {table}.")
    return jsonify({"last_timestamp": last_timestamp})

@main_app.route('/get_last_id', methods=['GET'])
def get_last_id():
    """Get's the last frame_id for a given source (device)"""
    if not verify_api_key():
        abort(401)

    source = request.args.get("source")
    table = request.args.get("table", "frames")

    try:
        last_id = db.get_last_id(source=source, table=table)
    except:
        return jsonify({"status": "error", "message": f"Couldn't retrieve last id for table {table} source {source}"}), 400
    
    print(f"Successfully sent last id for table {table} source {source}")
    return jsonify({"last_id": last_id})

@main_app.route('/sync_db', methods=['POST'])
def sync_db():
    """Endpoint for syncing annotations, locations, content updates, and frames from a device to the Hindsight server."""
    if not verify_api_key():
        abort(401)
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400
    
    annotations = data.get('annotations', [])
    locations = data.get('locations', [])
    content_updates = data.get('content', [])

    source = data.get("source", "not_provided")
    frames = data.get("frames", [])

    try:
        ingested_annotations_timestamps = set(db.get_annotations()['timestamp'])
        annotations = [a for a in annotations if a['timestamp'] not in ingested_annotations_timestamps]
        # Insert annotations
        db.insert_annotations(annotations)
        
        ingested_locations_timestamps = set(db.get_locations()['timestamp'])
        locations = [l for l in locations if l['timestamp'] not in ingested_locations_timestamps]
        # Insert locations
        db.insert_locations(locations)

        # Sync content updates (viewed, rankings, etc...)
        from_app_update_content(content_sync_list=content_updates)

        # Ingest frames and OCR results from a device
        if frames is not None:
            for frame in frames:
                if frame is None:
                    continue
                frame_id = db.insert_frame(timestamp=frame['timestamp'], path="None", application=frame['application'],
                                        source=source, source_id=frame['id'])

                converted_ocr_results = list()
                for ocr_result in frame['ocr_results']:
                    converted_ocr_results.append((ocr_result['x'], ocr_result['y'], ocr_result['width'],
                                                ocr_result['height'], ocr_result['text'], ocr_result['confidence'], ocr_result['blockNum'], -1))
                db.insert_ocr_results(frame_id=frame_id, ocr_results=converted_ocr_results)
    except:
        return jsonify({'status': 'error', 'message': 'Failed Database sync'}), 400

    return jsonify({'status': 'success', 'message': 'Database successfully synced'})

@main_app.route('/upload_video', methods=['POST'])
def upload_video():
    """Upload a video and update frames video_chunk_id and video_chunk_offset"""
    if not verify_api_key():
        abort(401)

    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400
    
    source = request.form.get("source", None)
    source_id = int(request.form.get("video_chunk_id", None))
    if source is None or source_id is None:
        return jsonify({"status": "error", "message": "Must provide source and source_id"}), 400
    
    frame_ids = request.form.get("frame_ids", "")

    # Convert frame_ids to list of integers
    frame_ids_list = list(map(int, frame_ids.split(","))) if frame_ids else []

    # Convert the source_ids to the correct ids in the hindsight db
    hindsight_frame_ids = db.convert_source_ids_to_hindsight_ids(table="frames", source=source, source_ids=frame_ids_list)

    if file:
        filename = secure_filename(file.filename)
        video_file_path = os.path.join(VIDEO_FILES_DIR, filename)
        try:
            with open(video_file_path, 'wb') as outfile:
                file.save(outfile)
            print("Saved", filename)
        except Exception as e:
            print(f"Error saving file: {e}")
            return jsonify({"status": "error", "message": "Failed to save video"}), 500
        
        video_chunk_id = db.insert_video_chunk(path=video_file_path, source=source, source_id=source_id)
        db.update_video_chunk_info(video_chunk_id=video_chunk_id, frame_ids=hindsight_frame_ids)
    
        return jsonify({"status": "success", "message": "Video file successfully uploaded"}), 200
    
    return jsonify({"status": "error", "message": "No file"}), 400
    
@main_app.route('/get_new_content', methods=['GET'])
def get_new_content():
    """Fetch all new unviewed content and content updates since provided last_sync_timestamp"""
    if not verify_api_key():
        abort(401)

    last_content_id = int(request.args.get('last_content_id'))
    last_sync_timestamp = int(request.args.get('last_sync_timestamp')) 

    print(f"Last content id {last_content_id}")
    new_content = fetch_contents(non_viewed=True, last_content_id=last_content_id)
    new_content_list = list()
    for c in new_content:
        c_dict = c.__dict__
        if "_sa_instance_state" in c_dict:
            del c_dict['_sa_instance_state']
        new_content_list.append(c_dict)

    newly_viewed_content = fetch_newly_viewed_content(since_timestamp=last_sync_timestamp)
    newly_viewed_content_ids = list(c.id for c in newly_viewed_content)

    non_viewed_content = fetch_contents(non_viewed=True)
    non_viewed_content_updates = list()
    for c in non_viewed_content:
        non_viewed_content_updates.append({"content_id" : c.id, "ranking_score" : c.ranking_score,
                                           "topic_label" : c.topic_label})
    print(f"Successully sent new content {len(new_content_list)} and newly viewed content {len(newly_viewed_content)}")
    return jsonify({"new_content" : new_content_list, "newly_viewed_content_ids" : newly_viewed_content_ids,
                    "non_viewed_content_updates" : non_viewed_content_updates})
    
@main_app.route('/ping', methods=['GET'])
def ping_server():
    if not verify_api_key():
        abort(401)
    return jsonify({'status': 'success', 'message': 'Server is reachable'}), 200

app = create_app()
if __name__ == '__main__':
    http_server = WSGIServer(('0.0.0.0', 6000), app, keyfile=SSL_KEY, certfile=SSL_CERT)
    http_server.serve_forever()
    