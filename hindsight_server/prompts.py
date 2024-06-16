def get_prompt(text, query):
    return f"""Below is the text that's been on my phone screen. ------------- 
        {text}
        ------------------ Above is the text that's been on my screen recently. Please answer whatever I ask using the provided information about what has been on the screen recently. Do not say anything else or give any other information. 
        Only answer the query. -------------------------- {query}"""

def get_prompt_multiple(text, query):
    return f"""Below is the text that's been on my phone screen. ------------- 
        {text}
        ------------------ Above is the text that's been on my screen recently. Please answer whatever I ask using the provided information about what has been on the screen recently. Do not say anything else or give any other information. 
        Multiple answers are allowed. Only answer the query. -------------------------- {query}"""

def get_prompt_confident(text, query):
    return f"""Below is the text that's been on my phone screen. ------------- 
        {text}
        ------------------ Above is the text that's been on my screen recently. Please answer whatever I ask using the provided information about what has been on the screen recently. Do not say anything else or give any other information. 
        If you are not confident respond "None". Only answer the query. -------------------------- {query}"""

def get_prompt_custom_additions(text, query, custom_additions):
    return f"""Below is the text that's been on my phone screen. ------------- 
        {text}
        ------------------ Above is the text that's been on my screen recently. Please answer whatever I ask using the provided information about what has been on the screen recently. Do not say anything else or give any other information. 
        {custom_additions} Only answer the query. -------------------------- {query}"""

def get_summary_prompt(text, query):
    return f"""Below are the results from a number of LLM queries prompted with the questions {query}.
            {text}
            ------------------
            What is the best answer to {query}? """