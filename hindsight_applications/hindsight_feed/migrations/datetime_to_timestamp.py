from sqlalchemy import MetaData, Table, Integer, Column, String, Float, Boolean, JSON, text
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Define the database connection
engine = create_engine(f'sqlite:////Users/connorparish/code/hindsight/applications/hindsight_feed/data/hindsight_feed.db')
Session = sessionmaker(bind=engine)
session = Session()

metadata = MetaData()

# Define the original and new tables
old_content_table = Table('content', metadata, autoload_with=engine)
new_content_table = Table(
    'new_content', metadata,
    Column('id', Integer, primary_key=True),
    Column('content_generator_id', Integer, nullable=False),
    Column('title', String(150), nullable=False),
    Column('url', String(300), nullable=False),
    Column('thumbnail_url', String(300), nullable=True),
    Column('published_date', Integer, nullable=False),  # Unix timestamp
    Column('ranking_score', Float, nullable=False),
    Column('score', Integer, nullable=True),
    Column('clicked', Boolean, default=False),
    Column('viewed', Boolean, default=False),
    Column('url_is_local', Boolean, default=False),
    Column('timestamp', Integer, default=lambda: int(datetime.utcnow().timestamp())),  # Unix timestamp
    Column('last_modified_timestamp', Integer, default=lambda: int(datetime.utcnow().timestamp())),  # Unix timestamp
    Column('content_generator_specific_data', JSON, nullable=True)
)

def migrate_to_new_schema():
    conn = engine.connect()
    
    try:
        # Create the new table
        new_content_table.create(engine)

        # Migrate the data from the old table to the new table
        old_data = conn.execute(old_content_table.select())

        # Iterate through old data and convert datetime fields to Unix timestamps
        for row in old_data:
            row_data = row._mapping
            new_row = {
                'id': row_data['id'],
                'content_generator_id': row_data['content_generator_id'],
                'title': row_data['title'],
                'url': row_data['url'],
                'thumbnail_url': row_data['thumbnail_url'],
                'published_date': int(row_data['published_date'].timestamp()) if row_data['published_date'] else None,
                'ranking_score': row_data['ranking_score'],
                'score': row_data['score'],
                'clicked': row_data['clicked'],
                'viewed': row_data['viewed'],
                'url_is_local': row_data['url_is_local'],
                'timestamp': int(row_data['timestamp'].timestamp()) if row_data['timestamp'] else None,
                'last_modified_timestamp': int(row_data['last_modified_timestamp'].timestamp()) if row_data['last_modified_timestamp'] else None,
                'content_generator_specific_data': row_data['content_generator_specific_data']
            }

            # Insert the transformed data into the new table
            conn.execute(new_content_table.insert().values(new_row))

        # Commit the changes
        conn.commit()

        content_exists = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='content'")).fetchone()
        if content_exists:
            print("Dropping the old 'content' table.")
            conn.execute(text('DROP TABLE content'))

        # Rename the new table to the original name
        conn.execute(text('ALTER TABLE new_content RENAME TO content'))
        print("Migration complete.")
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()  # Ensure the connection is closed

if __name__ == "__main__":
    migrate_to_new_schema()