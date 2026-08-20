import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from models.database import get_db, Poem

from vector_db.qdrant_db import add_to_vector_db, get_qdrant_client, COLLECTION_NAME
from qdrant_client.http import models as rest_models

db = next(get_db())

poem101 = db.query(Poem).filter(Poem.poem_number == 101).first()
if poem101:
    title = poem101.basic_information.get('poem_title', '')
    print(f"Found Poem 101: {title}")
    
    # 1. Delete existing vectors for Poem 101 from Qdrant if possible
    client = get_qdrant_client()
    try:
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=rest_models.FilterSelector(
                filter=rest_models.Filter(
                    must=[
                        rest_models.FieldCondition(
                            key="metadata.poem_title",
                            match=rest_models.MatchValue(value=value if 'value' in locals() else title)
                        )
                    ]
                )
            )
        )
        print("Old Qdrant chunks for Poem 101 deleted.")
    except Exception as e:
        print(f"Notice on deletion: {e}")

    # 2. Add updated Poem 101 to Qdrant Vector DB
    success = add_to_vector_db([poem101])
    if success:
        print("Successfully re-ingested clean Poem 101 into Qdrant Vector DB!")
else:
    print("Poem 101 not found in database.")

db.close()
