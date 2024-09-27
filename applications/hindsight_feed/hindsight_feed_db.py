import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean, FLOAT, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

from datetime import datetime

import utils

from config import DATA_DIR

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

    def __repr__(self):
        return f"<Content(title={self.title}, url={self.url}, published_date={self.published_date}, score={self.score}, clicked={self.clicked})>"
    
class ContentGenerator(Base):
    __tablename__ = 'content_generators'
    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    gen_type = Column(String(150), nullable=True)
    description = Column(String(300), nullable=True)

# Database connection
engine = create_engine(f'sqlite:///{db_path}')
Session = scoped_session(sessionmaker(bind=engine))
session = Session()

Base.metadata.create_all(engine)

def add_content(title, url, published_date, ranking_score, content_generator_id, thumbnail_url=None):
    new_content = Content(title=title, url=url, published_date=published_date, ranking_score=ranking_score,
                          content_generator_id=content_generator_id, thumbnail_url=thumbnail_url,
                          url_is_local=utils.is_local_url(url))
    session.add(new_content)
    session.commit()

def df_add_contents(df):
    contents = []
    for _, row in df.iterrows():
        contents.append(Content(title=row['title'], url=row['url'], published_date=row['published_date'], 
                                ranking_score=row['ranking_score'], thumbnail_url=row['thumbnail_url'],
                                content_generator_id=row['content_generator_id'], url_is_local=utils.is_local_url(row['url'])))
    try:
        session.bulk_save_objects(contents)
        session.commit()
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
    
def add_content_generator(name, gen_type=None, description=None):
    existing_generator = session.query(ContentGenerator).filter_by(name=name).first()
    if existing_generator:
        return existing_generator.id

    new_content_generator = ContentGenerator(name=name, gen_type=gen_type, description=description)
    session.add(new_content_generator)
    session.commit()
    return new_content_generator.id 
