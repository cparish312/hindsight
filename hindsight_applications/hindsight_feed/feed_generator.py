from hindsight_applications.hindsight_feed.hindsight_feed_db import fetch_contents, fetch_content_generators

from hindsight_applications.hindsight_feed.feeders.exa_topic.create_new_topics import create_new_topics, create_new_topics_viewed_random
from hindsight_applications.hindsight_feed.feeders.exa_topic.exa_topic import ExaTopicFeeder
from hindsight_applications.hindsight_feed.feeders.browser_history_summary.browser_history_summary import TopicBrowserSummaryFeeder
from hindsight_applications.hindsight_feed.chromadb_tools import ingest_all_contents

name_to_content_generator = {"ExaTopicFeeder" : ExaTopicFeeder, 
                             "TopicBrowserSummaryFeeder" : TopicBrowserSummaryFeeder}

def create_content_generator(content_generator_row):
    content_generator_type = name_to_content_generator[content_generator_row.gen_type]
    parameters = content_generator_row.parameters or {}
    return content_generator_type(
            **parameters,
            name=content_generator_row.name,
            description=content_generator_row.description,
            )

class FeedGenerator():
    def __init__(self, content_generators=None, min_num_content=200):
        self.content_generators = content_generators if content_generators is not None else self.get_database_generators()
        self.min_num_content = min_num_content
        # self.generate_content()

    def get_database_generators(self):
        content_generator_rows = fetch_content_generators()
        content_generators = list()
        # for content_generator_row in content_generator_rows:
        #     content_generators.append(create_content_generator(content_generator_row))
        return content_generators

    def gen_contents_from_generators(self):
        for content_generator in self.content_generators:
            if not isinstance(content_generator, TopicBrowserSummaryFeeder):
                content_generator.add_content()
        ingest_all_contents()

    def add_content_generator(self, content_generator):
        content_generator.add_content()
        self.content_generators.append(content_generator)
        ingest_all_contents()

    def get_contents(self):
        contents = fetch_contents(non_viewed=True)
        # contents = fetch_contents(non_viewed=False)
        contents = sorted(contents, key=lambda a: (a.ranking_score, a.timestamp), reverse=True)
        # contents = sorted(contents, key=lambda a: (a.timestamp, a.ranking_score), reverse=True)
        return contents
    
    def generate_content(self):
        contents = self.get_contents()
        num_topics_to_gen = max((self.min_num_content - len(contents)) // 20, 0)
        if num_topics_to_gen == 0:
            return
        
        print(f"Attempting to generate {num_topics_to_gen} new topics by topic modeling")
        new_topics = create_new_topics(num_topics=num_topics_to_gen)
        
        for new_topic in new_topics:
            new_topic_ = new_topic.replace(" ", "_")
            self.add_content_generator(ExaTopicFeeder(name=f"exa_autogen_topic_{new_topic_}", 
                                                        description="ExaTopicFeeder generated by topic modeling content that was clicked on",
                                                        topic=new_topic))
        
        print(f"Successfully added New content for {len(new_topics)} topics")

        print(f"Attempting to generate {1} new topics by random viewed sampling")
        new_rand_topics = create_new_topics_viewed_random(num_topics=1)
        for new_topic in new_rand_topics:
            new_topic_ = new_topic.replace(" ", "_")
            self.add_content_generator(ExaTopicFeeder(name=f"exa_autogen_rand_{new_topic_}", 
                                                        description="ExaTopicFeeder generated by randomly samping viewed content",
                                                        topic=new_topic))