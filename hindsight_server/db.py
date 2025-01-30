"""Code for interfacing with SQLite database."""
import os
import time
import shutil
import sqlite3
import numpy as np
import pandas as pd
from datetime import timedelta

import portalocker

import tzlocal
from zoneinfo import ZoneInfo

from hindsight_server.config import DATA_DIR, RAW_SCREENSHOTS_DIR
import hindsight_server.utils as utils

local_timezone = tzlocal.get_localzone()
video_timezone = ZoneInfo("UTC")

DB_FILE = os.path.join(DATA_DIR, "hindsight.db")

class HindsightDB:
    def __init__(self, db_file=DB_FILE):
        self.db_file = db_file
        self.lock_file = db_file + '.lock'
        self.create_tables()

    def get_connection(self):
        """Get a new connection every time for thread safety."""
        connection = sqlite3.connect(self.db_file, timeout=50)
        connection.execute('PRAGMA journal_mode=WAL;')
        connection.execute('PRAGMA busy_timeout = 10000;')
        return connection
    
    def with_lock(func):
        """Decorator to handle database locking."""
        def wrapper(self, *args, **kwargs):
            with open(self.lock_file, 'a') as lock_file:
                portalocker.lock(lock_file, portalocker.LOCK_EX)
                try:
                    result = func(self, *args, **kwargs)
                finally:
                    portalocker.unlock(lock_file)
                return result
        return wrapper

    @with_lock
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
                    chromadb_processed BOOLEAN NOT NULL DEFAULT false,
                    source TEXT,
                    source_id INTEGER,
                    video_chunk_id INTEGER,
                    video_chunk_offset INTEGER,
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
                    block_num INTEGER,
                    line_num INTEGER,
                    FOREIGN KEY (frame_id) REFERENCES frames(id)
                )
            ''')

            # Tables for handling queries
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS queries (
                    id INTEGER PRIMARY KEY,
                    query TEXT NOT NULL,
                    result TEXT,
                    source_frame_ids TEXT,
                    timestamp INTEGER NOT NULL,
                    active BOOLEAN NOT NULL DEFAULT true,
                    finished_timestamp INTEGER,
                    context_start_timestamp INTEGER,
                    context_end_timestamp INTEGER,
                    context_applications TEXT
                )
            ''')

            # Create locations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS locations (
                    timestamp INTEGER NOT NULL PRIMARY KEY,
                    latitude DOUBLE NOT NULL,
                    longitude DOUBLE NOT NULL
                )
            ''')

            # Create locations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS annotations (
                    timestamp INTEGER NOT NULL PRIMARY KEY,
                    text TEXT
                )
            ''')

            # Create labels table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS labels (
                    frame_id INTEGER NOT NULL,
                    label TEXT NOT NULL,
                    value TEXT 
                )
            ''')

            # Create video_chunks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS video_chunks (
                    id INTEGER PRIMARY KEY,
                    path TEXT NOT NULL,
                    source TEXT,
                    source_id INTEGER,
                    UNIQUE (path)
                )
            ''')

            cursor.execute('''
                PRAGMA table_info(video_chunks)
            ''')
            columns = [row[1] for row in cursor.fetchall()]
            if 'source' not in columns:
                cursor.execute('''
                    ALTER TABLE video_chunks
                    ADD COLUMN source TEXT
                ''')
                cursor.execute('''
                    ALTER TABLE video_chunks
                    ADD COLUMN source_id INTEGER
                ''')

            # Commit the changes and close the connection
            conn.commit()

    @with_lock
    def insert_frame(self, timestamp, path, application, source=None, source_id=None, video_chunk_id=None, video_chunk_offset=None):
        """Insert frame into frames table and return frame_id."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO frames (timestamp, path, application, source, source_id, video_chunk_id, video_chunk_offset)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (timestamp, path, application, source, source_id, video_chunk_id, video_chunk_offset))
                
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
        
    @with_lock
    def insert_video_chunk(self, path, source=None, source_id=None):
        """Insert frame into frames table and return frame_id."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO video_chunks (path, source, source_id)
                    VALUES (?, ?, ?)
                ''', (path, source, source_id,))
                
                # Get the last inserted frame_id
                video_chunk_id = cursor.lastrowid
                conn.commit()
                print(f"Video Chunk added successfully with video_chunk_id: {video_chunk_id}")
            except sqlite3.IntegrityError:
                # Frame already exists, get the existing frame_id
                cursor.execute('''
                    SELECT id FROM video_chunks
                    WHERE path = ?
                ''', (path))
                video_chunk_id= cursor.fetchone()[0]
                print(f"Video Chunk already exists with video_chunk_id: {video_chunk_id}")
            
            return video_chunk_id

    @with_lock
    def insert_ocr_results(self, frame_id, ocr_results):
        """Insert ocr results into ocr_results table."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Insert multiple OCR results
            cursor.executemany('''
                INSERT INTO ocr_results (frame_id, x, y, w, h, text, conf, block_num, line_num)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', [(frame_id, x, y, w, h, text, conf, block_num, line_num) for x, y, w, h, text, conf, block_num, line_num in ocr_results])
            
            conn.commit()

    def get_all_applications(self):
        """Returns all applications in the frames table."""
        with self.get_connection() as conn:
            # Query to get the frames with OCR results
            query = '''
                SELECT DISTINCT frames.application
                FROM frames
            '''
            
            # Use pandas to read the SQL query result into a DataFrame
            df = pd.read_sql_query(query, conn)
            return set(df['application'])
        
    def get_screenshots(self, frame_ids=None, impute_applications=False, application_alias=True):
        """Select frames with associated OCR results."""
        with self.get_connection() as conn:
            excluded_apps = ("frontCamera", "backCamera")
            # Query to get frames
            query = '''SELECT frames.*, 
                            video_chunks.path as video_chunk_path
                            FROM frames LEFT JOIN video_chunks ON frames.video_chunk_id = video_chunks.id
                            WHERE application NOT IN (?, ?)'''
            params = excluded_apps

            # Extend the query to filter by frame_ids if provided
            if frame_ids:
                placeholders = ','.join(['?'] * len(frame_ids))
                query += f" AND id IN ({placeholders})"
                params += tuple(frame_ids)
            
            # Use pandas to read the SQL query result into a DataFrame
            df = pd.read_sql_query(query, conn, params=params)
            if impute_applications:
                df = utils.impute_applications(df)

            df['application_org'] = df['application'].copy()
            if application_alias:
                id_to_alias = utils.get_identifiers_to_alias()
                df['application'] = df['application'].map(id_to_alias)
                df['application'] = df['application'].fillna(df['application_org'])
            return df

    def get_frames(self, frame_ids=None, impute_applications=False, application_alias=True, applications=None):
        """Select frames with associated OCR results."""
        with self.get_connection() as conn:
            # Query to get frames
            query = '''SELECT 
                            frames.*, 
                            video_chunks.path as video_chunk_path
                            FROM frames LEFT JOIN video_chunks ON frames.video_chunk_id = video_chunks.id'''
            params = tuple()
            if applications:
                placeholders = ','.join(['?'] * len(applications))  # Create placeholders for the query
                query += f" WHERE frames.application IN ({placeholders})"
                params += tuple(applications)

            if frame_ids:
                placeholders = ','.join(['?'] * len(frame_ids))  # Create placeholders for the query
                query += f" WHERE frames.id IN ({placeholders})"
                params += tuple(frame_ids)
            
            # Use pandas to read the SQL query result into a DataFrame
            df = pd.read_sql_query(query, conn, params=params if len(params) > 0 else None)

            df['application_org'] = df['application'].copy()
            if impute_applications:
                df = utils.impute_applications(df)

            if application_alias:
                id_to_alias = utils.get_identifiers_to_alias()
                df['application'] = df['application'].map(id_to_alias)
                df['application'] = df['application'].fillna(df['application_org'])
            return df
        
    def get_video_chunks(self):
        with self.get_connection() as conn:
            query = '''SELECT * FROM video_chunks'''
            df = pd.read_sql(query, conn)
            return df
        
    @with_lock
    def update_video_chunk_info(self, video_chunk_id, frame_ids):
        """
        Updates the video_chunk_id and video_chunk_offset for a frame_id.
        
        Args:
            video_chunk_id (int): The video chunk ID to assign.
            frame_ids (list[int]): List of frame IDs in order of video compression.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                # Prepare the data for the executemany function
                data_to_update = [(video_chunk_id, i, frame_id) for i, frame_id in enumerate(frame_ids)]
                
                cursor.executemany('''
                    UPDATE frames
                    SET video_chunk_id = ?, video_chunk_offset = ?
                    WHERE id = ?
                ''', data_to_update)
                conn.commit()
                print(f"Updated video_chunk_id and video_chunk_offset for {len(frame_ids)} frames.")
            except sqlite3.Error as e:
                print(f"An error occurred while updating video_chunk_id and video_chunk_offset: {e}")
    
    def get_ocr_results(self, frame_id=None):
        """Gets ocr results for a single frame_id."""
        with self.get_connection() as conn:
            if frame_id is None:
                query = '''SELECT * FROM ocr_results'''
            else:
                query = f'''SELECT * FROM ocr_results WHERE frame_id = {frame_id}'''
            # Use pandas to read the SQL query result into a DataFrame
            df = pd.read_sql_query(query, conn)
            return df
        
    def get_frames_without_ocr(self):
        """Select frames that have not been linked to any OCR results."""
        with self.get_connection() as conn:
            # Query to get the frames that do not have associated OCR results
            query = '''
                SELECT f.*
                FROM frames f
                LEFT JOIN ocr_results o ON f.id = o.frame_id
                WHERE o.id IS NULL
            '''

            # Use pandas to read the SQL query result into a DataFrame
            df = pd.read_sql_query(query, conn)
            return df

    def get_frames_with_ocr(self, frame_ids=None, impute_applications=False):
        """Select frames with associated OCR results."""
        if frame_ids is not None and len(frame_ids) == 0:
            return pd.DataFrame()
        with self.get_connection() as conn:
            # Query to get the frames with OCR results
            query = '''
                SELECT DISTINCT frames.id as frame_id, frames.timestamp, frames.path, frames.application, x, y, w, h, text, conf
                FROM frames
                INNER JOIN ocr_results ON frames.id = ocr_results.frame_id
            '''
            if frame_ids:
                placeholders = ','.join(['?'] * len(frame_ids))  # Create placeholders for the query
                query += f" WHERE frames.id IN ({placeholders})"
            
            # Use pandas to read the SQL query result into a DataFrame
            df = pd.read_sql_query(query, conn, params=tuple(frame_ids) if frame_ids else None)
            if impute_applications:
                df = utils.impute_applications(df)
            return df
    
    def search(self, text=None, start_date=None, end_date=None, apps=None, n_seconds=None, impute_applications=False):
        """Search for frames with OCR results containing the specified text.
        Args:
            text (str): text to search for
            start_date (pd.datetime): search all frames after this time
            end_date (pd.datetime): search all frames before this time
            app (list | set): only include these app identifiers
            n_seconds (int): only return 1 result within a n_seconds time period
        Returns:
            pd.Dataframe containing search results
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

            if impute_applications:
                df = utils.impute_applications(df)

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
        
    def insert_query(self, query, context_start_timestamp=None, context_end_timestamp=None, context_applications=None):
        """Inserts query into queries table
        Args:
            query (str): LLM query
            context_start_timestamp (int): the earliest screenshot timestamp to use for context
            context_end_timestamp (int): the latest screenshot timestamp to use for context
            context_applications (list[str]): a list of applications to use as potential context. If None all will be used."""
        query_timestamp = int(time.time() * 1000) # UTC in milliseconds
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO queries (query, timestamp, context_start_timestamp, context_end_timestamp, context_applications)
                VALUES (?, ?, ?, ?, ?)
            ''', (query, query_timestamp, context_start_timestamp, context_end_timestamp, context_applications))
            
            # Get the last inserted frame_id
            query_id = cursor.lastrowid
            conn.commit()
            print(f"Query added successfully with query_id: {query_id}")
            return query_id
        
    def insert_query_result(self, query_id, result, source_frame_ids):
        """Inserts the result of a query into the queries table"""
        # Convert source_frame_ids from a list or set to a comma-separated string
        finished_timestamp = int(time.time() * 1000) # UTC in milliseconds
        source_frame_ids_str = ','.join(map(str, source_frame_ids))
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    UPDATE queries SET result = ?, source_frame_ids = ?, finished_timestamp = ?
                    WHERE id = ?
                ''', (result, source_frame_ids_str, finished_timestamp, query_id))
                conn.commit()
                print(f"Query result added successfully for query_id: {query_id}")
            except sqlite3.Error as e:
                print(f"An error occurred: {e}")


    def get_active_queries(self):
        """Returns all active queries. This inlcudes for completed and currently running queries."""
        with self.get_connection() as conn:
            query = f'''SELECT * FROM queries WHERE active = true'''
            df = pd.read_sql_query(query, conn)
            # Impute Query Running... for running queries
            df['result'] = df['result'].fillna("Query Running...")
            return df
        
    def get_unprocessed_queries(self):
        """Returns all queries without finished_timestamp."""
        with self.get_connection() as conn:
            query = f'''SELECT * FROM queries WHERE finished_timestamp IS NULL'''
            df = pd.read_sql_query(query, conn)
            # Replace np.nan with None
            df = df.replace({np.nan : None})
            return df
        
    @with_lock
    def update_chromadb_processed(self, frame_ids, value=True):
        """Updates the chromadb_processed status for a list of frame_ids."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Prepare the data for the executemany function
            data_to_update = [(value, frame_id) for frame_id in frame_ids]
            try:
                cursor.executemany('''
                    UPDATE frames
                    SET chromadb_processed = ?
                    WHERE id = ?
                ''', data_to_update)
                conn.commit()
                print(f"Updated chromadb_processed for {len(frame_ids)} frames.")
            except sqlite3.Error as e:
                print(f"An error occurred while updating chromadb_processed: {e}")

    def get_non_chromadb_processed_frames_with_ocr(self, frame_ids=None, impute_applications=False):
        """Select frames that have not been processed but chromadb but have associated OCR results."""
        with self.get_connection() as conn:
            # Query to get the frames with OCR results
            query = '''
                SELECT DISTINCT frames.*
                FROM frames
                INNER JOIN ocr_results ON frames.id = ocr_results.frame_id
                WHERE NOT frames.chromadb_processed
            '''
            
            # Use pandas to read the SQL query result into a DataFrame
            df = pd.read_sql_query(query, conn)
            if impute_applications:
                df = utils.impute_applications(df)
            return df
        
    def get_last_id(self, source=None, table="frames"):
        """Returns the largest id from a given source and table"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if source is not None:
                query = f"SELECT MAX(source_id) FROM {table} WHERE source = ?"
                cursor.execute(query, (source,))
            else:
                query = f"SELECT MAX(id) FROM {table}"
                cursor.execute(query)

            # Fetch the result
            max_id = cursor.fetchone()[0]
            return max_id
        
    def get_last_timestamp(self, table):
        """Returns the most recent timestamp in the table provided."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = f"SELECT MAX(timestamp) FROM {table}"
            cursor.execute(query)
            # Fetch the result
            max_timestamp = cursor.fetchone()[0]
            return max_timestamp
    
    @with_lock
    def insert_annotations(self, annotations):
        """Insert annotations into annotations table."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany('''
                INSERT INTO annotations (timestamp, text)
                VALUES (?, ?)
            ''', [(a['timestamp'], a['text']) for a in annotations])
            
            conn.commit()
            
            print(f"{len(annotations)} annotations added successfully.")

    def get_annotations(self):
        """Returns all annotations."""
        with self.get_connection() as conn:
            query = f'''SELECT * FROM annotations'''
            df = pd.read_sql_query(query, conn)
            df = df.dropna()
            return df

    @with_lock
    def insert_locations(self, locations):
        """Insert locations into locations table."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany('''
                INSERT INTO locations (latitude, longitude, timestamp)
                VALUES (?, ?, ?)
            ''', [(l['latitude'], l['longitude'], l['timestamp']) for l in locations])
            
            conn.commit()
            
            print(f"{len(locations)} locations added successfully.")

    def get_locations(self):
        """Returns all locations."""
        with self.get_connection() as conn:
            query = f'''SELECT * FROM locations'''
            df = pd.read_sql_query(query, conn)
            return df
        
    @with_lock
    def add_label(self, frame_id, label, value=None):
        """Adds a label to the labels table for a given frame."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f'''INSERT INTO labels (frame_id, label, value)
            VALUES (?, ?, ?)''', (frame_id, label, value))
            conn.commit()
            print(f"Successfully added label {label}:{value} for {frame_id}")

    @with_lock
    def get_frames_with_label(self, label, value=None):
        """Returns all frame_ids with the associated label."""
        with self.get_connection() as conn:
            query = f"""SELECT frame_id FROM labels WHERE label = '{label}'
                    AND value = '{value}'"""
            df = pd.read_sql_query(query, conn)
            return set(df['frame_id'])

    def copy_database(self, frame_ids, db_file, frames_dir_path):
        """
        Copies specific frames from the current database to a new database file, and copies associated files.
        
        Args:
            frame_ids (list[int]): List of frame IDs to copy.
            db_file (str): File path of the new database.
            frames_dir_path (str): Directory path to copy the frame files to.
        """
        frames_dir_path = os.path.abspath(frames_dir_path)

        # Establish a connection to the new database and create tables
        new_db_conn = sqlite3.connect(db_file)
        new_cursor = new_db_conn.cursor()

        # Create tables in the new database
        new_cursor.execute('''
            CREATE TABLE IF NOT EXISTS frames (
                id INTEGER PRIMARY KEY,
                timestamp INTEGER NOT NULL,
                path TEXT NOT NULL,
                application TEXT NOT NULL,
                chromadb_processed BOOLEAN NOT NULL DEFAULT false
            )
        ''')
        new_cursor.execute('''
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

        # Select frames from the current database
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, timestamp, path, application, chromadb_processed FROM frames WHERE id IN ({})
            '''.format(','.join('?' for _ in frame_ids)), tuple(frame_ids))
            
            frames = cursor.fetchall()

            # Copy frames to new database and copy files
            for frame in frames:
                frame_id, timestamp, path, application, chromadb_processed = frame
                new_path = path.replace(str(RAW_SCREENSHOTS_DIR), frames_dir_path)
                utils.make_dir(os.path.dirname(new_path))
                
                # Copy file to new location
                shutil.copy2(path, new_path)
                
                # Insert frame into new database
                new_cursor.execute('''
                    INSERT INTO frames (id, timestamp, path, application, chromadb_processed)
                    VALUES (?, ?, ?, ?, ?)
                ''', (frame_id, timestamp, new_path, application, chromadb_processed))

        # Commit changes to the new database and close connections
        new_db_conn.commit()
        new_db_conn.close()

    def convert_source_ids_to_hindsight_ids(self, table: str, source: str, source_ids: list[int]) -> list[int]:
        """
        Converts a list of source_ids to hindsight database ids in the same order.

        Args:
            table (str): The table to query (e.g., "frames" or "video_chunks").
            source_ids (list[int]): A list of source-specific IDs to look up.
            source (str): The source name associated with these IDs.

        Returns:
            list[int]: A list of corresponding Hindsight DB IDs, maintaining the order of source_ids.
        """
        if not source_ids:
            return []

        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Convert list to tuple format for SQL query
            placeholders = ','.join(['?'] * len(source_ids))
            query = f"""
                SELECT source_id, id
                FROM {table}
                WHERE source_id IN ({placeholders}) AND source = ?
            """
            
            # Execute the query and fetch results
            cursor.execute(query, (*source_ids, source))
            rows = cursor.fetchall()

            # Convert results into a dictionary {source_id: hindsight_id}
            source_to_hindsight_map = {source_id: hindsight_id for source_id, hindsight_id in rows}

            # Map input source_ids to their corresponding hindsight IDs while maintaining order
            hindsight_ids = [source_to_hindsight_map.get(sid, None) for sid in source_ids]

            return hindsight_ids
