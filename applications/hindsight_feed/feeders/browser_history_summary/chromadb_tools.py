import os
import pandas as pd
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

from feeders.browser_history_summary.browser_history import get_browser_history

from config import DATA_DIR

chromadb_path = os.path.join(DATA_DIR, "chromadb")

def get_chroma_collection(collection_name="browser_history"):
    """Returns chromadb collections."""
    embedding_function = embedding_functions.DefaultEmbeddingFunction()
    chroma_client = chromadb.PersistentClient(path=chromadb_path)
    chroma_collection = chroma_client.get_or_create_collection(collection_name, embedding_function=embedding_function)
    return chroma_collection

def chroma_search_results_to_df(chroma_search_results):
    """Converts results from chromadb query to a pandas DataFrame"""
    results_l = list()
    for i in range(len(chroma_search_results['ids'])):
        for j in range(len(chroma_search_results['ids'][i])):
            d = {"chroma_query_id" : i, "id" : chroma_search_results['ids'][i][j],
                 "distance" : chroma_search_results['distances'][i][j]}
            
            if chroma_search_results['embeddings']:
                d["embedding"] = chroma_search_results['embeddings'][i][j]
            if chroma_search_results['documents']:
                d["document"] = chroma_search_results['documents'][i][j]
            d.update(chroma_search_results['metadatas'][i][j])
            results_l.append(d)
    return pd.DataFrame(results_l)

def get_browser_history_chromadb_metadata(row):
    metadata_d = {"url" : row['url'], "title" : row['title'], "timestamp" : row['timestamp']}
    metadata_d_cleaned = {} # Values cannot be None
    for k, v in metadata_d.items():
        if v is None:
            metadata_d_cleaned[k] = ""
        else:
            metadata_d_cleaned[k] = v
    return metadata_d_cleaned

def run_chroma_ingest(df, chroma_collection):
    documents = list()
    metadatas = list()
    ids = list()
    for i, row in df.iterrows():
        documents.append(row['title_description'])
        metadatas.append(get_browser_history_chromadb_metadata(row))
        ids.append(str(row['url_hash']))

    if len(documents) == 0:
        return
    chroma_collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    print(f"Successfully added {len(documents)} documents to chromadb")

def run_chroma_ingest_batched(df, chroma_collection, batch_size=1000):
    """Runs chromadb ingest in a batched fashion to balance efficiency and reliability."""
    num_batches = len(df) // batch_size + (1 if len(df) % batch_size > 0 else 0)
    for i in range(num_batches):
        print("Batch", i)
        start_index = i * batch_size
        end_index = start_index + batch_size
        batch_df = df.iloc[start_index:end_index]
        run_chroma_ingest(df=batch_df, chroma_collection=chroma_collection)

def ingest_browser_history(history):
    news_collection = get_chroma_collection(collection_name="browser_history")
    ingested_url_hashes = set(int(h) for h in news_collection.get()['ids'])
    total_num_urls = len(history)
    history = history.loc[~(history['url_hash'].isin(ingested_url_hashes))]
    print(f"Ingesting {len(history)} new urls out of {total_num_urls} total urls")
    run_chroma_ingest_batched(history, news_collection)

def ingest_all_browser_history():
    history_df = get_browser_history()
    ingest_browser_history(history=history_df)

if __name__ == "__main__":
    ingest_all_browser_history()