from sentence_transformers import SentenceTransformer
from scipy.spatial.distance import cosine

from hindsight_applications.hindsight_feed.hindsight_feed_db import fetch_contents, update_content_topic_label
from hindsight_applications.hindsight_feed.feed_utils import content_to_df
from hindsight_applications.hindsight_feed.chromadb_tools import get_chroma_collection, chroma_search_results_to_df

import matplotlib.pyplot as plt

def get_pred_text(row):
        pred_text = ""
        if isinstance(row['author'], str):
            pred_text += "Author: " + row['author'] + "\n"
        pred_text += "Title: " + row['title'] + "\n"
        # pred_text += "Summary: " + row['summary']
        pred_text += "Text: " + row['text']
        return pred_text

manual_labels = {"AI" : "Machine Learning and Artificial Intelligence including large language models", 
                 "Personal Feed" : "A personal news feed where the user controls the algorithm",
                 "Consiousness" : "The study of human consiousness"}
def add_manual_labels(content, embedding_model, manual_labels=manual_labels, similarity_threshold=0.15):
    labeled_content = set()
    label_to_embedding = [(label, embedding_model.encode(label_text)) for label, label_text in manual_labels.items()]
    for i, row in content.iterrows():
        similarities = [1 - cosine(row['embedding'], label_embedding) for label, label_embedding in label_to_embedding]
        max_similarity = max(similarities)
        most_similar_index = similarities.index(max(similarities))
        if max_similarity >= similarity_threshold:
            update_content_topic_label(row['id'], topic_label=label_to_embedding[most_similar_index][0])
            labeled_content.add(row['id'])
    return labeled_content

def label_unlabeled_content(manual_labels=manual_labels, similarity_threshold=0.15):
    content = fetch_contents(non_viewed=True)
    content = content_to_df(content)

    unlabeled_content = content.loc[content['topic_label'].isnull()]
    if len(unlabeled_content) == 0:
        return
    
    unlabeled_content['prediction_text'] = unlabeled_content.apply(lambda row: get_pred_text(row), axis=1)

    embedding_model = SentenceTransformer('all-mpnet-base-v2')
    embeddings = embedding_model.encode(unlabeled_content["prediction_text"].to_list())
    unlabeled_content["embedding"] = list(embeddings)
    labeled_content = add_manual_labels(content=content, embedding_model=embedding_model,
                                        manual_labels=manual_labels, similarity_threshold=similarity_threshold)