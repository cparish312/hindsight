import sys
sys.path.insert(0, "../")

from hindsight_feed_db import add_content_generator

class ContentGenerator():
    def __init__(self, name, gen_type, description=None):
        self.name = name
        self.description = description
        self.id = add_content_generator(name=name, gen_type=gen_type, description=description)