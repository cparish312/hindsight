import os
import time
import sqlite3
import pandas as pd
from datetime import timedelta
from threading import Lock

import tzlocal
from zoneinfo import ZoneInfo

from config import DATA_DIR

local_timezone = tzlocal.get_localzone()
video_timezone = ZoneInfo("UTC")

DB_FILE = os.path.join(DATA_DIR, "hindsight.db")

demo_apps = {'android', 'com-connor-hindsight', 'com-android-phone', 'com-android-pixeldisplayservice', 'com-android-settings',  'com-github-android', 'com-reddit-frontpage', 'com-soundcloud-android', 'com-spotify-music'}

class HindsightDB:
    def __init__(self, db_file=DB_FILE):
        self.db_file = db_file
        self.db_lock = Lock()
        self.create_tables()

    def get_connection(self):
        """ Get a new connection every time for thread safety. """
        return sqlite3.connect(self.db_file)

    def create_tables(self):
        # Create the "frames" table if it doesn't exist
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS frames (
                    id INTEGER PRIMARY KEY,
                    timestamp INTEGER NOT NULL,
                    path TEXT NOT NULL,
                    application TEXT NOT NULL,
                    UNIQUE (timestamp, path)
                )
            ''')
            
            # Create the "ocr_results" table if it doesn't exist
            cursor.execute('''
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

            # cursor.execute('''
            #     DROP TABLE IF EXISTS queries
            # ''')

            # Tables for handling queries
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS queries (
                    id INTEGER PRIMARY KEY,
                    query TEXT NOT NULL,
                    result TEXT,
                    source_frame_ids TEXT,
                    timestamp INTEGER NOT NULL,
                    active BOOLEAN NOT NULL DEFAULT true
                )
            ''')

            # Commit the changes and close the connection
            conn.commit()

    def insert_frame(self, timestamp, path, application):
        with self.db_lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute('''
                        INSERT INTO frames (timestamp, path, application)
                        VALUES (?, ?, ?)
                    ''', (timestamp, path, application))
                    
                    # Get the last inserted frame_id
                    frame_id = cursor.lastrowid
                    conn.commit()
                    print(f"Frame added successfully with frame_id: {frame_id}")
                except sqlite3.IntegrityError:
                    # Frame already exists, get the existing frame_id
                    cursor.execute('''
                        SELECT id FROM frames
                        WHERE timestamp = ? AND path = ?
                    ''', (timestamp, path))
                    frame_id = cursor.fetchone()[0]
                    print(f"Frame already exists with frame_id: {frame_id}")
                
                return frame_id

    def insert_ocr_results(self, frame_id, ocr_results):
        with self.db_lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Insert multiple OCR results
                cursor.executemany('''
                    INSERT INTO ocr_results (frame_id, x, y, w, h, text, conf)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', [(frame_id, x, y, w, h, text, conf) for x, y, w, h, text, conf in ocr_results])
                
                conn.commit()
                
                print(f"{len(ocr_results)} OCR results added successfully.")

    def get_frames(self, frame_id=None):
        """Select frames with associated OCR results."""
        with self.get_connection() as conn:
            # Query to get frames
            if frame_id is None:
                query = '''SELECT * FROM frames'''
            else:
                query = f'''SELECT * FROM frames WHERE id = {frame_id}'''
            
            # Use pandas to read the SQL query result into a DataFrame
            df = pd.read_sql_query(query, conn)
            # df = df.loc[df['application'].isin(demo_apps)]
            return df
    
    def get_ocr_results(self, frame_id=None):
        with self.get_connection() as conn:
            if frame_id is None:
                query = '''SELECT * FROM ocr_results'''
            else:
                query = f'''SELECT * FROM ocr_results WHERE frame_id = {frame_id}'''
            # Use pandas to read the SQL query result into a DataFrame
            df = pd.read_sql_query(query, conn)
            return df

    def get_frames_with_ocr(self):
        """Select frames with associated OCR results."""
        with self.get_connection() as conn:
            # Query to get the frames with OCR results
            query = '''
                SELECT DISTINCT frames.id as frame_id, frames.timestamp, frames.path, frames.application, x, y, w, h, text, conf
                FROM frames
                INNER JOIN ocr_results ON frames.id = ocr_results.frame_id
            '''
            
            # Use pandas to read the SQL query result into a DataFrame
            df = pd.read_sql_query(query, conn)
            return df
    
    def search(self, text=None, start_date=None, end_date=None, apps=None, n_seconds=None):
        """Search for frames with OCR results containing the specified text. If n_seconds
        is provided it will only return 1 result within each n_seconds period.
        Bonus:
        Date and app filtering could be done in query to optimize but perfomance isn't currently
        an issue so leaning towards simplicity.
        """
        with self.get_connection() as conn:
            if text is None:
                query = '''
                SELECT frames.id, frames.path, frames.timestamp, frames.application, GROUP_CONCAT(ocr_results.text, ' ') AS combined_text
                FROM frames
                INNER JOIN ocr_results ON frames.id = ocr_results.frame_id
                GROUP BY frames.id
                '''
                df = pd.read_sql_query(query, conn)
            else:
                # Query to get the combined OCR text for each frame_id
                query = '''
                    SELECT frames.id, frames.path, frames.timestamp, frames.application, GROUP_CONCAT(ocr_results.text, ' ') AS combined_text
                    FROM frames
                    INNER JOIN ocr_results ON frames.id = ocr_results.frame_id
                    GROUP BY frames.id
                    HAVING combined_text LIKE ?
                '''
                df = pd.read_sql_query(query, conn, params=('%' + text + '%',))

            if apps:
                df = df.loc[df['application'].isin(apps)]

            # Convert timestamp to datetime
            df['datetime_utc'] = pd.to_datetime(df['timestamp'] / 1000, unit='s', utc=True)
            df['datetime_local'] = df['datetime_utc'].apply(lambda x: x.replace(tzinfo=video_timezone).astimezone(local_timezone))
            if start_date:
                df = df.loc[df['datetime_local'] >= start_date]

            if end_date:
                df = df.loc[df['datetime_local'] <= end_date]

            # Sort by timestamp
            df = df.sort_values(by='datetime_utc', ascending=False)
            # df = df.loc[df['application'].isin(demo_apps)]

            if n_seconds is None:
                return df
            
            # Select the most recent frame per N minutes
            result = []
            last_time = None
            for _, row in df.iterrows():
                if last_time is None or row['datetime_utc'] <= last_time - timedelta(seconds=n_seconds):
                    result.append(row)
                    last_time = row['datetime_utc']

            # Convert result to DataFrame
            result_df = pd.DataFrame(result)
            
            return result_df
        
    def insert_query(self, query):
        """Inserts query into queries table"""
        query_timestamp = int(time.time() * 1000) # UTC in milliseconds
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO queries (query, timestamp)
                VALUES (?, ?)
            ''', (query, query_timestamp))
            
            # Get the last inserted frame_id
            query_id = cursor.lastrowid
            conn.commit()
            print(f"Query added successfully with query_id: {query_id}")
            return query_id
        
    def insert_query_result(self, query_id, result, source_frame_ids):
        """Inserts the result of a query into the queries table"""
        # Convert source_frame_ids from a list or set to a comma-separated string
        source_frame_ids_str = ','.join(map(str, source_frame_ids))
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    UPDATE queries SET result = ?, source_frame_ids = ?
                    WHERE id = ?
                ''', (result, source_frame_ids_str, query_id))
                conn.commit()
                print(f"Query result added successfully for query_id: {query_id}")
            except sqlite3.Error as e:
                print(f"An error occurred: {e}")


    def get_active_queries(self):
        """Returns all active queries"""
        with self.get_connection() as conn:
            query = f'''SELECT * FROM queries WHERE active = true'''
            df = pd.read_sql_query(query, conn)
            return df