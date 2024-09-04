"""Code for interfacing with SQLite database."""
import os
import time
import shutil
import sqlite3
import numpy as np
import pandas as pd
from datetime import timedelta

import redis
from redis.lock import Lock

import tzlocal
from zoneinfo import ZoneInfo

from config import DATA_DIR, RAW_SCREENSHOTS_DIR
import utils

local_timezone = tzlocal.get_localzone()
video_timezone = ZoneInfo("UTC")

DB_FILE = os.path.join(DATA_DIR, "hindsight.db")

demo_apps = {'android', 'com-connor-hindsight', 'com-android-phone', 'com-android-pixeldisplayservice', 'com-android-settings',  'com-github-android', 'com-reddit-frontpage', 'com-soundcloud-android', 'com-spotify-music'}

class HindsightDB:
    def __init__(self, db_file=DB_FILE):
        self.db_file = db_file
        client = redis.Redis(host='localhost', port=6379, db=0)
        self.db_lock = Lock(client, "hindsight_db_lock") # Use Redis Lock to ensure lock across multiple instances of HindsightDB
        with self.db_lock:
            self.create_tables()
            self.create_lock_table()

    def get_connection(self):
        """Get a new connection every time for thread safety."""
        connection = sqlite3.connect(self.db_file)
        connection.execute('PRAGMA journal_mode=WAL;')
        connection.execute('PRAGMA busy_timeout = 10000;')
        return connection

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
                    UNIQUE (timestamp, path)
                )
            ''')

            # Add the 'chromadb_processed' column if it does not exist
            cursor.execute('''
                PRAGMA table_info(frames)
            ''')
            columns = [row[1] for row in cursor.fetchall()]
            if 'chromadb_processed' not in columns:
                cursor.execute('''
                    ALTER TABLE frames
                    ADD COLUMN chromadb_processed BOOLEAN NOT NULL DEFAULT false
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

            # Add the 'chromadb_processed' column if it does not exist
            cursor.execute('''
                PRAGMA table_info(ocr_results)
            ''')
            columns = [row[1] for row in cursor.fetchall()]
            if 'block_num' not in columns:
                cursor.execute('''
                    ALTER TABLE ocr_results
                    ADD COLUMN block_num INTEGER
                ''')
                cursor.execute('''
                    ALTER TABLE ocr_results
                    ADD COLUMN line_num INTEGER
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
                    active BOOLEAN NOT NULL DEFAULT true,
                    finished_timestamp INTEGER,
                    context_start_timestamp INTEGER,
                    context_end_timestamp INTEGER,
                    context_applications TEXT
                )
            ''')

            # Add the 'chromadb_processed' column if it does not exist
            # cursor.execute('''
            #     PRAGMA table_info(queries)
            # ''')
            # columns = [row[1] for row in cursor.fetchall()]
            # if 'finished_timestamp' not in columns:
            #     cursor.execute('''
            #         ALTER TABLE queries
            #         ADD COLUMN finished_timestamp INTEGER
            #     ''')

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

            # Commit the changes and close the connection
            conn.commit()

    def create_lock_table(self):
        """Table for handling db based locks."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS db_locks (
                    lock_name TEXT PRIMARY KEY,
                    is_locked INTEGER NOT NULL DEFAULT false
                )
            ''')
            # Ensure necessary locks are available in the table
            cursor.execute('''
                INSERT OR IGNORE INTO db_locks (lock_name, is_locked)
                VALUES ('db', false), ('chromadb', false)
            ''')
            conn.commit()

    def acquire_lock(self, lock_name):
        """Attempt to acquire a lock by name."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Check if the lock is currently available
            cursor.execute('''
                SELECT is_locked FROM db_locks WHERE lock_name = ?
            ''', (lock_name,))
            if cursor.fetchone()[0] == 0:
                # Lock is available, acquire it
                cursor.execute('''
                    UPDATE db_locks SET is_locked = 1 WHERE lock_name = ?
                ''', (lock_name,))
                conn.commit()
                return True
            return False
        
    def check_lock(self, lock_name):
        """Checks the value of a lock without acquiring it."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Check if the lock is currently available
            cursor.execute('''
                SELECT is_locked FROM db_locks WHERE lock_name = ?
            ''', (lock_name,))
            if cursor.fetchone()[0] == 0:
                return True
            return False

    def release_lock(self, lock_name):
        """Release a lock by name."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE db_locks SET is_locked = 0 WHERE lock_name = ?
            ''', (lock_name,))
            conn.commit()


    def insert_frame(self, timestamp, path, application):
        """Insert frame into frames table and return frame_id."""
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
        """Insert ocr results into ocr_results table."""
        with self.db_lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Insert multiple OCR results
                cursor.executemany('''
                    INSERT INTO ocr_results (frame_id, x, y, w, h, text, conf, block_num, line_num)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', [(frame_id, x, y, w, h, text, conf, block_num, line_num) for x, y, w, h, text, conf, block_num, line_num in ocr_results])
                
                conn.commit()
                
                print(f"{len(ocr_results)} OCR results added successfully.")

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
        
    def get_screenshots(self, frame_ids=None, impute_applications=True, application_alias=True):
        """Select frames with associated OCR results."""
        with self.get_connection() as conn:
            excluded_apps = ("frontCamera", "backCamera")
            # Query to get frames
            query = 'SELECT * FROM frames WHERE application NOT IN (?, ?)'
            params = excluded_apps

            # Extend the query to filter by frame_ids if provided
            if frame_ids:
                placeholders = ','.join(['?'] * len(frame_ids))
                query += f" AND id IN ({placeholders})"
                params = excluded_apps + tuple(frame_ids)
            
            # Use pandas to read the SQL query result into a DataFrame
            df = pd.read_sql_query(query, conn, params=params)
            # df = df.loc[df['application'].isin(demo_apps)]
            if impute_applications:
                df = utils.impute_applications(df)

            df['application_org'] = df['application'].copy()
            if application_alias:
                id_to_alias = utils.get_identifiers_to_alias()
                df['application'] = df['application'].map(id_to_alias)
                df['application'] = df['application'].fillna(df['application_org'])
            return df

    def get_frames(self, frame_ids=None, impute_applications=True, application_alias=True, applications=None):
        """Select frames with associated OCR results."""
        with self.get_connection() as conn:
            # Query to get frames
            query = '''SELECT * FROM frames'''
            params = tuple()
            if applications:
                placeholders = ','.join(['?'] * len(applications))  # Create placeholders for the query
                query += f" WHERE application IN ({placeholders})"
                params += tuple(applications)

            if frame_ids:
                placeholders = ','.join(['?'] * len(frame_ids))  # Create placeholders for the query
                query += f" WHERE id IN ({placeholders})"
                params += tuple(frame_ids)
            
            # Use pandas to read the SQL query result into a DataFrame
            df = pd.read_sql_query(query, conn, params=params if len(params) > 0 else None)
            # df = df.loc[df['application'].isin(demo_apps)]
            if impute_applications:
                df = utils.impute_applications(df)

            df['application_org'] = df['application'].copy()
            if application_alias:
                id_to_alias = utils.get_identifiers_to_alias()
                df['application'] = df['application'].map(id_to_alias)
                df['application'] = df['application'].fillna(df['application_org'])
            return df
    
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

    def get_frames_with_ocr(self, frame_ids=None, impute_applications=True):
        """Select frames with associated OCR results."""
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
    
    def search(self, text=None, start_date=None, end_date=None, apps=None, n_seconds=None, impute_applications=True):
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
        
    def insert_query(self, query, context_start_timestamp=None, context_end_timestamp=None, context_applications=None):
        """Inserts query into queries table"""
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
        """Returns all active queries"""
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
        
    def update_chromadb_processed(self, frame_ids, value=True):
        """Updates the chromadb_processed status for a list of frame_ids."""
        with self.db_lock:  # Ensure thread-safety
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

    def get_non_chromadb_processed_frames_with_ocr(self, frame_ids=None, impute_applications=True):
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
        
    def get_last_timestamp(self, table):
        """Returns the most recent timestamp in the table provided."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = f"SELECT MAX(timestamp) FROM {table}"
            cursor.execute(query)
            # Fetch the result
            max_timestamp = cursor.fetchone()[0]
            return max_timestamp
        
    def insert_annotations(self, annotations):
        """Insert annotations into annotations table."""
        with self.db_lock:
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

    def insert_locations(self, locations):
        """Insert locations into locations table."""
        with self.db_lock:
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
        
    def add_label(self, frame_id, label, value=None):
        with self.db_lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f'''INSERT INTO labels (frame_id, label, value)
                VALUES (?, ?, ?)''', (frame_id, label, value))
                conn.commit()
                print(f"Successfully added label {label}:{value} for {frame_id}")

    def get_frames_with_label(self, label, value=None):
        with self.db_lock:
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
            
            # # Also handle copying OCR results if necessary
            # ocr_ids = [frame[0] for frame in frames]
            # cursor.execute('''
            #     SELECT * FROM ocr_results WHERE frame_id IN ({})
            # '''.format(','.join('?' for _ in ocr_ids)), ocr_ids)
            # ocr_results = cursor.fetchall()

            # for ocr_result in ocr_results:
            #     new_cursor.execute('''
            #         INSERT INTO ocr_results (frame_id, x, y, w, h, text, conf)
            #         VALUES (?, ?, ?, ?, ?, ?, ?)
            #     ''', ocr_result)

        # Commit changes to the new database and close connections
        new_db_conn.commit()
        new_db_conn.close()
