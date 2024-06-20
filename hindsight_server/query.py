import pandas as pd

from datetime import timedelta

from mlx_lm import load, generate

from prompts import get_prompt, get_summary_prompt, get_recomposition_prompt, get_decomposition_prompt, get_summary_compete_prompt
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

def basic_retrieved_query(query_text, source_apps=None, utc_milliseconds_start_date=None, utc_milliseconds_end_date=None, 
                          max_chroma_results=100, num_contexts=20, per_usage_results=1, model=None, tokenizer=None):
    """Grabs the closest per_usage_results frames within a usage. Combines all contexts into a single prompt."""
    chroma_search_results = query_chroma(query_text, source_apps, utc_milliseconds_start_date, utc_milliseconds_end_date, max_chroma_results)
    chroma_search_results_df = chroma_search_results_to_df(chroma_search_results)
    if len(chroma_search_results_df) == 0:
        print("No relevant sources in chromadb")
        return None, None
    chroma_search_results_df = chroma_search_results_df.drop_duplicates(subset=['document'])
    chroma_search_results_df = utils.add_datetimes(chroma_search_results_df).sort_values(by='datetime_local', ascending=True)

    # Take the smallest {per_usage_results} distances within a given usage
    chroma_search_results_df = utils.add_usage_ids(chroma_search_results_df, new_usage_threshold=timedelta(seconds=120))
    sel_df = chroma_search_results_df.groupby('usage_id')['distance'].nsmallest(per_usage_results).reset_index()
    chroma_search_results_df = chroma_search_results_df.merge(sel_df, on=['usage_id', 'distance'])

    chroma_search_results_df = chroma_search_results_df.sort_values(by="distance", ascending=True)
    chroma_search_results_df = chroma_search_results_df.iloc[:num_contexts]
    chroma_search_results_df = chroma_search_results_df.sort_values(by="datetime_local", ascending=True)

    combined_text = ""
    for t in chroma_search_results_df['document']:
        combined_text += "New Context" + "-"*30 + "\n"
        combined_text += t

    prompt = get_prompt(text=combined_text, query=query_text)
    if model is None:
        model, tokenizer = load(MLX_LLM_MODEL) 
    response = generate(model, tokenizer, prompt=prompt)
    source_frame_ids = list(chroma_search_results_df['id'])
    return response, source_frame_ids

def long_context_query(query_text, source_apps=None, utc_milliseconds_start_date=None, utc_milliseconds_end_date=None,
                        max_chroma_results=100, num_contexts=10, per_usage_results=1, context_buffer=5, model=None, tokenizer=None):
    """Grabs the closest per_usage_results frames within a usage. Grabs """
    chroma_search_results = query_chroma(query_text, source_apps, utc_milliseconds_start_date, utc_milliseconds_end_date, max_chroma_results)
    chroma_search_results_df = chroma_search_results_to_df(chroma_search_results)
    if len(chroma_search_results_df) == 0:
        print("No relevant sources in chromadb")
        return None, None
    chroma_search_results_df = chroma_search_results_df.drop_duplicates(subset=['document'])
    chroma_search_results_df = utils.add_datetimes(chroma_search_results_df).sort_values(by='datetime_local', ascending=True)

    # Take the smallest {per_usage_results} distances within a given usage
    chroma_search_results_df = utils.add_usage_ids(chroma_search_results_df, new_usage_threshold=timedelta(seconds=120))
    sel_df = chroma_search_results_df.groupby('usage_id')['distance'].nsmallest(per_usage_results).reset_index()
    chroma_search_results_df = chroma_search_results_df.merge(sel_df, on=['usage_id', 'distance'])

    chroma_search_results_df = chroma_search_results_df.sort_values(by="distance", ascending=True)
    chroma_search_results_df = chroma_search_results_df.iloc[:num_contexts]
    chroma_search_results_df = chroma_search_results_df.sort_values(by="datetime_local", ascending=True)

    frames_df = db.get_frames()
    ocr_results_df = db.get_frames_with_ocr()

    if model is None:
        model, tokenizer = load(MLX_LLM_MODEL) 

    responses = list()
    for frame_id in chroma_search_results_df['id']:
        context_text = utils.get_context_around_frame_id(int(frame_id), frames_df, ocr_results_df, context_buffer=context_buffer)
        prompt = get_prompt(text=context_text, query=query_text)
        response = generate(model, tokenizer, prompt=prompt)
        responses.append(response)

    sep_str = "\n" + "-"*20 + "\n"
    combined_responses = sep_str.join(responses)
    summary_prompt = get_summary_prompt(text=combined_responses, query=query_text)
    response = generate(model, tokenizer, prompt=summary_prompt)
    source_frame_ids = list(chroma_search_results_df['id'])
    return response, source_frame_ids


def run_decomp_question_query(query_text, num_decomp_questions=4, source_apps=None, utc_milliseconds_start_date=None, utc_milliseconds_end_date=None, max_chroma_results=100, max_tokens=500,
                              model=None, tokenizer=None):
    decomp_prompt = get_decomposition_prompt(query_text, num_decomp_questions)
    if model is None:
        model, tokenizer = load(MLX_LLM_MODEL) 
    response = generate(model, tokenizer, prompt=decomp_prompt)
    decomp_questions = response.split("\n")[1:5]

    total_source_frame_ids = set()
    q_to_res = {}
    for q in decomp_questions:
        response, source_frame_ids = long_context_query(query_text=q, source_apps=source_apps, utc_milliseconds_start_date=utc_milliseconds_start_date, 
                                       utc_milliseconds_end_date=utc_milliseconds_end_date, max_chroma_results=max_chroma_results, model=model, tokenizer=tokenizer)
        if response is not None:
            q_to_res[q] = response
            total_source_frame_ids.update(set(source_frame_ids))

    recomp_prompt = get_recomposition_prompt(query_text, q_to_res)
    final_response = generate(model, tokenizer, prompt=recomp_prompt, max_tokens=max_tokens)
    return final_response, total_source_frame_ids


def query_and_insert(query_id, query_text, source_apps=None, utc_milliseconds_start_date=None, utc_milliseconds_end_date=None, max_chroma_results=100):
    query_type = "b" 
    if "\\" in query_text:
        query_text_s = query_text.split("\\")
        query_type = query_text_s[0]
        query_text = query_text_s[1]
    
    if query_type == "b":
        response, source_frame_ids = basic_retrieved_query(query_text, source_apps=source_apps, utc_milliseconds_start_date=utc_milliseconds_start_date, 
                                        utc_milliseconds_end_date=utc_milliseconds_end_date, max_chroma_results=max_chroma_results)
    elif query_type == "l":
        response, source_frame_ids = long_context_query(query_text, source_apps=source_apps, utc_milliseconds_start_date=utc_milliseconds_start_date, 
                                        utc_milliseconds_end_date=utc_milliseconds_end_date, max_chroma_results=max_chroma_results, num_contexts=10, 
                                        per_usage_results=1, context_buffer=5)
    elif query_type == "d":
        response, source_frame_ids = run_decomp_question_query(query_text, num_decomp_questions=4, source_apps=source_apps, utc_milliseconds_start_date=utc_milliseconds_start_date, 
                                        utc_milliseconds_end_date=utc_milliseconds_end_date, max_chroma_results=max_chroma_results)
    elif query_type == "a":
        model, tokenizer = load(MLX_LLM_MODEL) 
        response_b, source_frame_ids_b = basic_retrieved_query(query_text, source_apps=source_apps, utc_milliseconds_start_date=utc_milliseconds_start_date, 
                                        utc_milliseconds_end_date=utc_milliseconds_end_date, max_chroma_results=max_chroma_results, model=model, tokenizer=tokenizer)
        response_l, source_frame_ids_l = long_context_query(query_text, source_apps=source_apps, utc_milliseconds_start_date=utc_milliseconds_start_date, 
                                        utc_milliseconds_end_date=utc_milliseconds_end_date, max_chroma_results=max_chroma_results, num_contexts=10, 
                                        per_usage_results=1, context_buffer=5, model=model, tokenizer=tokenizer)
        response_d, source_frame_ids_d = run_decomp_question_query(query_text, num_decomp_questions=4, source_apps=source_apps, utc_milliseconds_start_date=utc_milliseconds_start_date, 
                                        utc_milliseconds_end_date=utc_milliseconds_end_date, max_chroma_results=max_chroma_results, model=model, tokenizer=tokenizer)
        method_to_text = {"Basic" : response_b, "Long Context" : response_l, "Decomposition" : response_d}
        summary_compete_prompt = get_summary_compete_prompt(method_to_text, query_text)
        response = generate(model, tokenizer, prompt=summary_compete_prompt, max_tokens=500)
        source_frame_ids = set(source_frame_ids_b) | set(source_frame_ids_l) | set(source_frame_ids_d)
    else:
        print("Invalid query type", query_type)
        db.insert_query_result(query_id, "Invalid query type", {})
        return

    if source_frame_ids is None:
        db.insert_query_result(query_id, "No relevant sources in chromadb", {})
    else:
        db.insert_query_result(query_id, response, source_frame_ids)
