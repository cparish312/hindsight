import mlx
import gc

import sys
sys.path.insert(0, "../")

from db import HindsightDB
import utils
from chromadb_tools import get_chroma_collection, query_chroma, chroma_search_results_to_df, MLX_EMBDEDDING_MODEL
gc.collect()
mlx.core.metal.clear_cache()

chroma_collection = get_chroma_collection()
db = HindsightDB()

def create_initial_data_points():
    frames = db.get_frames()
    frames = utils.add_datetimes(frames)
    frames['month_year'] = frames['datetime_local'].dt.to_period('M')
    month_url_counts = frames.groupby('month_year').agg(
                            num_frames=('id', 'count'),       
                            frame_ids=('id', list),
                            applications=('application', list)    
                        ).reset_index()
    data_points = [(t, n, u, titles) for t, n, u, titles in zip(month_url_counts['month_year'], month_url_counts['num_frames'], month_url_counts['frame_ids'], month_url_counts['applications'])]
    return data_points

def search_history(text, distance_threshold=0.5, top_n=2000, time_bin="M", applications=None):
    if text is not None or text == "":
        if applications is None:
            chroma_search_results = chroma_collection.query(
                    query_texts=[text],
                    n_results=top_n
            )
        else:
            chroma_search_results = chroma_collection.query(
                    query_texts=[text],
                    n_results=top_n,
                    where={"application": {"$in": list(applications)}}
            )
        results_df = chroma_search_results_to_df(chroma_search_results=chroma_search_results)
        results_df = results_df.loc[results_df['distance'] <= distance_threshold]

        frames = db.get_frames(frame_ids=list(results_df['id']))
    else:
        frames = db.get_frames()
        if applications is not None:
            frames = frames.loc[frames['application_org'].isin(applications)]
    
    frames = utils.add_datetimes(frames)
    frames['time_bin'] = frames['datetime_local'].dt.to_period(time_bin)
    frame_id_counts = frames.groupby('time_bin').agg(
                                            num_frames=('id', 'count'),       
                                            frame_ids=('id', list),
                                            applications=('application', list)        
                                        ).reset_index()
    data_points = [(t, n, i, apps) for t, n, i, apps in zip(frame_id_counts['time_bin'], frame_id_counts['num_frames'], frame_id_counts['frame_ids'], frame_id_counts['applications'])]
    return data_points
