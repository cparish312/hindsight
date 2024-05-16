import os
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify

app = Flask(__name__)

RAW_SCREENSHOTS_DIR = '/Users/connorparish/projects/hindsight/pixel8_screenshots'
SSL_CERT="/Users/connorparish/.ssl/hindsight_server/server.crt"
SSL_KEY="/Users/connorparish/.ssl/hindsight_server/server.key"

@app.route('/data', methods=['POST'])
def receive_data():
    data = request.json
    print("Received data:", data)
    return jsonify({"status": "success", "message": "Data received"}), 200

@app.route('/upload_image', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(RAW_SCREENSHOTS_DIR, filename))
        return jsonify({"status": "success", "message": "File successfully uploaded"}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=6000, ssl_context=(SSL_CERT, SSL_KEY))
