"""Scripts for running LLM queries on screenshot context."""
import gc

from datetime import timedelta

from .prompts import get_prompt, get_summary_prompt, get_recomposition_prompt, get_decomposition_prompt, get_summary_compete_prompt
from chromadb_tools import query_chroma, chroma_search_results_to_df, get_chroma_collection
from db import HindsightDB
import utils
from config import LLM_MODEL_NAME, RUNNING_PLATFORM
# from query_vlm import vlm_basic_retrieved_query

if RUNNING_PLATFORM == 'Darwin':
    from mlx_lm import load, generate

    def llm_generate(pipeline, prompt, max_tokens):
        model, tokenizer = pipeline
        return generate(model, tokenizer, prompt=prompt, max_tokens=max_tokens)
else:
    from transformers import AutoTokenizer, AutoModelForCausalLM

    def load(model_name):
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(model_name)
        return model, tokenizer
    
    def llm_generate(pipeline, prompt, max_tokens):
        model, tokenizer = pipeline

        inputs = tokenizer(prompt, return_tensors="pt")

        outputs = model.generate(**inputs, max_length=max_tokens)

        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        return generated_text

db = HindsightDB()

def basic_retrieved_query(query_text, source_apps=None, utc_milliseconds_start_date=None, utc_milliseconds_end_date=None, 
                          max_chroma_results=100, num_contexts=20, per_usage_results=1, pipeline=None,
                          max_tokens=100, chroma_collection=None):
    """Grabs the closest per_usage_results frames within a usage. Combines all contexts into a single prompt."""
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

    combined_text = ""
    for t in chroma_search_results_df['document']:
        combined_text += "New Context" + "-"*30 + "\n"
        combined_text += t

    prompt = get_prompt(text=combined_text, query=query_text)
    if pipeline is None:
        pipeline = load(LLM_MODEL_NAME) 
    response = llm_generate(pipeline=pipeline, prompt=prompt, max_tokens=max_tokens)
    source_frame_ids = list(chroma_search_results_df['id'])
    return response, source_frame_ids

def long_context_query(query_text, source_apps=None, utc_milliseconds_start_date=None, utc_milliseconds_end_date=None,
                        max_chroma_results=100, num_contexts=10, per_usage_results=1, context_buffer=5, pipeline=None,
                        max_tokens=200, chroma_collection=None):
    """Grabs the closest per_usage_results frames within a usage. For each frame, grabs the number of context_buffer frames
    before and after the frame. It then passes these contexts to the LLM to get a response for each original usage frame.
    Finally, all of these results are passed to the LLM to get a final response.
    """
    chroma_collection = get_chroma_collection() if chroma_collection is None else chroma_collection
    chroma_search_results = query_chroma(query_text, source_apps, utc_milliseconds_start_date, utc_milliseconds_end_date, 
                                         max_chroma_results, chroma_collection=chroma_collection)
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

    if pipeline is None:
        pipeline = load(LLM_MODEL_NAME) 

    responses = list()
    for frame_id in chroma_search_results_df['id']:
        context_text = utils.get_context_around_frame_id(int(frame_id), frames_df, db, context_buffer=context_buffer)
        prompt = get_prompt(text=context_text, query=query_text)
        response = llm_generate(pipeline=pipeline, prompt=prompt, max_tokens=max_tokens)
        responses.append(response)

    sep_str = "\n" + "-"*20 + "\n"
    combined_responses = sep_str.join(responses)
    summary_prompt = get_summary_prompt(text=combined_responses, query=query_text)
    response = llm_generate(pipeline=pipeline, prompt=summary_prompt, max_tokens=max_tokens)
    source_frame_ids = list(chroma_search_results_df['id'])
    return response, source_frame_ids


def run_decomp_question_query(query_text, num_decomp_questions=4, source_apps=None, utc_milliseconds_start_date=None, utc_milliseconds_end_date=None, max_chroma_results=100, max_tokens=500,
                              pipeline=None, chroma_collection=None):
    """Uses a decompotion strategy to answer more advanced questions. The first step is to answer questions to help
    get the context needed to answer the original query. Check out README for more details.
    """
    chroma_collection = get_chroma_collection() if chroma_collection is None else chroma_collection
    decomp_prompt = get_decomposition_prompt(query_text, num_decomp_questions)
    if pipeline is None:
        pipeline = load(LLM_MODEL_NAME) 
    response = llm_generate(pipeline=pipeline, prompt=decomp_prompt)
    decomp_questions = response.split("\n")[1:num_decomp_questions + 1]

    total_source_frame_ids = set()
    q_to_res = {}
    for q in decomp_questions:
        response, source_frame_ids = long_context_query(query_text=q, source_apps=source_apps, utc_milliseconds_start_date=utc_milliseconds_start_date, 
                                       utc_milliseconds_end_date=utc_milliseconds_end_date, max_chroma_results=max_chroma_results, pipeline=pipeline, 
                                       chroma_collection=chroma_collection)
        if response is not None:
            q_to_res[q] = response
            total_source_frame_ids.update(set(source_frame_ids))

    recomp_prompt = get_recomposition_prompt(query_text, q_to_res)
    final_response = llm_generate(pipeline=pipeline, prompt=recomp_prompt, max_tokens=max_tokens)
    return final_response, total_source_frame_ids


def query_and_insert(query_id, query_text, source_apps=None, utc_milliseconds_start_date=None, utc_milliseconds_end_date=None, max_chroma_results=100):
    """Runs querying and inserts the results into the queries table."""
    # Default don't pull context from the hindsight app
    if source_apps is None:
        source_apps = db.get_all_applications() - {'com-connor-hindsight'}

    query_type = "b" 
    if "/" in query_text:
        query_text_s = query_text.split("/")
        query_type = query_text_s[0]
        query_text = "/".join(query_text_s[1:])
    
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
        pipeline = load(LLM_MODEL_NAME) 
        chroma_collection = get_chroma_collection()
        response_b, source_frame_ids_b = basic_retrieved_query(query_text, source_apps=source_apps, utc_milliseconds_start_date=utc_milliseconds_start_date, 
                                        utc_milliseconds_end_date=utc_milliseconds_end_date, max_chroma_results=max_chroma_results, pipeline=pipeline,
                                        chroma_collection=chroma_collection)
        response_l, source_frame_ids_l = long_context_query(query_text, source_apps=source_apps, utc_milliseconds_start_date=utc_milliseconds_start_date, 
                                        utc_milliseconds_end_date=utc_milliseconds_end_date, max_chroma_results=max_chroma_results, num_contexts=10, 
                                        per_usage_results=1, context_buffer=5, pipeline=pipeline, chroma_collection=chroma_collection)
        response_d, source_frame_ids_d = run_decomp_question_query(query_text, num_decomp_questions=4, source_apps=source_apps, utc_milliseconds_start_date=utc_milliseconds_start_date, 
                                        utc_milliseconds_end_date=utc_milliseconds_end_date, max_chroma_results=max_chroma_results, pipeline=pipeline,
                                        chroma_collection=chroma_collection)
        method_to_text = {"Basic" : response_b, "Long Context" : response_l, "Decomposition" : response_d}
        summary_compete_prompt = get_summary_compete_prompt(method_to_text, query_text)
        response = llm_generate(pipeline=pipeline, prompt=summary_compete_prompt, max_tokens=250)
        source_frame_ids = set(source_frame_ids_b) | set(source_frame_ids_l) | set(source_frame_ids_d)
    elif query_type == "v":
        pass
        # response, source_frame_ids = vlm_basic_retrieved_query(query_text, source_apps=source_apps, utc_milliseconds_start_date=utc_milliseconds_start_date, 
        #                             utc_milliseconds_end_date=utc_milliseconds_end_date, max_chroma_results=max_chroma_results)
    else:
        print("Invalid query type", query_type)
        db.insert_query_result(query_id, "Invalid query type", {})
        return

    if source_frame_ids is None:
        db.insert_query_result(query_id, "No relevant sources in chromadb", {})
    else:
        db.insert_query_result(query_id, response, source_frame_ids)

    gc.collect()