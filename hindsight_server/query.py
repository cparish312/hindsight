import pandas as pd

from datetime import timedelta

from mlx_lm import load, generate

from prompts import get_prompt
from db import HindsightDB
from run_chromadb_ingest import get_chroma_collection
import utils
from config import MLX_LLM_MODEL

db = HindsightDB()

def chroma_search_results_to_df(chroma_search_results):
    results_l = list()
    for i in range(len(chroma_search_results['ids'])):
        for j in range(len(chroma_search_results['ids'][i])):
            d = {"chroma_query_id" : i, "id" : chroma_search_results['ids'][i][j],
                 "distance" : chroma_search_results['distances'][i][j], 
                 "document" : chroma_search_results['documents'][i][j]}
            d.update(chroma_search_results['metadatas'][i][j])
            results_l.append(d)
    return pd.DataFrame(results_l)

def query_chroma(query_text, source_apps=None, utc_milliseconds_start_date=None, utc_milliseconds_end_date=None, max_chroma_results=200):
    chroma_collection = get_chroma_collection()

    conditions = []
    if source_apps is not None:
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


def query(query_id, query_text, source_apps=None, utc_milliseconds_start_date=None, utc_milliseconds_end_date=None, max_chroma_results=100, per_usage_results=1):
    chroma_search_results = query_chroma(query_text, source_apps, utc_milliseconds_start_date, utc_milliseconds_end_date, max_chroma_results)
    chroma_search_results_df = chroma_search_results_to_df(chroma_search_results)
    if len(chroma_search_results_df) == 0:
        print("No relevant sources in chromadb")
        db.insert_query_result(query_id, "No relevant sources in chromadb", {})
        return
    chroma_search_results_df = chroma_search_results_df.drop_duplicates(subset=['document'])
    chroma_search_results_df = utils.add_datetimes(chroma_search_results_df).sort_values(by='datetime_local', ascending=True)

    # Take the smallest {per_usage_results} distances within a given usage
    chroma_search_results_df = utils.add_usage_ids(chroma_search_results_df, new_usage_threshold=timedelta(seconds=120))
    sel_df = chroma_search_results_df.groupby('usage_id')['distance'].nsmallest(per_usage_results).reset_index()
    chroma_search_results_df = chroma_search_results_df.merge(sel_df, on=['usage_id', 'distance'])

    chroma_search_results_df = chroma_search_results_df.sort_values(by="distance", ascending=True)
    chroma_search_results_df = chroma_search_results_df.iloc[:20]
    chroma_search_results_df = chroma_search_results_df.sort_values(by="datetime_local", ascending=True)

    combined_text = ""
    for t in chroma_search_results_df['document']:
        combined_text += "New Screenshot" + "-"*30 + "\n"
        combined_text += t

    model, tokenizer = load(MLX_LLM_MODEL)
    prompt = get_prompt(text=combined_text, query=query_text)
    response = generate(model, tokenizer, prompt=prompt)
    source_frame_ids = list(chroma_search_results_df['id'])
    db.insert_query_result(query_id, response, source_frame_ids)
