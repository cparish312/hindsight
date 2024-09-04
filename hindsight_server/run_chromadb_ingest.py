import os
import platform
import chromadb
from chromadb import Documents, Embeddings, EmbeddingFunction
from chromadb.utils import embedding_functions
import sys

if platform.system() == 'Darwin':
    from mlx_embedding_models.embedding import EmbeddingModel

sys.path.insert(0, "../")
from db import HindsightDB
from config import DATA_DIR, MLX_EMBDEDDING_MODEL
import utils

chroma_db_path = os.path.join(DATA_DIR, "chromadb")

class MLXEmbeddingFunction(EmbeddingFunction):
    def __init__(self, model_id=MLX_EMBDEDDING_MODEL):
        self.embedding_model = EmbeddingModel.from_registry(model_id)

    def __call__(self, input: Documents) -> Embeddings:
        return self.embedding_model.encode(input).tolist()

def get_chroma_collection(collection_name="pixel_screenshots", model_id=MLX_EMBDEDDING_MODEL):
    """Returns chromadb collections."""
    if platform.system() == 'Darwin':
        embedding_function = MLXEmbeddingFunction(model_id=model_id)
    else:
        embedding_function = embedding_functions.DefaultEmbeddingFunction()
    chroma_client = chromadb.PersistentClient(path=chroma_db_path)
    chroma_collection = chroma_client.get_or_create_collection(collection_name, embedding_function=embedding_function)
    return chroma_collection

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