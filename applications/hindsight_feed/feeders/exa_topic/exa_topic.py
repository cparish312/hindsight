import sys
import os
import pandas as pd
from exa_py import Exa

import utils
from hindsight_feed_db import fetch_contents, df_add_contents
from feeders.content_generator import ContentGenerator

from config import DATA_DIR

exa_api_key_f = os.path.join(DATA_DIR, "exa_api.key")
if os.path.exists(exa_api_key_f):
    with open(exa_api_key_f, 'r') as infile:
        EXA_API_KEY = infile.read().strip()
else:
    raise(ValueError(f"Missing {exa_api_key_f}"))

class ExaTopicFeeder(ContentGenerator):
    def __init__(self, name, description, topic, min_num_contents=10):
        super().__init__(name=name, description=description, gen_type="ExaTopicFeeder", parameters={"topic" : topic, "min_num_contents" : min_num_contents})
        self.topic = topic
        self.min_num_contents = min_num_contents
    
    def search_exa(self):
        exa = Exa(EXA_API_KEY)
        exa_result = exa.search_and_contents(
            self.topic,
            type="neural",
            use_autoprompt=True,
            num_results=25,
            text=True,
            highlights=True,
            start_published_date=None
            )
        
        results_l = list()
        for res in exa_result.results:
            res_d = res.__dict__
            results_l.append(res_d)
        results_df = pd.DataFrame(results_l)
        return results_df
        
    def get_content(self):
        exa_results = self.search_exa()
        exa_results['thumbnail_url'] = exa_results['url'].apply(lambda x: utils.get_thumbnail_url(x))
        exa_results['ranking_score'] = exa_results['score']
        exa_results['title'] = exa_results['title'].fillna(exa_results['text']) # For tweets
        return exa_results
    
    def add_content(self):
        contents = fetch_contents(non_viewed=True, content_generator_id=self.id)
        if len(contents) >= self.min_num_contents:
            return

        print(f"{self.name} fetching content")
        exa_results = self.get_content()
        exa_results['content_generator_id'] = self.id
        exa_results['published_date'] = pd.to_datetime(exa_results['published_date'])
        exa_results['published_date'] = exa_results['published_date'].fillna(pd.Timestamp.now())
        df_add_contents(exa_results)