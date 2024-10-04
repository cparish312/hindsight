import os
import time
import pandas as pd
import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory, Response
from hindsight_feed_db import update_content_score, content_clicked, content_viewed, Session
from feed_generator import FeedGenerator
from feeders.exa_topic.exa_topic import ExaTopicFeeder
from feeders.browser_history_summary.browser_history_summary import YesterdayBrowserSummaryFeeder, TopicBrowserSummaryFeeder

from feed_utils import url_to_path
from feed_config import GENERATOR_DATA_DIR

app = Flask(__name__)

app.config['SERVER_NAME'] = 'localhost:5000'
app.config['LOCAL_DOCS_PATH'] = GENERATOR_DATA_DIR

# content_generators = [ExaTopicFeeder(name="exa_topic_local_ai", description="ExaTopicFeeder for getting information on local ai", 
#                                      topic="local Artificial Intelligence", min_num_contents=10),
#                     ExaTopicFeeder(name="exa_topic_personal_ai", description="ExaTopicFeeder for getting information on personal ai", 
#                     topic="personal Artificial Intelligence", min_num_contents=10),
#                     ExaTopicFeeder(name="exa_topic_personal_feed", description="ExaTopicFeeder for getting information on personal feed", 
#                     topic="personal feed where you can control your own algorithmn", min_num_contents=10),
#                     ExaTopicFeeder(name="exa_topic_personal_exa_feed", description="ExaTopicFeeder for getting information on personal exa feed", 
#                     topic="personal feed using exa.ai", min_num_contents=10)]
content_generators = None
feed_generator = FeedGenerator(content_generators=content_generators)
print("Number of Content Generators", len(feed_generator.content_generators))

@app.teardown_request
def on_teardown(err):
    Session.remove()

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
    print('streaming file', filename)
    file_path = os.path.join(GENERATOR_DATA_DIR, url_to_path(filename)).replace(".html", "_content.html")
    return Response(file_stream(file_path), mimetype='text/event-stream')

def get_feed_content():
    content = feed_generator.get_contents()
    for c in content:
        if c.published_date:
            c.published_date = pd.to_datetime(c.published_date / 1000, unit='s', utc=True).strftime('%Y-%m-%d')
    return content

@app.route('/')
def home():
    contents = get_feed_content()
    return render_template('index.html', contents=contents)

def event_stream():
    displayed_content_ids = {c.id for c in get_feed_content()}
    with app.app_context():
        while True:
            current_contents = get_feed_content()
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
    app.run(debug=True)

                         