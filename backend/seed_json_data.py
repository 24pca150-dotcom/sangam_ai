import os
import sys
import json
import argparse
sys.stdout.reconfigure(encoding='utf-8')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.database import get_db, Poem, PoemQA, engine, Base
from vector_db.qdrant_db import add_to_vector_db, add_qa_to_vector_db, get_qdrant_client, COLLECTION_NAME

def reset_all_databases():
    print("Resetting SQL Database (Poem & PoemQA tables)...")
    db = next(get_db())
    try:
        db.query(PoemQA).delete()
        db.query(Poem).delete()
        db.commit()
        print("SQL Database tables cleared successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error resetting SQL Database: {e}")
    finally:
        db.close()

    print("Resetting Qdrant Vector DB Collection...")
    client = get_qdrant_client()
    try:
        if client.collection_exists(COLLECTION_NAME):
            client.delete_collection(COLLECTION_NAME)
            print(f"Qdrant collection '{COLLECTION_NAME}' deleted.")
        get_qdrant_client() # Re-creates empty collection
        print("Qdrant Vector DB re-initialized successfully.")
    except Exception as e:
        print(f"Error resetting Qdrant Vector DB: {e}")

def ingest_poems_json(file_path: str):
    if not os.path.exists(file_path):
        print(f"Error: Poems file '{file_path}' not found.")
        return

    print(f"Reading poems JSON from '{file_path}'...")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if not isinstance(data, list):
        data = [data]

    db = next(get_db())
    added_poems = []
    
    for item in data:
        basic = item.get('basic_information', {})
        title = basic.get('poem_title') or item.get('poem_title', 'Unknown')
        number = basic.get('poem_number') or item.get('poem_number', 0)
        anthology = basic.get('anthology_name') or item.get('anthology_name', '')
        poet = basic.get('poet_name') or item.get('poet_name', '')

        # Check existing
        existing = db.query(Poem).filter(Poem.poem_title == title).first()
        if not existing:
            db_poem = Poem(
                poem_title=title,
                poem_number=number,
                anthology_name=anthology,
                poet_name=poet,
                basic_information=basic,
                historical_information=item.get('historical_information', {}),
                meaning_interpretation=item.get('meaning_interpretation', {}),
                literary_classification=item.get('literary_classification'),
                literary_analysis=item.get('literary_analysis'),
                language_analysis=item.get('language_analysis'),
                grammar_analysis=item.get('grammar_analysis'),
                detailed_glossary=item.get('detailed_glossary'),
                line_by_line_meaning=item.get('line_by_line_meaning'),
                keywords=item.get('keywords'),
                named_entities=item.get('named_entities'),
                poem_structure=item.get('poem_structure'),
                references=item.get('references')
            )
            db.add(db_poem)
            added_poems.append(db_poem)

    db.commit()
    print(f"Saved {len(added_poems)} poems into SQL Database.")

    if added_poems:
        print("Generating Qdrant Vector DB embeddings with clean split_line Tamil text...")
        add_to_vector_db(added_poems)
        print("Vector DB ingestion completed successfully.")

    db.close()

def ingest_qa_json(file_path: str):
    if not os.path.exists(file_path):
        print(f"Error: QA JSON file '{file_path}' not found.")
        return

    print(f"Reading QA JSON from '{file_path}'...")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if not isinstance(data, list):
        data = [data]

    db = next(get_db())
    added_qas = []
    
    for item in data:
        orig_id = item.get('id', 0)
        q_text = item.get('question', '')
        a_text = item.get('answer', '')
        qa_type = item.get('type', 'factual')
        poem_id = item.get('poem_id')

        existing = db.query(PoemQA).filter(PoemQA.original_id == orig_id, PoemQA.question == q_text).first()
        if not existing:
            db_qa = PoemQA(
                original_id=orig_id,
                poem_id=poem_id,
                type=qa_type,
                question=q_text,
                answer=a_text
            )
            db.add(db_qa)
            added_qas.append(db_qa)

    db.commit()
    print(f"Saved {len(added_qas)} QA pairs into SQL Database.")
    db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Master Seeding & Data Ingestion Tool for Sangam AI")
    parser.add_argument("--clear", action="store_true", help="Wipe SQL Database and Qdrant Vector DB")
    parser.add_argument("--poems", type=str, help="Path to poems JSON file to ingest")
    parser.add_argument("--qa", type=str, help="Path to QA pairs JSON file to ingest")
    
    args = parser.parse_args()

    if args.clear:
        reset_all_databases()

    if args.poems:
        ingest_poems_json(args.poems)

    if args.qa:
        ingest_qa_json(args.qa)

    if not args.clear and not args.poems and not args.qa:
        print("Master Data Ingestion Tool:")
        print("Usage:")
        print("  python seed_json_data.py --clear                   (Wipe databases fresh)")
        print("  python seed_json_data.py --poems path/to/poems.json (Ingest poems JSON)")
        print("  python seed_json_data.py --qa path/to/qa.json       (Ingest QA pairs JSON)")
        print("  python seed_json_data.py --clear --poems path/to/poems.json --qa path/to/qa.json")
