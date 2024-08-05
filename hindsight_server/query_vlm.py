"""Scripts for running VLM queries on screenshot context."""
import gc
import cv2
import pandas as pd
import mlx

from datetime import timedelta

from mlx_lm import load, generate
from mlx_vlm import load as vlm_load
from mlx_vlm import generate as vlm_generate

from prompts import get_summary_prompt
from chromadb_tools import query_chroma, chroma_search_results_to_df
from db import HindsightDB
import utils
from config import MLX_LLM_MODEL
from config import MLX_VLM_MODEL

db = HindsightDB()

def run_vlm_query(im_path, query, model, processor):
    im = cv2.imread(im_path)
    # prompt = processor.tokenizer.apply_chat_template(
    #     [{"role": "user", "content": f"""<image>\nThis is a screenshot from my phone. Only use the information in the screenshot
    #       to answer the query provided. If you cannot effectively answer the query respond 'No Information'. Query: {query}"""}],
    #     tokenize=False,
    #     add_generation_prompt=True,
    #     max_tokens=100
    # )
    prompt = processor.tokenizer.apply_chat_template(
        [{"role": "user", "content": f"""<image>\nThis is a screenshot from my phone. Describe what is in the screenshot
          with as much detail as possible."""}],
        tokenize=False,
        add_generation_prompt=True,
        max_tokens=300
    )
    response = vlm_generate(model, processor, im, prompt, verbose=False)
    return response

def vlm_basic_retrieved_query(query_text, source_apps=None, utc_milliseconds_start_date=None, utc_milliseconds_end_date=None, 
                          max_chroma_results=100, num_contexts=10, per_usage_results=2, max_tokens=100, chroma_collection=None):
    """Grabs the closest per_usage_results frames within a usage. Runs each each against the VLM and combines the answers."""
    chroma_search_results = query_chroma(query_text, source_apps, utc_milliseconds_start_date, utc_milliseconds_end_date, max_chroma_results,
                                         chroma_collection=chroma_collection)
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

    frames_df = db.get_frames(frame_ids=set(chroma_search_results_df['frame_id']))[['id', 'path']]
    chroma_search_results_df = chroma_search_results_df.merge(frames_df, left_on='frame_id', right_on='id')

    model, processor = vlm_load(MLX_VLM_MODEL)

    responses = list()
    for i, row in chroma_search_results_df.iterrows():
        response = run_vlm_query(im_path=row['path'], query=query_text, model=model, processor=processor)
        responses.append(response)

    del model
    del processor
    gc.collect()
    mlx.core.metal.clear_cache()

    sep_str = "\n" + "-"*20 + "\n"
    combined_responses = sep_str.join(responses)
    summary_prompt = get_summary_prompt(text=combined_responses, query=query_text)
    print(summary_prompt)

    model, tokenizer = load(MLX_LLM_MODEL) 
    response = generate(model, tokenizer, prompt=summary_prompt, max_tokens=max_tokens)
    source_frame_ids = list(chroma_search_results_df['frame_id'])
    return response, source_frame_ids
