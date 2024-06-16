import os
import chromadb
from chromadb import Documents, Embeddings, EmbeddingFunction
import sys

from mlx_embedding_models.embedding import EmbeddingModel

sys.path.insert(0, "../")
from db import HindsightDB
from config import DATA_DIR, MLX_EMBDEDDING_MODEL
import utils

db = HindsightDB()
chroma_db_path = os.path.join(DATA_DIR, "chromadb")

class MLXEmbeddingFunction(EmbeddingFunction):
    def __init__(self, model_id=MLX_EMBDEDDING_MODEL):
        self.embedding_model = EmbeddingModel.from_registry(model_id)

    def __call__(self, input: Documents) -> Embeddings:
        return self.embedding_model.encode(input).tolist()

def get_chroma_collection(collection_name="pixel_screenshots", model_id=MLX_EMBDEDDING_MODEL):
    embedding_function = MLXEmbeddingFunction(model_id=model_id)
    chroma_client = chromadb.PersistentClient(path=chroma_db_path)
    chroma_collection = chroma_client.get_or_create_collection(collection_name, embedding_function=embedding_function)
    return chroma_collection

def get_screenshot_preprompt(application, timestamp):
    return f"""Description: Text from a screenshot of {application} with UTC timestamp {timestamp}: \n""" + "-"*20 + "/n"

def get_chromadb_text(ocr_result, application, timestamp):
    frame_cleaned_text = utils.ocr_results_to_str(ocr_result)
    frame_text = get_screenshot_preprompt(application, timestamp) + frame_cleaned_text
    return frame_text

def get_chromadb_metadata(row):
    return {"frame_id" : row['id'], "application" : row['application'], "timestamp" : row['timestamp']}

def run_chroma_ingest(df, chroma_collection, ocr_results_df):
    documents = list()
    metadatas = list()
    ids = list()
    last_document = ""
    for i, row in df.iterrows():
        # ocr_result = db.get_ocr_results(frame_id=row['id'])
        ocr_result = ocr_results_df.loc[ocr_results_df['frame_id'] == row['id']]
        if len(ocr_result) == 0 or set(ocr_result['text']) == {None}:
            continue
        document = get_chromadb_text(ocr_result=ocr_result, application=row['application'], timestamp=row['timestamp'])
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
    print(f"Successfully added {len(documents)} documents to chromadb")

if __name__ == "__main__":
    frames = db.get_frames()
    ocr_results_df = db.get_frames_with_ocr()
    chroma_collection = get_chroma_collection()
    ingested_ids = [int(i) for i in chroma_collection.get()['ids']]
    # Remove already ingested frames
    frames = frames.loc[~(frames['id'].isin(ingested_ids))]

    print("Total frames to ingest", len(frames))
    batch_size = 1000
    num_batches = len(frames) // batch_size + (1 if len(frames) % batch_size > 0 else 0)
    for i in range(num_batches):
        print("Batch", i)
        start_index = i * batch_size
        end_index = start_index + batch_size
        frames_batch = frames.iloc[start_index:end_index]
        run_chroma_ingest(df=frames_batch, chroma_collection=chroma_collection, ocr_results_df=ocr_results_df)