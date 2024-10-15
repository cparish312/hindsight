import os
import pandas as pd
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

from hindsight_applications.hindsight_feed.feed_config import DATA_DIR
from hindsight_applications.hindsight_feed.hindsight_feed_db import fetch_contents

chromadb_path = os.path.join(DATA_DIR, "chromadb")

def get_chroma_collection(collection_name="content"):
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

def get_content_chromadb_metadata(c):
    metadata_d = {"content_generator_id" : c.content_generator_id, "url" : c.url, "title" : c.title, "content_id" : c.id}
    metadata_d_cleaned = {} # Values cannot be None
    for k, v in metadata_d.items():
        if v is None:
            metadata_d_cleaned[k] = ""
        else:
            metadata_d_cleaned[k] = v
    return metadata_d_cleaned

def content_to_text(c):
    if "text" in c.content_generator_specific_data:
        return c.title + " " + c.content_generator_specific_data['text']
    else:
        return f"{c.title} {c.summary}"

def run_chroma_ingest(contents, chroma_collection):
    documents = list()
    metadatas = list()
    ids = list()
    for c in contents:
        documents.append(content_to_text(c))
        metadatas.append(get_content_chromadb_metadata(c))
        ids.append(str(c.id))

    if len(documents) == 0:
        return
    chroma_collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    print(f"Successfully added {len(documents)} documents to chromadb")

def run_chroma_ingest_batched(contents, chroma_collection, batch_size=1000):
    """Runs chromadb ingest in a batched fashion to balance efficiency and reliability."""
    num_batches = len(contents) // batch_size + (1 if len(contents) % batch_size > 0 else 0)
    for i in range(num_batches):
        print("Batch", i)
        start_index = i * batch_size
        end_index = start_index + batch_size
        contents_batch = contents[start_index:min(end_index, len(contents))]
        run_chroma_ingest(contents=contents_batch, chroma_collection=chroma_collection)

def ingest_contents(contents):
    contents_collection = get_chroma_collection(collection_name="content")
    ingested_content_ids = set(int(h) for h in contents_collection.get()['ids'])
    new_contents = [c for c in contents if c.id not in ingested_content_ids]
    print(f"Ingesting {len(new_contents)} new content")
    run_chroma_ingest_batched(new_contents, contents_collection)

def ingest_all_contents():
    contents = fetch_contents()
    ingest_contents(contents=contents)
