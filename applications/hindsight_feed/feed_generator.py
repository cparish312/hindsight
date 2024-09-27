from hindsight_feed_db import fetch_contents, fetch_content_generators

from feeders.exa_topic.exa_topic import ExaTopicFeeder
from feeders.browser_history_summary.browser_history_summary import TopicBrowserSummaryFeeder

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
    def __init__(self, content_generators=None):
        self.content_generators = content_generators if content_generators is not None else self.get_database_generators()
        self.gen_contents()

    def get_database_generators(self):
        content_generator_rows = fetch_content_generators()
        content_generators = list()
        for content_generator_row in content_generator_rows:
            content_generators.append(create_content_generator(content_generator_row))
        return content_generators

    def gen_contents(self):
        for content_generator in self.content_generators:
            if not isinstance(content_generator, TopicBrowserSummaryFeeder):
                content_generator.add_content()

    def add_content_generator(self, content_generator):
        self.content_generators.append(content_generator)
        content_generator.add_content()

    def get_contents(self):
        # contents = fetch_contents(non_viewed=True)
        contents = fetch_contents(non_viewed=False)
        contents = sorted(contents, key=lambda a: (a.ranking_score, a.timestamp), reverse=True)
        return contents