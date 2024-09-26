import gc

from browser_history import get_browser_history
from chromadb_tools import get_chroma_collection, chroma_search_results_to_df, ingest_browser_history

gc.collect()

chroma_collection = get_chroma_collection(collection_name="browser_history")
history = get_browser_history()
ingest_browser_history(history)

def search_history(text, distance_threshold=0.5, top_n=2000, time_bin="M"):
    if text is None or text == "":
        results_history = history.copy()
    else:
        chroma_search_results = chroma_collection.query(
                query_texts=[text],
                n_results=top_n
        )
        results_df = chroma_search_results_to_df(chroma_search_results=chroma_search_results)
        results_df = results_df.loc[results_df['distance'] <= distance_threshold]

        results_history = history.loc[history['url'].isin(results_df['url'])]
    results_history['time_bin'] = results_history['datetime_local'].dt.to_period(time_bin)
    month_url_counts = results_history.groupby('time_bin').agg(
                                            num_urls=('url', 'count'),       
                                            urls=('url', list),
                                            titles=('title', list)        
                                        ).reset_index()
    data_points = [(t, n, u, titles) for t, n, u, titles in zip(month_url_counts['time_bin'], month_url_counts['num_urls'], month_url_counts['urls'], month_url_counts['titles'])]
    return data_points
