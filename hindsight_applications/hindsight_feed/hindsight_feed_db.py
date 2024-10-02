import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean, FLOAT, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

import time
from datetime import datetime, timezone

import hindsight_applications.hindsight_feed.feed_utils as feed_utils

from hindsight_applications.hindsight_feed.feed_config import DATA_DIR

Base = declarative_base()

base_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(DATA_DIR, 'hindsight_feed.db')

class Content(Base):
    __tablename__ = 'content'
    id = Column(Integer, primary_key=True)
    content_generator_id = Column(Integer, nullable=False)
    title = Column(String(150), nullable=False)
    url = Column(String(300), nullable=False)
    thumbnail_url = Column(String(300), nullable=True)
    published_date = Column(Integer, nullable=False) 
    ranking_score = Column(FLOAT, nullable=False)
    score = Column(Integer, nullable=True)
    clicked = Column(Boolean, default=False)
    viewed = Column(Boolean, default=False)
    url_is_local = Column(Boolean, default=False)
    timestamp = Column(Integer, default=lambda: int(time.time() * 1000))  
    last_modified_timestamp = Column(Integer, default=lambda: int(time.time() * 1000))
    content_generator_specific_data = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<Content(title={self.title}, url={self.url}, published_date={self.published_date}, score={self.score}, clicked={self.clicked})>"
    
class ContentGenerator(Base):
    __tablename__ = 'content_generators'
    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    gen_type = Column(String(150), nullable=True)
    description = Column(String(300), nullable=True)
    parameters = Column(JSON, nullable=True) 

# Database connection
engine = create_engine(f'sqlite:///{db_path}')
Session = scoped_session(sessionmaker(bind=engine))
session = Session

Base.metadata.create_all(engine)

def add_content(title, url, published_date, ranking_score, content_generator_id, thumbnail_url=None, content_generator_specific_data=None):
    if isinstance(published_date, datetime):
        published_date = feed_utils.datetime_to_utc_timestamp(published_date)

    existing_content = session.query(Content).filter_by(url=url).first()
    if existing_content is None:
        new_content = Content(title=title, url=url, published_date=published_date, ranking_score=ranking_score,
                            content_generator_id=content_generator_id, thumbnail_url=thumbnail_url,
                            url_is_local=feed_utils.is_local_url(url), content_generator_specific_data=content_generator_specific_data)
        session.add(new_content)
        session.commit()
    else:
        print(f"Content with URL '{url}' already exists in the database.")

def df_add_contents(df):
    contents = []
    if "content_generator_specific_data" not in df.columns:
        df["content_generator_specific_data"] = None

    for _, row in df.iterrows():
        existing_content = session.query(Content).filter_by(url=row['url']).first()
        if existing_content is None:
            published_date = row["published_date"]
            if isinstance(published_date, datetime):
                published_date = feed_utils.datetime_to_utc_timestamp(published_date)

            contents.append(Content(title=row['title'], url=row['url'], published_date=published_date, 
                                    ranking_score=row['ranking_score'], thumbnail_url=row['thumbnail_url'],
                                    content_generator_id=row['content_generator_id'], url_is_local=feed_utils.is_local_url(row['url']),
                                    content_generator_specific_data=row["content_generator_specific_data"]))
        else:
            print(f"Content with URL '{row['url']}' already exists in the database and will not be added.")
    try:
        if contents:
            session.bulk_save_objects(contents)
            session.commit()
        else:
            print("No new contents to add.")
    except Exception as e:
        print(f"Failed to add contents: {e}")
        session.rollback()

def content_clicked(id):
    content = session.query(Content).get(id)
    if content:
        content.clicked = True
        content.viewed = True
        content.last_modified_timestamp = int(time.time() * 1000)
        session.commit()

def update_content_score(id, score):
    content = session.query(Content).get(id)
    if content:
        content.score = score
        content.last_modified_timestamp = int(time.time() * 1000)
        session.commit()

def content_viewed(id):
    content = session.query(Content).get(id)
    if content:
        content.viewed = True
        content.last_modified_timestamp = int(time.time() * 1000)
        session.commit()

def fetch_contents(non_viewed=False, content_generator_id=None, last_content_id=None):
    query = session.query(Content).filter(Content.title != "")
    if non_viewed:
        query = query.filter(Content.viewed == False)
    if content_generator_id:
        query = query.filter(Content.content_generator_id == content_generator_id)
    if last_content_id:
        query = query.filter(Content.id > last_content_id)
    contents =  query.all()
    return contents
    
def add_content_generator(name, gen_type=None, description=None, parameters=None):
    existing_generator = session.query(ContentGenerator).filter_by(name=name).first()
    if existing_generator:
        return existing_generator.id

    new_content_generator = ContentGenerator(name=name, gen_type=gen_type, description=description, parameters=parameters)
    session.add(new_content_generator)
    session.commit()
    return new_content_generator.id 

def fetch_content_generators():
    query = session.query(ContentGenerator)
    contents =  query.all()
    return contents

def from_app_update_content(content_sync_list):
    try:
        for content_sync in content_sync_list:
            # Get the content record by its ID
            content = session.query(Content).get(content_sync['id'])

            if content:
                # Handle last_modified_timestamp: take the most recent one
                if 'last_modified_timestamp' in content_sync:
                    # Update if the incoming timestamp is more recent
                    if content_sync['last_modified_timestamp'] > content.last_modified_timestamp:
                        content.last_modified_timestamp = content_sync['last_modified_timestamp']

                        # Update to newer score if exists
                        if 'score' in content_sync and content_sync['score'] is not None:
                            content.score = content_sync['score']
                        
                # Handle clicked: keep true if it was already true or the incoming update sets it to true
                if 'clicked' in content_sync:
                    content.clicked = content.clicked or content_sync['clicked']

                # Handle viewed: same logic as clicked, keep true if it was already true or the incoming update sets it to true
                if 'viewed' in content_sync:
                    content.viewed = content.viewed or content_sync['viewed']

                # Commit the changes to the database
                session.commit()
            else:
                print(f"Content with ID {content_sync['id']} not found in the database.")

    except Exception as e:
        print(f"Failed to update content from app: {e}")
        session.rollback()

def fetch_newly_viewed_content(since_timestamp):
    """Get all content viewed since the provided timestamp"""
    query = session.query(Content).filter(Content.title != "")
    query = query.filter(Content.last_modified_timestamp > since_timestamp)
    query = query.filter(Content.viewed)
    contents =  query.all()
    return contents