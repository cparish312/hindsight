from hindsight_feed_db import fetch_contents

class FeedGenerator():
    def __init__(self, content_generators=None):
        self.content_generators = content_generators if content_generators is not None else list()
        self.gen_contents()

    def gen_contents(self):
        for content_generator in self.content_generators:
            content_generator.add_content()

    def add_content_generator(self, content_generator):
        self.content_generators.append(content_generator)
        content_generator.add_content()

    def get_contents(self):
        # contents = fetch_contents(non_viewed=True)
        contents = fetch_contents(non_viewed=False)
        contents = sorted(contents, key=lambda a: (a.ranking_score, a.timestamp), reverse=True)
        return contents