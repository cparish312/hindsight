"""Prompt templates"""
from utils import text_split_str

def get_prompt(text, query):
    return f"""Below is the text that's been on my phone screen. ------------- 
        {text}
        ------------------ Above is the text that's been on my screen recently. Please answer whatever I ask using the provided information about what has been on the screen recently. Do not say anything else or give any other information. 
        Only answer the query. -------------------------- {query}\nAnswer:"""

def get_prompt_multiple(text, query):
    return f"""Below is the text that's been on my phone screen. ------------- 
        {text}
        ------------------ Above is the text that's been on my screen recently. Please answer whatever I ask using the provided information about what has been on the screen recently. Do not say anything else or give any other information. 
        Multiple answers are allowed. Only answer the query. -------------------------- {query}\nAnswer:"""

def get_prompt_confident(text, query):
    return f"""Below is the text that's been on my phone screen. ------------- 
        {text}
        ------------------ Above is the text that's been on my screen recently. Please answer whatever I ask using the provided information about what has been on the screen recently. Do not say anything else or give any other information. 
        If you are not confident respond "None". Only answer the query. -------------------------- {query}\nAnswer:"""

def get_prompt_custom_additions(text, query, custom_additions):
    return f"""Below is the text that's been on my phone screen. ------------- 
        {text}
        ------------------ Above is the text that's been on my screen recently. Please answer whatever I ask using the provided information about what has been on the screen recently. Do not say anything else or give any other information. 
        {custom_additions} Only answer the query. -------------------------- {query}\nAnswer:"""

def get_summary_prompt(text, query):
    return f"""Below are the results from a number of LLM queries prompted with the question {query}.
            {text}
            ------------------
            Using these results as context. Answer the query: '{query}'\nAnswer:"""

def get_decomposition_prompt(query, num_decomp_questions):
    return f"""You are a helpful assistant that generates multiple sub-queries related to an input question. \n
        The goal is to break down the input into a set of sub-problems / sub-questions that can be answers in isolation. \n
        These queries will be passed into a embedding database to grab relevant context from text of a users' phone screenshots. \n
        Generate multiple search queries related to: {query} \n
        Output ({num_decomp_questions} queries)\nAnswer:"""

def get_recomposition_prompt(query, queries_to_res):
    prompt = """Below are a number of queries and responses from an LLM."""
    for q, r in queries_to_res.items():
        prompt += f"""Question: {q} \nResponse: {r}\n"""
    prompt += f"""Using this context answer the Question: {query}\nAnswer:"""
    return prompt

def get_summary_compete_prompt(method_to_text, query):
    prompt_str = f"""Below are the results from a number of LLM RAG pipelines asked to solve the query: {query}.\n"""
    for method, text in method_to_text.items():
          prompt_str += f"""Method : {method} \nResponse: {text}\n\n"""
          prompt_str += text_split_str
        
    prompt_str += f"Considering the query '{query}', what is the best and most helpful detailed response among the above? Please specify both the method and the detailed response.\nMethod: \nAnswer: "
    return prompt_str