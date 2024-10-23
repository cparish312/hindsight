import os
import pickle
import numpy as np

from sentence_transformers import SentenceTransformer
import torch

from sklearn.model_selection import train_test_split

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

from hindsight_applications.hindsight_feed.feed_config import RANKER_DATA_DIR
from hindsight_applications.hindsight_feed.hindsight_feed_db import fetch_contents, update_content_ranked_score
from hindsight_applications.hindsight_feed.feed_utils import content_to_df

os.makedirs(RANKER_DATA_DIR, exist_ok=True)

class SentenceTransformersLinearRegRanker():
    def __init__(self):
        self.embedding_model = SentenceTransformer('all-mpnet-base-v2')
        self.model_save_path = os.path.join(RANKER_DATA_DIR, "sentence_transformers_reg_ranker.pkl")

    def get_pred_text(self, row):
        pred_text = ""
        if isinstance(row['author'], str):
            pred_text += "Author: " + row['author'] + "\n"
        pred_text += "Title: " + row['title'] + "\n"
        # pred_text += "Summary: " + row['summary']
        pred_text += "Text: " + row['text']
        return pred_text

    def train(self, content):
        content["prediction_text"] = content.apply(lambda row: self.get_pred_text(row), axis=1)

        content_embeddings = self.embedding_model.encode(content["prediction_text"].to_list())

        X = content_embeddings
        y = content['clicked'].values
        
        model = LogisticRegression(max_iter=1000, penalty='l2', C=1.0, solver='lbfgs')

        model.fit(X, y)

        y_pred_prob = model.predict_proba(X)[:, 1]

        auc_score = roc_auc_score(y, y_pred_prob)
        print(f'SentenceTransformersLinearRegRanker AUC: {auc_score:.4f}')

        with open(self.model_save_path, 'wb') as outfile:
            pickle.dump(model, outfile)

    def predict(self, content, add_random=True):
        if not os.path.exists(self.model_save_path):
            raise ValueError(f"Please Train model first as {self.model_save_path} does not exists.")
        
        content["prediction_text"] = content.apply(lambda row: self.get_pred_text(row), axis=1)
        
        content_embeddings = self.embedding_model.encode(content["prediction_text"].to_list())

        with open(self.model_save_path, 'rb') as infile:
            model = pickle.load(infile)

        preds = model.predict_proba(content_embeddings)[:, 1]

        if add_random:
            random_values = np.random.uniform(0, 1 - preds)
            preds += random_values

        return preds
    
    def generate_new_rankings(self, add_random=True):
        if not os.path.exists(self.model_save_path):
            self.generate_rankings(add_random=add_random)
        content = fetch_contents(non_viewed=True)
        content = content_to_df(content)

        non_ranked_content = content.loc[content['ranking_score'] <= 0]
        if len(non_ranked_content) == 0:
            return
        
        non_ranked_content['clicked_prediction_prob'] = self.predict(non_ranked_content, add_random=add_random)
        print(f"Created {len(non_ranked_content)} predictions")

        for i, row in non_ranked_content.iterrows():
            update_content_ranked_score(id=row["id"], ranking_score=row["clicked_prediction_prob"])
        
    def generate_rankings(self, add_random=True):
        content = fetch_contents(non_viewed=False)
        content = content_to_df(content)

        # Only want to train on content that has been viewed
        viewed_content = content.loc[content['viewed']]
        self.train(viewed_content)

        # Only want to predict on content that hasn't been viewed
        non_viewed_content = content.loc[~content['viewed']]
        non_viewed_content['clicked_prediction_prob'] = self.predict(non_viewed_content, add_random=add_random)
        print(f"Created {len(non_viewed_content)} predictions")

        for i, row in non_viewed_content.iterrows():
            update_content_ranked_score(id=row["id"], ranking_score=row["clicked_prediction_prob"])

        print("Successfully updated ranking score for non-viewed content")