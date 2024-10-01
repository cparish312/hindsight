import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean, FLOAT, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

from datetime import datetime

import feed_utils

from feed_config import DATA_DIR

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
    published_date = Column(DateTime, nullable=False)
    ranking_score = Column(FLOAT, nullable=False)
    score = Column(Integer, nullable=True)
    clicked = Column(Boolean, default=False)
    viewed = Column(Boolean, default=False)
    url_is_local = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    last_modified_timestamp = Column(DateTime, default=datetime.utcnow)
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
            contents.append(Content(title=row['title'], url=row['url'], published_date=row['published_date'], 
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
        content.last_modified_timestamp = datetime.utcnow()
        session.commit()

def update_content_score(id, score):
    content = session.query(Content).get(id)
    if content:
        content.score = score
        content.last_modified_timestamp = datetime.utcnow()
        session.commit()

def content_viewed(id):
    content = session.query(Content).get(id)
    if content:
        content.viewed = True
        content.last_modified_timestamp = datetime.utcnow()
        session.commit()

def fetch_contents(non_viewed=False, content_generator_id=None):
    query = session.query(Content).filter(Content.title != "")
    if non_viewed:
        query = query.filter(Content.viewed == False)
    if content_generator_id:
        query = query.filter(Content.content_generator_id == content_generator_id)
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
