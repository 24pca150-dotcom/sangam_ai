import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.database import Poem

DATABASE_URL = "postgresql://languageuser:rF9ZJJTa7PiYz24H0TfJ5tGKz7QAubHk@dpg-d8nsgh3tqb8s73di12sg-a.singapore-postgres.render.com:5432/languageapp"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()

poem = db.query(Poem).filter(Poem.poem_number == 101).first()
if poem:
    
    import copy
    updated_basic_info = copy.deepcopy(poem.basic_information)
    
    correct_text = '''ஒருநாட் செல்லல மிருநாட் செல்லலம்
பன்னாள் பயின்று பலரொடு செல்லினும்
தலைநாட் போன்ற விருப்பினன் மாதோ;
அணிபூ ணணிந்த யானை யியறேர்
அதியமான் பரிசில் பெறூஉங் காலம்
நீட்டினும் நீட்டா தாயினும் யானைதன்
கோட்டிடை வைத்த கவளம் போலக்
கையகத் ததுவது பொய்யா காதே
அருந்தே மாந்த நெஞ்சம்
வருந்த வேண்டா வாழ்கவன் றாளே'''
    
    updated_basic_info['original_tamil_text'] = correct_text
    
    poem.basic_information = updated_basic_info
    
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(poem, "basic_information")
    
    db.commit()
    print("Update successful!")
else:
    print("Poem 101 not found.")
db.close()
