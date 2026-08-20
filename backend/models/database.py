from sqlalchemy import create_engine, Column, Integer, String, Text, JSON
from sqlalchemy.orm import sessionmaker, declarative_base
import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    if DATABASE_URL.startswith("postgresql"):
        engine = create_engine(DATABASE_URL, connect_args={"sslmode": "require"})
    else:
        engine = create_engine(DATABASE_URL)
else:
    DB_DIR = os.path.join(os.path.dirname(__file__), '../../data')
    os.makedirs(DB_DIR, exist_ok=True)
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(DB_DIR, 'sangam_final.db')}"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Poem(Base):
    __tablename__ = "comprehensive_poems"

    id = Column(Integer, primary_key=True, index=True)
    poem_title = Column(String, unique=True, index=True)
    poem_number = Column(Integer, index=True)
    anthology_name = Column(String, index=True)
    poet_name = Column(String, index=True)
    
    # Core JSON objects
    basic_information = Column(JSON)
    historical_information = Column(JSON)
    meaning_interpretation = Column(JSON)
    
    # Extended JSON objects
    literary_classification = Column(JSON, nullable=True)
    literary_analysis = Column(JSON, nullable=True)
    language_analysis = Column(JSON, nullable=True)
    grammar_analysis = Column(JSON, nullable=True)
    detailed_glossary = Column(JSON, nullable=True)
    line_by_line_meaning = Column(JSON, nullable=True)
    keywords = Column(JSON, nullable=True)
    named_entities = Column(JSON, nullable=True)
    poem_structure = Column(JSON, nullable=True)
    references = Column(JSON, nullable=True)

class PoemQA(Base):
    __tablename__ = "poem_qa"

    id = Column(Integer, primary_key=True, index=True)
    poem_id = Column(Integer, index=True) # ID referencing the Poem, or just a generic ID
    original_id = Column(Integer) # The 'id' field from the JSON
    type = Column(String, index=True) # 'factual', 'multi_hop', etc.
    question = Column(String, index=True)
    answer = Column(Text)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
