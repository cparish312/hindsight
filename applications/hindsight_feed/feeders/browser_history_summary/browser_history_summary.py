import os
import html
import platform
from datetime import datetime, timedelta

from bs4 import BeautifulSoup
from bs4.element import Comment

import feed_utils
import hindsight_feed_db 
from feeders.browser_history_summary.browser_history import get_browser_history
from feeders.browser_history_summary.chromadb_tools import ingest_all_browser_history, get_chroma_collection, chroma_search_results_to_df
from feeders.content_generator import ContentGenerator
from feed_config import GENERATOR_DATA_DIR

import sys
sys.path.insert(0, "../../../../")
sys.path.insert(0, "../../../")
sys.path.insert(0, "./")

from hindsight_server.config import LLM_MODEL_NAME
from hindsight_server.query.query import load, llm_generate

class BrowserSummaryFeeder(ContentGenerator):
    def __init__(self, name, description, gen_type="BrowserSummaryFeeder", parameters=None):
        super().__init__(name=name, description=description, gen_type=gen_type, parameters=parameters)
        self.gen_type = gen_type
        self.data_dir = os.path.join(GENERATOR_DATA_DIR, f"{self.gen_type}/{self.id}")
        print(os.path.abspath(self.data_dir))
        feed_utils.make_dir(self.data_dir)
    
    def add_html_text(self, df):
        df['html'] = df['url'].apply(lambda x: feed_utils.get_html(x))
        df['html_text'] = df['html'].apply(lambda x: feed_utils.html_to_text(x))
        df = df.dropna(subset=['html_text'])
        df = df.drop_duplicates(subset=['html_text'])
        df = df.loc[df['html_text'].str.len() > 10]
        return df
    
    def get_summarize_prompt(self, html_text, topic=None):
        if topic is None:
            prompt = f"""Below is text from a webpage:\n {html_text}\n 
                Provide only a single bullet-point summary. Do not include any questions, answers, or follow-up statements. This is the summary:\n"""
        else:
            prompt = f"""Below is text from a webpage:\n {html_text}\n 
                Provide only a single bullet-point summary relevant to {topic}. Do not include any questions, answers, or follow-up statements. This is the summary:\n"""
        return prompt

    
    def generate_html_base(self, topic, html_path, stream_html_path):
        styles = '''
        <style>
            /* General Styles */
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #f0f2f5;
                color: #333;
                margin: 0;
                padding: 0;
                line-height: 1.6;
            }
            .container {
                max-width: 900px;
                margin: 20px auto;
                padding: 20px;
                background-color: #fff;
                border-radius: 8px;
                box-shadow: 0 6px 12px rgba(0, 0, 0, 0.1);
            }
            .header {
                font-size: 28px;
                text-align: center;
                color: #007BFF;
                margin-bottom: 20px;
            }
            .content-container {
                display: flex;
                align-items: center;
                padding: 20px;
                border-bottom: 1px solid #e1e4e8;
                background-color: #ffffff;
                border-radius: 8px;
                box-shadow: 0 6px 12px rgba(0, 0, 0, 0.1);
                margin-bottom: 20px;
                transition: transform 0.2s ease;
            }
            .content-container:last-child {
                border-bottom: none;
            }
            .content-container:hover {
                transform: translateY(-5px);
            }
            .thumbnail-container {
                flex-shrink: 0;
                margin-right: 15px;
            }
            .content-thumbnail {
                width: 100px;
                height: 100px;
                border-radius: 8px;
                object-fit: cover;
            }
            .text-container {
                flex-grow: 1;
            }
            .content-title {
                font-size: 20px;
                font-weight: bold;
                color: #007BFF;
                text-decoration: none;
                margin-bottom: 15px;
                display: block;
                transition: color 0.2s ease;
            }
            .content-title:hover {
                color: #0056b3;
            }
            .summary {
                font-size: 14px;
                color: #555;
                margin-top: 8px;
                white-space: pre-wrap;
            }
            .date-header {
                font-size: 18px;
                font-weight: bold;
                color: #555;
                margin-top: 20px;
                margin-bottom: 10px;
                padding-bottom: 5px;
                border-bottom: 2px solid #007BFF;
            }
        </style>
        '''

        header_html = f'<div class="header">{topic}</div>'

        place_holder_html = f"""
        <div class="container">
            {header_html}
            <div id="content-display"></div>
        </div>
        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                console.log('Streaming from this file');
                var filePath = window.location.pathname.split('/').slice(2).join('/');
                var eventSource = new EventSource(`{stream_html_path}`);
                eventSource.onmessage = function(event) {{
                    var contentWrapper = document.getElementById('content-display');
                    console.log('Streaming data', event.data);
                    contentWrapper.innerHTML = event.data;
                }};
            }});
        </script>
        """

        base_html = styles + place_holder_html
        with open(html_path, 'w') as outfile:
            outfile.write(base_html)

    def append_to_html(self, html_text, html_path):
        with open(html_path, 'a') as outfile:
            outfile.write(html_text)

    def get_url_summary_html(self, row):
        # Check for thumbnail and adjust HTML accordingly
        html_body = feed_utils.get_html(row['url'])
        html_text = feed_utils.html_to_text(html_body)
        if html_text is None:
            return None
        elif len(html_text) < 80:
            return None
        elif html_text in self.summarized_html_texts: # Remove duplicates
            return None
        self.summarized_html_texts.add(html_text) 

        topic = self.topic if self.gen_type != "TopicBrowserSummaryFeeder" else None
        summary_text = llm_generate(self.pipeline, prompt=self.get_summarize_prompt(html_text, topic=topic), max_tokens=30)
        summary_text = summary_text.split('.')[0]
        # print("HTML text:", html_text)
        # print()
        # print("Summary text", summary_text)
        thumbnail_url = feed_utils.get_thumbnail_url(row['url'], html_body)

        thumbnail_html = ""
        if thumbnail_url:
            thumbnail_html = f"""
                <div class="thumbnail-container">
                    <a href="{row['url']}" target="_blank">
                        <img src="{thumbnail_url}" alt="Thumbnail for {row['title']}" class="content-thumbnail">
                    </a>
                </div>
            """

        # Escape HTML special characters in the summary and convert newlines to HTML breaks
        escaped_summary = html.escape(summary_text).replace('\n', '<br>')

        # Combine all parts
        html_content = f"""
            <div class="content-container" data-content-id="{row['id']}">
                {thumbnail_html}
                <div class="text-container">
                    <a href="{row['url']}" target="_blank" onclick="trackClick({row['id']});" class="content-title">{row['title']}</a>
                    <div class="summary">{escaped_summary}</div>
                </div>
            </div>
        """
        return html_content
    
    def generate_html_content(self, results_history, html_path):        
        results_history = results_history.sort_values('datetime_local', ascending=False)
        results_history['day_accessed'] = results_history['datetime_local'].dt.date

        self.summarized_html_texts = set()

        for date in results_history.day_accessed.unique():
            date_df = results_history.loc[results_history['day_accessed'] == date]
            if self.gen_type != "YesterdayBrowserSummaryFeeder":
                self.append_to_html(f'<div class="date-header">Accessed on: {date}</div>', html_path)

            for i, row in date_df.iterrows():
                url_summary_html = self.get_url_summary_html(row)
                if url_summary_html is not None:
                    self.append_to_html(url_summary_html, html_path)

class YesterdayBrowserSummaryFeeder(BrowserSummaryFeeder):

    def __init__(self, name, description):
        super().__init__(name=name, description=description, gen_type="YesterdayBrowserSummaryFeeder")

    def get_yesterday_dates(self):
        now_utc = datetime.utcnow()
        yesterday_start = (now_utc - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_end = yesterday_start + timedelta(days=1, microseconds=-1)
        return yesterday_start, yesterday_end
    
    def get_yesterday_history(self, yesterday_start, yesterday_end):
        history = get_browser_history()
        return history.loc[(history['datetime_utc'].dt.date >= yesterday_start.date()) & (history['datetime_utc'].dt.date <= yesterday_end.date())]

    def get_url_text(self, row):
        return f"""Access time: {row['datetime_local']}\n
            Web Page summary: {row['summary']}\n
            """

    def get_yesterday_summary_prompt(self, df):
        prompt = f"Below are summaries extracted from different webpages that a user looked at yesterday. \n"
        for i, row in df.iterrows():
            prompt += self.get_url_text(row)
        prompt += "Create a list of topics the user was looking at. Answer: \n"
        return prompt

    def add_content(self):
        contents = hindsight_feed_db.fetch_contents(non_viewed=False, content_generator_id=self.id)
        yesterday_start, yesterday_end = self.get_yesterday_dates()
        if contents:
            # last_published_date = max([datetime.strptime(c.published_date, "%Y-%m-%d %H:%M:%S.%f") for c in contents])
            last_published_date = max([c.published_date for c in contents])
            if last_published_date >= yesterday_end:
                return

        print(f"Generating Yesterday's {yesterday_start} Browser History Summary")
        
        history = self.get_yesterday_history(yesterday_start=yesterday_start, yesterday_end=yesterday_end)
        if len(history) == 0:
            return
        print(f"Number of urls from yesterday: {len(history)}")

        now_utc = datetime.utcnow()         
        title = f"{yesterday_start}"
        summary_html_page_path = os.path.join(self.data_dir, f"""{title.replace(" ", "_")}-{now_utc.timestamp()}.html""")

        thumbnail_url = ""
        html_page_url = f"""/local/docs/{summary_html_page_path.replace(GENERATOR_DATA_DIR, "")}"""

        hindsight_feed_db.add_content(title, url=html_page_url, published_date=now_utc, 
                    ranking_score=100, content_generator_id=self.id, thumbnail_url=thumbnail_url)

        
        self.pipeline = load(LLM_MODEL_NAME) 
        self.generate_full_html(history, topic=title, html_path=summary_html_page_path)
                                              
        # yesterday_summary_prompt = self.get_yesterday_summary_prompt(history)

        print(f"Finished adding content for YesterdayBrowserSummaryFeeder for {yesterday_start}")
        
class TopicBrowserSummaryFeeder(BrowserSummaryFeeder):

    def __init__(self, name, description, topic, n_chroma_res=200, distance_threshold=1.2, topic_urls=None):
        parameters = {"topic" : topic, "n_chroma_res" : n_chroma_res, 
                      "distance_threshold" : distance_threshold, "topic_urls" : topic_urls}
        super().__init__(name=name, description=description, gen_type="TopicBrowserSummaryFeeder", parameters=parameters)
        self.topic = topic
        self.n_chroma_res = n_chroma_res
        self.distance_threshold = distance_threshold
        self.topic_urls = topic_urls

    def __str__(self):
        return f""

    def __repr__(self):
        return f""

    def get_url_text(self, row):
        return f"""Access time: {row['datetime_local']}\n
            Web Page summary: {row['summary']}\n
            """
    
    def get_relevant_history(self):
        if self.topic_urls is None:
            chroma_collection = get_chroma_collection(collection_name="browser_history")

            chroma_search_results = chroma_collection.query(
                        query_texts=[self.topic],
                        n_results=self.n_chroma_res
                )
            results_df = chroma_search_results_to_df(chroma_search_results=chroma_search_results)
            results_df = results_df.loc[results_df['distance'] <= self.distance_threshold]

            self.topic_urls = set(results_df['url'])
    
        history = get_browser_history()
        results_history = history.loc[history['url'].isin(self.topic_urls)]
        return results_history

    def get_topic_summary_prompt(self, df):
        prompt = f"Below are summaries extracted from different webpages that a user looked at yesterday. \n"
        for i, row in df.iterrows():
            prompt += self.get_url_text(row)
        prompt += "Create a list of topics the user was looking at. Answer: \n"
        return prompt

    def add_content(self):

        ingest_all_browser_history() # Ensure all Browser history is in chromadb
        
        history = self.get_relevant_history()
        if len(history) == 0:
            return
        print(f"Number of urls for topic: {len(history)}")

        title = f"{self.topic}"
        now_utc = datetime.utcnow()
        summary_html_page_path = os.path.join(self.data_dir, f"""{title.replace(" ", "_")}-{now_utc.timestamp()}.html""")

        thumbnail_url = ""
        html_page_url = f"""/local/docs/{summary_html_page_path.replace(GENERATOR_DATA_DIR, "")}"""
        stream_html_path = html_page_url.replace('/local/docs/', '/stream/docs/')
        self.generate_html_base(topic=self.topic, html_path=summary_html_page_path, stream_html_path=stream_html_path)

        hindsight_feed_db.add_content(title, url=html_page_url, published_date=now_utc, 
                    ranking_score=101, content_generator_id=self.id, thumbnail_url=thumbnail_url)
        
        self.pipeline = load(LLM_MODEL_NAME) 
        summary_html_content_path = summary_html_page_path.replace(".html", "_content.html")
        self.generate_html_content(history, html_path=summary_html_content_path)
                                              
        # topic_summary_prompt = self.get_topic_summary_prompt(history)
        
        print(f"Finished content from TopicBrowserSummaryFeeder for {self.topic}")  