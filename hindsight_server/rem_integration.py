import sys
import sqlite3
import pandas as pd

import matplotlib.pyplot as plt

sys.path.insert(0, "/Users/connorparish/code/hindsight")

from hindsight_server.db import HindsightDB

source_name = "rem"
rem_db_path = "/Users/connorparish/Library/Containers/today.jason.rem/Data/Library/Application Support/today.jason.rem/db.sqlite3"

def get_ocr_res(frame_ids, conn):
    """Gets all ocr results for given frame_ids from the REM frames_text table."""
    query = "SELECT * from frames_text"
    if frame_ids is not None:
        placeholders = ','.join(['?'] * len(frame_ids))  # Create placeholders for the query
        query += f" WHERE frameId IN ({placeholders})"

    # Use pandas to read the SQL query result into a DataFrame
    df = pd.read_sql_query(query, conn, params=tuple(frame_ids) if frame_ids else None)
    return df

def ingest_rem():
    """Ingests all REM frames and ocr_results into the Hindsight database."""
    hindsight_db = HindsightDB()
    rem_conn = sqlite3.connect(rem_db_path)

    frames = pd.read_sql("SELECT * from frames", con=rem_conn)
    frames["int_timestamp"] = pd.to_datetime(frames['timestamp']).astype('int64') // 10**6
    frames["activeApplicationName"] = frames["activeApplicationName"].fillna("None")

    all_video_chunks = pd.read_sql("SELECT * from video_chunks", con=rem_conn)

    last_video_chunk_id = hindsight_db.get_last_id(source=source_name, table="video_chunks")
    video_chunks = all_video_chunks
    if last_video_chunk_id != None:
        video_chunks = video_chunks.loc[video_chunks['id'] > last_video_chunk_id]

    video_chunks = video_chunks.sort_values(by="id")
    print(f"Syncing {len(video_chunks)} REM video chunks")

    video_chunks_batch_size = 100

    num_batches = len(video_chunks) // video_chunks_batch_size + (1 if len(video_chunks) % video_chunks_batch_size > 0 else 0)
    for i in range(num_batches):
        print("REM sync Batch", i)
        start_index = i * video_chunks_batch_size
        end_index = start_index + video_chunks_batch_size
        video_chunks_batch = video_chunks.iloc[start_index:end_index]
        # Video chunks done to speed up by grabbing more OCR results at once
        video_chunk_frames = frames.loc[frames['chunkId'].isin(video_chunks_batch['id'])]
        video_batch_ocr_res = get_ocr_res(frame_ids=list(video_chunk_frames['id']), conn=rem_conn)
        for _, video_row in video_chunks_batch.iterrows():
            print(video_row['id'])
            video_frames = video_chunk_frames.loc[video_chunk_frames['chunkId'] == video_row['id']]
            video_chunk_id = hindsight_db.insert_video_chunk(video_row["filePath"], source=source_name, source_id=video_row['id'])
            # The video chunk id from the rem video_chunks table
            for _, frame_row in video_frames.iterrows():
                frame_id = hindsight_db.insert_frame(timestamp=frame_row['int_timestamp'], path="None", application=frame_row["activeApplicationName"],
                                        source=source_name, source_id=frame_row['id'], video_chunk_id=video_chunk_id, video_chunk_offset=frame_row['offsetIndex'])
                
                # The frame id from the rem frames table
                frame_ocr_res = video_batch_ocr_res.loc[video_batch_ocr_res['frameId'] == frame_row["id"]]
                converted_ocr_results = list()
                for _, ocr_result in frame_ocr_res.iterrows():
                    converted_ocr_results.append((ocr_result['x'], ocr_result['y'], ocr_result['w'],
                                                ocr_result['h'], ocr_result['text'], -1, -1, -1))
                hindsight_db.insert_ocr_results(frame_id=frame_id, ocr_results=converted_ocr_results)

