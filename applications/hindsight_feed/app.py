import os
import time
from flask import Flask, render_template, request, jsonify, send_from_directory, Response
from db import update_content_score, content_clicked, content_viewed
from feed_generator import FeedGenerator
from feeders.exa_topic.exa_topic import ExaTopicFeeder
from feeders.browser_history_summary.browser_history_summary import YesterdayBrowserSummaryFeeder, TopicBrowserSummaryFeeder

from config import GENERATOR_DATA_DIR

app = Flask(__name__)

app.config['LOCAL_DOCS_PATH'] = GENERATOR_DATA_DIR

content_generators = list()
feed_generator = FeedGenerator(content_generators=content_generators)

@app.route('/local/docs/<path:filename>')
def serve_file(filename):
    return send_from_directory(app.config['LOCAL_DOCS_PATH'], filename)

def file_stream(file_path):
    """Stream the file from the given path if it has been updated."""
    print(f"Streaming from {file_path}")
    last_modified_time = None
    try:
        while True:
            if os.path.exists(file_path) and os.path.isfile(file_path):
                stat = os.stat(file_path)
                if last_modified_time is None or stat.st_mtime > last_modified_time: # Check file has changed
                    last_modified_time = stat.st_mtime
                    with open(file_path, 'r') as file:
                        html_content = file.read().replace('\n', '')
                        yield f"data: {html_content}\n\n"
            else:
                yield "data: \n\n" 
            time.sleep(4)  # Check for updates every 5 seconds
    except Exception as e:
        print(f"Error: {e}")
        yield "data: Error loading file.\n\n"

@app.route('/stream/docs/<path:filename>')
def stream_file(filename):
    file_path = os.path.join(GENERATOR_DATA_DIR, filename).replace(".html", "_content.html")
    return Response(file_stream(file_path), mimetype='text/event-stream')

@app.route('/')
def home():
    contents = feed_generator.get_contents()
    return render_template('index.html', contents=contents)

def event_stream():
    displayed_content_ids = {c.id for c in feed_generator.get_contents()}
    with app.app_context():
        while True:
            current_contents = feed_generator.get_contents()
            for c in current_contents[::-1]: # Iterate reverse to ensure multiple new contents are added in the correct order
                if c.id in displayed_content_ids:
                    continue
                content_html = render_template('content_template.html', content=c)
                content_html = content_html.replace('\n', '')
                yield f"data: {content_html}\n\n"
                displayed_content_ids.add(c.id)
            time.sleep(1)  # Sleep for demonstration purposes

@app.route('/stream')
def stream():
    return app.response_class(event_stream(), mimetype='text/event-stream')

@app.route('/update_score', methods=['POST'])
def update_score():
    content_id = request.form.get('content_id')
    score = request.form.get('score')
    if score:
        update_content_score(content_id, int(score))
    return jsonify(success=True)

@app.route('/handle_click', methods=['POST'])
def handle_click():
    content_id = request.form.get('content_id')
    clicked = request.form.get('clicked', False)
    if clicked:
        content_clicked(content_id)
        for content_id in request.form.getlist('ids_before[]'):
            content_viewed(content_id)
    return jsonify(success=True)

@app.route('/submit_query', methods=['POST'])
def submit_query():
    query = request.form['query'] 
    print(f"Received query: {query}") 
    feed_generator.add_content_generator(TopicBrowserSummaryFeeder(name=f"""TopicBrowserSummaryFeeder_{query.replace(" ", "_")}""", 
                                                description=f"Generates an html page with a summary for all browser history related to {query}",
                                                topic=query))
    return jsonify(success=True)
    
if __name__ == '__main__':
    app.run(debug=False)

                         