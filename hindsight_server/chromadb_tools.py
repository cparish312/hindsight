import os
import pandas as pd
import chromadb
from chromadb import Documents, Embeddings, EmbeddingFunction
from chromadb.utils import embedding_functions
import sys

sys.path.insert(0, "../")
from db import HindsightDB
from config import DATA_DIR, MLX_EMBDEDDING_MODEL, RUNNING_PLATFORM
import utils

if RUNNING_PLATFORM == 'Darwin':
    from mlx_embedding_models.embedding import EmbeddingModel

chroma_db_path = os.path.join(DATA_DIR, "chromadb")

DEFAULT_COLLECTION = "pixel_screenshots"

class MLXEmbeddingFunction(EmbeddingFunction):
    def __init__(self, model_id=MLX_EMBDEDDING_MODEL):
        self.embedding_model = EmbeddingModel.from_registry(model_id)

    def __call__(self, input: Documents) -> Embeddings:
        return self.embedding_model.encode(input).tolist()
    
    def embed_query(self, input: Documents) -> Embeddings:
        print("MLX EMBEDDING", type(input))
        return self.embedding_model.encode([input]).tolist()[0]


def get_chroma_collection(collection_name=DEFAULT_COLLECTION, model_id=MLX_EMBDEDDING_MODEL):
    """Returns chromadb collections."""
    if RUNNING_PLATFORM == 'Darwin':
        embedding_function = MLXEmbeddingFunction(model_id=model_id)
    else:
        embedding_function = embedding_functions.DefaultEmbeddingFunction()
    chroma_client = chromadb.PersistentClient(path=chroma_db_path)
    chroma_collection = chroma_client.get_or_create_collection(collection_name, embedding_function=embedding_function)
    return chroma_collection

def delete_chroma_collection(collection_name):
    chroma_client = chromadb.PersistentClient(path=chroma_db_path)
    chroma_client.delete_collection(name=collection_name)
    return f"Deleted {collection_name}"

def chroma_search_results_to_df(chroma_search_results):
    """Converts results from chromadb query to a pandas DataFrame"""
    results_l = list()
    for i in range(len(chroma_search_results['ids'])):
        for j in range(len(chroma_search_results['ids'][i])):
            d = {"chroma_query_id" : i, "id" : chroma_search_results['ids'][i][j],
                 "distance" : chroma_search_results['distances'][i][j]
                 }
            
            if chroma_search_results['embeddings']:
                d["embedding"] = chroma_search_results['embeddings'][i][j]
            if chroma_search_results['documents']:
                d["document"] = chroma_search_results['documents'][i][j]
            d.update(chroma_search_results['metadatas'][i][j])
            results_l.append(d)
    return pd.DataFrame(results_l)

def query_chroma(query_text: str, source_apps=None, utc_milliseconds_start_date=None, utc_milliseconds_end_date=None, 
                 max_chroma_results=200, chroma_collection=None, ):
    """Queries chromadb with the query_text and the provided constraints.
    Args:
        query_text (str): Text to query chromadb of OCR results from user screenshots

    returns query results from chroma collection
    """
    chroma_collection = get_chroma_collection() if chroma_collection is None else chroma_collection

    conditions = []
    if source_apps is not None:
        source_apps = list(source_apps)
        conditions.append({"application": {"$in": source_apps}})
    
    if utc_milliseconds_start_date is not None:
        conditions.append({"timestamp": {"$gte": int(utc_milliseconds_start_date)}})
    
    if utc_milliseconds_end_date is not None:
        conditions.append({"timestamp": {"$lte": int(utc_milliseconds_end_date)}})
    
    if len(conditions) > 1:
        chroma_search_results = chroma_collection.query(
            query_texts=[query_text],
            n_results=max_chroma_results,
            where={
                "$and": conditions
            }
        )
    elif len(conditions) == 1:
        chroma_search_results = chroma_collection.query(
            query_texts=[query_text],
            n_results=max_chroma_results,
            where=conditions[0]
        )
    else:
        chroma_search_results = chroma_collection.query(
            query_texts=[query_text],
            n_results=max_chroma_results,
        )
    return chroma_search_results

def get_chromadb_metadata(row):
    return {"frame_id" : row['id'], "application" : row['application'], "timestamp" : row['timestamp']}

def run_chroma_ingest(db, df, chroma_collection, ocr_results_df):
    """Runs chromadb ingest for frames in df. Will skip frames that have the same ocr results as the 
    prior frame.
    """
    documents = list()
    metadatas = list()
    ids = list()
    last_document = ""
    for i, row in df.iterrows():
        # ocr_result = db.get_ocr_results(frame_id=row['id'])
        ocr_result = ocr_results_df.loc[ocr_results_df['frame_id'] == row['id']]
        if len(ocr_result) == 0 or set(ocr_result['text']) == {None}:
            continue
        document = utils.get_preprompted_text(ocr_result=ocr_result, application=row['application'], timestamp=row['timestamp'])
        if last_document != document:
            documents.append(document)
            metadatas.append(get_chromadb_metadata(row))
            ids.append(str(row['id']))
            last_document = document

    if len(documents) == 0:
        db.update_chromadb_processed(frame_ids=set(df['id']))
        return
    chroma_collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    db.update_chromadb_processed(frame_ids=set(df['id']))
    print(f"Successfully added {len(documents)} documents to chromadb")

def run_chroma_ingest_batched(db, df, chroma_collection, batch_size=1000):
    """Runs chromadb ingest in a batched fashion to balance efficiency and reliability."""
    num_batches = len(df) // batch_size + (1 if len(df) % batch_size > 0 else 0)
    for i in range(num_batches):
        print("Batch", i)
        start_index = i * batch_size
        end_index = start_index + batch_size
        frames_batch = df.iloc[start_index:end_index]
        ocr_results_df = db.get_frames_with_ocr(frame_ids=set(frames_batch['id']))
        run_chroma_ingest(db=db, df=frames_batch, chroma_collection=chroma_collection, ocr_results_df=ocr_results_df)

if __name__ == "__main__":
    db = HindsightDB()
    frames_df = db.get_non_chromadb_processed_frames_with_ocr().sort_values(by='timestamp', ascending=True)
    frame_ids = set(frames_df['id'])
    print("Total frames to ingest", len(frame_ids))
    if len(frame_ids) > 0:
        chroma_collection = get_chroma_collection()
        run_chroma_ingest_batched(db, frames_df, chroma_collection=chroma_collection)