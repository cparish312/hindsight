import sys
import os
import pandas as pd
from exa_py import Exa

import hindsight_applications.hindsight_feed.feed_utils as feed_utils
from hindsight_applications.hindsight_feed.hindsight_feed_db import fetch_contents, df_add_contents
from hindsight_applications.hindsight_feed.feeders.content_generator import ContentGenerator

from hindsight_applications.hindsight_feed.feed_config import EXA_API_KEY

class ExaTopicFeeder(ContentGenerator):
    def __init__(self, name, description, topic, min_num_contents=10, parent_generator_id=None, find_similar=False, exclude_seen_urls=True):
        super().__init__(name=name, description=description, gen_type="ExaTopicFeeder", 
                         parameters={"topic" : topic, "min_num_contents" : min_num_contents, "parent_generator_id" : parent_generator_id, 
                                     "find_similar" : find_similar, "exclude_seen_urls" : exclude_seen_urls})
        self.topic = topic
        self.min_num_contents = min_num_contents
        self.find_similar = find_similar
        self.exclude_seen_urls = exclude_seen_urls
    
    def search_exa(self):
        exa = Exa(EXA_API_KEY)

        exclude_urls = list()
        if self.exclude_seen_urls:
            content = fetch_contents(non_viewed=False)
            seen_urls = {c.url.split("/")[2] for c in content}
            allow_urls = feed_utils.get_allow_urls()
            exclude_urls = list(seen_urls - allow_urls)[:100] # Need to optimize excluding urls based on likelihood to find

        if self.find_similar:
            exa_result = exa.find_similar_and_contents(
                self.topic,
                num_results=25,
                text=True,
                highlights=True,
                summary=True,
                exclude_domains=exclude_urls,
                livecrawl="always"
                )
        else:
            exa_result = exa.search_and_contents(
                self.topic,
                type="neural",
                use_autoprompt=True,
                num_results=25,
                text=True,
                highlights=True,
                summary=True,
                start_published_date=None,
                exclude_domains=exclude_urls,
                livecrawl="always"
                )
        
        results_l = list()
        for res in exa_result.results:
            res_d = res.__dict__
            res_d["content_generator_specific_data"] = res_d.copy()
            results_l.append(res_d)
        results_df = pd.DataFrame(results_l)
        return results_df
        
    def get_content(self):
        exa_results = self.search_exa()
        exa_results['thumbnail_url'] = exa_results['url'].apply(lambda x: feed_utils.get_thumbnail_url(x))
        exa_results['ranking_score'] = exa_results['score']
        exa_results = exa_results.drop(columns=["score"])
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