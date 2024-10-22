from sqlalchemy import create_engine, MetaData, Table, text
from sqlalchemy.exc import SQLAlchemyError

# Define your database URL
DATABASE_URL = 'sqlite:////Users/connorparish/code/hindsight/hindsight_applications/hindsight_feed/data/hindsight_feed.db'  # Update this line with your database URL

# Create an engine and bind metadata
engine = create_engine(DATABASE_URL)
metadata = MetaData()

# Reflect existing tables
metadata.reflect(engine)

# Access the 'content' table
content_table = Table('content', metadata, autoload_with=engine)

# Check if 'summary' column exists
if 'topic_label' not in content_table.c:
    # Construct the ALTER TABLE statement
    alter_statement = text('ALTER TABLE content ADD COLUMN topic_label VARCHAR(150)')

    # Execute the statement
    try:
        with engine.connect() as connection:
            connection.execute(alter_statement)
        print('Column "topic_label" added successfully.')
    except SQLAlchemyError as e:
        print(f'An error occurred: {e}')

    # Verify the addition
    metadata.reflect(engine)
    content_table = Table('content', metadata, autoload_with=engine)

    if 'topic_label' in content_table.c:
        print('Verification successful: "topic_label" column exists.')
    else:
        print('Verification failed: "topic_label" column does not exist.')
else:
    print('Column "topic_label" already exists.')
