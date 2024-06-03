import os
import sqlite3
import pandas as pd
from datetime import timedelta

import tzlocal
from zoneinfo import ZoneInfo

from hindsight_server import DATA_DIR

local_timezone = tzlocal.get_localzone()
video_timezone = ZoneInfo("UTC")

DB_FILE = os.path.join(DATA_DIR, "hindsight.db")

class HindsightDB:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Create the "frames" table if it doesn't exist
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS frames (
                id INTEGER PRIMARY KEY,
                timestamp INTEGER NOT NULL,
                path TEXT NOT NULL,
                application TEXT NOT NULL,
                UNIQUE (timestamp, path)
            )
        ''')

        # Create the "ocr_results" table if it doesn't exist
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS ocr_results (
                id INTEGER PRIMARY KEY,
                frame_id INTEGER NOT NULL,
                x DOUBLE NOT NULL,
                y DOUBLE NOT NULL,
                w DOUBLE NOT NULL,
                h DOUBLE NOT NULL,
                text TEXT,
                conf DOUBLE NOT NULL,
                FOREIGN KEY (frame_id) REFERENCES frames(id)
            )
        ''')

        # Commit the changes and close the connection
        self.conn.commit()

    def insert_frame(self, timestamp, path, application):
        try:
            self.cursor.execute('''
                INSERT INTO frames (timestamp, path, application)
                VALUES (?, ?, ?)
            ''', (timestamp, path, application))
            
            # Get the last inserted frame_id
            frame_id = self.cursor.lastrowid
            self.conn.commit()
            print(f"Frame added successfully with frame_id: {frame_id}")
        except sqlite3.IntegrityError:
            # Frame already exists, get the existing frame_id
            self.cursor.execute('''
                SELECT id FROM frames
                WHERE timestamp = ? AND path = ?
            ''', (timestamp, path))
            frame_id = self.cursor.fetchone()[0]
            print(f"Frame already exists with frame_id: {frame_id}")
        
        return frame_id

    def insert_ocr_results(self, frame_id, ocr_results):
        # Insert multiple OCR results
        self.cursor.executemany('''
            INSERT INTO ocr_results (frame_id, x, y, w, h, text, conf)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', [(frame_id, x, y, w, h, text, conf) for x, y, w, h, text, conf in ocr_results])
        
        self.conn.commit()
        
        print(f"{len(ocr_results)} OCR results added successfully.")

    def get_frames(self):
        """Select frames with associated OCR results."""
        # Query to get frames
        query = '''SELECT * FROM frames'''
        
        # Use pandas to read the SQL query result into a DataFrame
        df = pd.read_sql_query(query, self.conn)
        return df
    
    def get_ocr_results(self, frame_id=None):
        if frame_id is None:
            query = '''SELECT * FROM ocr_results'''
        else:
            query = f'''SELECT * FROM ocr_results WHERE frame_id = {frame_id}'''
        # Use pandas to read the SQL query result into a DataFrame
        df = pd.read_sql_query(query, self.conn)
        return df

    def get_frames_with_ocr(self):
        """Select frames with associated OCR results."""
        # Query to get the frames with OCR results
        query = '''
            SELECT DISTINCT frames.id as frame_id, frames.timestamp, frames.path, frames.application, x, y, w, h, text, conf
            FROM frames
            INNER JOIN ocr_results ON frames.id = ocr_results.frame_id
        '''
        
        # Use pandas to read the SQL query result into a DataFrame
        df = pd.read_sql_query(query, self.conn)
        return df
    
    def search_text(self, text, n_seconds=None):
        """Search for frames with OCR results containing the specified text. If n_seconds
        is provided it will only return 1 result within each n_seconds period"""
        # Query to get the combined OCR text for each frame_id
        query = '''
            SELECT frames.id, frames.path, frames.timestamp, GROUP_CONCAT(ocr_results.text, ' ') AS combined_text
            FROM frames
            INNER JOIN ocr_results ON frames.id = ocr_results.frame_id
            GROUP BY frames.id
            HAVING combined_text LIKE ?
        '''
        
        # Use pandas to read the SQL query result into a DataFrame
        df = pd.read_sql_query(query, self.conn, params=('%' + text + '%',))
        if n_seconds is None:
            return df

        # Convert timestamp to datetime
        df['datetime_utc'] = pd.to_datetime(df['timestamp'] / 1000, unit='s', utc=True)

        # Sort by timestamp
        df = df.sort_values(by='datetime_utc', ascending=False)

        # Select the most recent frame per N minutes
        result = []
        last_time = None
        for _, row in df.iterrows():
            if last_time is None or row['datetime_utc'] <= last_time - timedelta(seconds=n_seconds):
                result.append(row)
                last_time = row['datetime_utc']

        # Convert result to DataFrame
        result_df = pd.DataFrame(result)
        result_df['datetime_local'] = result_df['datetime_utc'].apply(lambda x: x.replace(tzinfo=video_timezone).astimezone(local_timezone))
        
        return result_df