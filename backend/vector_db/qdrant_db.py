from langchain_qdrant import QdrantVectorStore
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
import os
from dotenv import load_dotenv

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
HF_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")

# Initialize Embedding Model using HuggingFace Inference API
embeddings = HuggingFaceEndpointEmbeddings(
    huggingfacehub_api_token=HF_TOKEN,
    model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

COLLECTION_NAME = "sangam_detailed_poems"

_client = None
_vector_store = None

def get_qdrant_client():
    global _client
    if _client is not None:
        return _client
    
    if QDRANT_URL and QDRANT_API_KEY:
        try:
            remote_client = QdrantClient(
                url=QDRANT_URL,
                api_key=QDRANT_API_KEY,
                timeout=10.0
            )
            if not remote_client.collection_exists(COLLECTION_NAME):
                remote_client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
                )
            _client = remote_client
            return _client
        except Exception as e:
            print(f"Warning: Cloud Qdrant unavailable ({e}). Using local Qdrant database.")

    LOCAL_QDRANT_DIR = os.path.join(os.path.dirname(__file__), '../../data/qdrant_local')
    os.makedirs(LOCAL_QDRANT_DIR, exist_ok=True)
    _client = QdrantClient(path=LOCAL_QDRANT_DIR)
    if not _client.collection_exists(COLLECTION_NAME):
        _client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )
    return _client

def get_vector_store():
    global _vector_store
    if _vector_store is not None:
        return _vector_store
    
    client_instance = get_qdrant_client()
    _vector_store = QdrantVectorStore(
        client=client_instance,
        collection_name=COLLECTION_NAME,
        embedding=embeddings,
    )
    return _vector_store

class VectorStoreProxy:
    def __getattr__(self, name):
        return getattr(get_vector_store(), name)

vector_store = VectorStoreProxy()

# Create a text splitter to handle large token sizes safely
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len
)

def _g(obj, attr, default=""):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)

def add_to_vector_db(poems_data):
    all_chunks = []
    all_metadatas = []
    
    for poem in poems_data:
        basic = getattr(poem, 'basic_information', {})
        histo = getattr(poem, 'historical_information', {})
        mean = getattr(poem, 'meaning_interpretation', {})
        
        poem_title = _g(basic, 'poem_title', getattr(poem, 'poem_title', 'Unknown'))
        anthology_name = _g(basic, 'anthology_name', getattr(poem, 'anthology_name', ''))
        poet_name = _g(basic, 'poet_name', getattr(poem, 'poet_name', ''))
        poet_gender = _g(basic, 'poet_gender', '')
        original_tamil_text = _g(basic, 'original_tamil_text', '')
        
        # Build clean, readable Tamil poem text from line_by_line_meaning split_line if available
        clean_poem_lines = []
        line_by_line = getattr(poem, 'line_by_line_meaning', None)
        if line_by_line and isinstance(line_by_line, list):
            for item in line_by_line:
                if isinstance(item, dict) and 'split_line' in item:
                    clean_poem_lines.append(item['split_line'].strip())
        
        readable_tamil_text = "\n".join(clean_poem_lines) if clean_poem_lines else original_tamil_text

        # Build dynamic fields based on what's available
        extra_info = ""
        struct = getattr(poem, 'poem_structure', None)
        if struct:
            extra_info += f"\n        Poem Structure (Thinai, Thurai, etc): {struct}"
        keywords = getattr(poem, 'keywords', None)
        if keywords:
            extra_info += f"\n        Keywords: {', '.join(keywords) if isinstance(keywords, list) else keywords}"
        entities = getattr(poem, 'named_entities', None)
        if entities:
            extra_info += f"\n        Named Entities: {entities}"
        refs = getattr(poem, 'references', None)
        if refs:
            extra_info += f"\n        References: {refs}"

        # Create a highly detailed text representation for embeddings
        text_content = f"""
        Poem Title: {poem_title}
        Anthology: {anthology_name}
        Poet: {poet_name} ({poet_gender})
        Readable Tamil Poem Text:
        {readable_tamil_text}
        
        Original Sandhi Text: {original_tamil_text}

        
        Historical Context: {_g(histo, 'historical_context')}
        Time Period: {_g(histo, 'time_period')}
        Dynasty: {_g(histo, 'dynasty')}
        King Mentioned: {_g(histo, 'king_mentioned')}
        Place Mentioned: {_g(histo, 'place_mentioned')}
        Social Background: {_g(histo, 'social_background')}
        
        Simple Meaning: {_g(mean, 'simple_tamil_meaning')}
        Detailed Explanation: {_g(mean, 'detailed_tamil_explanation')}
        English Translation: {_g(mean, 'english_translation')}
        Summary: {_g(mean, 'summary')}
        Core Message: {_g(mean, 'core_message')}
        Thematic Tags: {', '.join(_g(mean, 'thematic_tags', [])) if isinstance(_g(mean, 'thematic_tags'), list) else _g(mean, 'thematic_tags')}
        {extra_info}
        """
        
        # Split the large text into chunks so we don't hit token limits
        chunks = text_splitter.split_text(text_content)
        
        # Attach the exact same metadata to EVERY chunk of this poem
        for chunk in chunks:
            all_chunks.append(chunk)
            all_metadatas.append({
                "poem_title": poem_title, 
                "anthology": anthology_name, 
                "poet": poet_name
            })
        
    vector_store.add_texts(texts=all_chunks, metadatas=all_metadatas)
    return True

def search_vector_db(query, k=3):
    results = vector_store.similarity_search(query, k=k)
    return results

def search_vector_db_with_scores(query, k=3):
    return vector_store.similarity_search_with_score(query, k=k)

def add_qa_to_vector_db(qa_pairs, poem_title: str):
    all_chunks = []
    all_metadatas = []
    
    for qa in qa_pairs:
        # A clear, isolated chunk for the Q&A pair so the LLM understands it
        text_content = f"Static QA Pair:\nQuestion: {qa.question}\nAnswer: {qa.answer}"
        all_chunks.append(text_content)
        all_metadatas.append({
            "poem_title": poem_title,
            "type": "qa_pair",
            "qa_id": qa.original_id,
            "qa_type": qa.type
        })
        
    if all_chunks:
        vector_store.add_texts(texts=all_chunks, metadatas=all_metadatas)
        return True
    return False
