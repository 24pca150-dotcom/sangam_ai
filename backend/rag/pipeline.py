from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from vector_db.qdrant_db import vector_store
import os
import json
import re
from dotenv import load_dotenv

load_dotenv()

# Initialize Groq LLM
llm = ChatGroq(
    temperature=0.4,
    model_name="qwen/qwen3.8-27b", 
    api_key=os.getenv("GROQ_API_KEY", "dummy_key_change_me")
)

prompt_template = """
You are an expert Sangam Tamil Literature AI assistant specializing in Purananuru (புறநானூறு).
Your task is to understand user questions (asked in Tamil, English, or Tanglish) and provide clear, accurate, and elegant answers in natural Tamil based on the provided Context.

GUIDELINES:
1. The user may ask questions in Tamil (e.g., 'புறநானூறு 101 பாடல் விளக்கம்'), English (e.g., '101 song meaning', 'line 4 meaning of poem 101', '101 song in 4 line meaning'), or Tanglish (e.g., '101 song oda meaning enna').
2. Always answer in natural, respectful, and scholarly Tamil.
3. If the user asks about a specific line (e.g., '4th line', '4 line meaning', 'வரி 4'), identify that line from the poem or line-by-line meaning in the Context and explain its meaning clearly.
4. If the user asks for a summary or general meaning, provide a clear explanation synthesizing the poem's simple meaning, detailed explanation, and historical context.
5. Base your answers on the provided Context (Poem text, line-by-line meaning, historical background, simple & detailed explanations, and QA pairs).
6. ONLY if the provided Context is completely empty or completely irrelevant to the asked poem/topic, respond with:
   {{"answer": "மன்னித்துக்கொள்ளுங்கள், இந்த கேள்விக்கான தகவல்கள் நமது தரவுத்தளத்தில் பதிவேற்றப்படவில்லை."}}
7. YOU MUST RETURN YOUR RESPONSE AS A VALID JSON OBJECT with exactly one key: "answer".

Output Format:
```json
{{
  "answer": "உங்களுடைய தெளிவான தமிழ் பதில்..."
}}
```

Chat History:
{chat_history}

Context:
{context}

Question:
{input}

Answer:
"""
prompt = PromptTemplate.from_template(prompt_template)

chain = prompt | llm

def clean_answer_text(text: str) -> str:
    if not text:
        return text
    
    # Remove thinking tags if present
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    
    # Remove markdown formatting if present
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    
    trimmed = text.strip()
    if '"answer"' in trimmed:
        try:
            parsed = json.loads(trimmed)
            if isinstance(parsed, dict) and "answer" in parsed:
                return str(parsed["answer"]).strip()
        except Exception:
            pass
            
        # Robust regex fallback that handles quotes inside answer text
        match = re.search(r'"answer"\s*:\s*"(.*)"', trimmed, re.DOTALL)
        if match:
            extracted = match.group(1).strip()
            if extracted.endswith('"}') or extracted.endswith('"'):
                extracted = re.sub(r'"\}?$', '', extracted).strip()
            if len(extracted) > 2:
                return extracted

    # If raw context dump leaked, truncate before Static QA Pair dump
    if "Static QA Pair:" in text:
        text = text.split("Static QA Pair:")[0]
        
    # Strip internal debug prefixes
    text = re.sub(r'^Detailed Explanation:\s*', '', text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r'^Explanation:\s*', '', text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r'^Context:\s*', '', text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r'^Question:\s*', '', text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r'^Answer:\s*', '', text, flags=re.IGNORECASE | re.MULTILINE)
    
    return text.strip()



def generate_answer(question: str, chat_history: list = None):
    if chat_history is None:
        chat_history = []
        
    # Format chat history to a string
    history_str = ""
    for msg in chat_history:
        history_str += f"{msg.role.capitalize()}: {msg.content}\n"
    
    # 1. Hybrid Search: Check PostgreSQL for structured poem data if a poem number is mentioned
    numbers = [int(n) for n in re.findall(r'\b\d+\b', question)]
    poem_numbers = [n for n in numbers if 1 <= n <= 400]
    
    db_context = ""
    db_poem = None
    target_poem_title = None
    
    try:
        from models.database import SessionLocal, Poem
        with SessionLocal() as db_session:
            for num in poem_numbers:
                p = db_session.query(Poem).filter(Poem.poem_number == num).first()
                if p:
                    db_poem = p
                    target_poem_title = p.poem_title
                    basic = p.basic_information or {}
                    mean = p.meaning_interpretation or {}
                    histo = p.historical_information or {}
                    lines = p.line_by_line_meaning or []
                    
                    lines_text = ""
                    if lines and isinstance(lines, list):
                        for idx, item in enumerate(lines, 1):
                            if isinstance(item, dict):
                                split_l = item.get('split_line', '')
                                l_mean = item.get('meaning', '')
                                lines_text += f"\nவரி {idx}: {split_l} -> பொருள்: {l_mean}"
                    
                    db_context = f"""
=== அதிகாரப்பூர்வ புறநானூறு தரவுத்தள தகவல் ===
பாடல் தலைப்பு: {p.poem_title}
பாடல் எண்: {p.poem_number}
நூல்: {p.anthology_name}
புலவர்: {p.poet_name}
அரசர்: {histo.get('king_mentioned', '')}

அசல் பாடல் வரிகள்:
{basic.get('original_tamil_text', '')}

ஒவ்வொரு வரிக்கான பொருள் (Line by Line Meaning):
{lines_text}

எளிய விளக்கம்:
{mean.get('simple_tamil_meaning', '')}

விரிவான விளக்கம்:
{mean.get('detailed_tamil_explanation', '')}

வரலாற்று பின்னணி:
{histo.get('historical_context', '')}
==========================================
"""
                    break
    except Exception as db_err:
        print(f"Hybrid DB lookup note: {db_err}")

    # 2. Vector Semantic Search
    search_query = re.sub(r'\b(summary|solu|pathi|tell|about|details)\b', '', question, flags=re.IGNORECASE).strip()
    if not search_query or len(search_query.strip().split()) <= 1:
        search_query = question

    if len(question.strip().split()) <= 2 and not re.search(r'\d+', question):
        search_query = f"{question} என்பதன் பொருள் என்ன?"
        
    docs = vector_store.similarity_search(search_query, k=4)
    
    # Validation: If a specific poem number was asked but not found in DB or docs
    if poem_numbers and not db_poem:
        found_in_docs = False
        for num in poem_numbers:
            for doc in docs:
                doc_title = str(doc.metadata.get('poem_title', ''))
                if str(num) in doc_title or str(num) in doc.page_content:
                    found_in_docs = True
                    break
            if found_in_docs:
                break
        
        if not found_in_docs:
            req_num_str = poem_numbers[0]
            return {
                "answer": f"மன்னித்துக்கொள்ளுங்கள், புறநானூறு {req_num_str} பற்றிய தகவல்கள் நமது தரவுத்தளத்தில் பதிவேற்றப்படவில்லை.",
                "context_sources": [],
                "top_poem_title": None
            }

    # Combine DB context and Vector search chunks
    vector_context = "\n\n".join([doc.page_content for doc in docs])
    combined_context = f"{db_context}\n\n{vector_context}".strip()
    
    # 3. Invoke LLM
    content = ""
    try:
        response = chain.invoke({"context": combined_context, "chat_history": history_str, "input": question})
        content = response.content
    except Exception as llm_err:
        print(f"LLM Invoke error: {llm_err}")
        if combined_context:
            content = combined_context
        else:
            content = "மன்னித்துக்கொள்ளுங்கள், இந்த கேள்விக்கான தகவல் தரவுத்தளத்தில் கண்டறியப்படவில்லை."
    
    # 4. Parse JSON from response
    answer_text = content
    try:
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = content
            
        parsed_json = json.loads(json_str)
        if isinstance(parsed_json, dict) and "answer" in parsed_json:
            answer_text = parsed_json["answer"]
    except Exception as e:
        print(f"Failed to parse JSON response: {e}")
        answer_text = content
    
    clean_answer = clean_answer_text(answer_text)
    if not clean_answer or len(clean_answer.strip()) < 5:
        clean_answer = "மன்னித்துக்கொள்ளுங்கள், புறநானூறு தரவுத்தளத்தில் உங்கள் கேள்விக்கான தகவலைத் தேடுவதில் ஒரு சிறிய சிக்கல் ஏற்பட்டது. தயவுசெய்து மீண்டும் கேட்கவும்."
    
    sources = []
    if target_poem_title:
        sources.append(target_poem_title)
    for doc in docs:
        title = doc.metadata.get('poem_title') or 'புறநானூறு'
        poet = doc.metadata.get('poet')
        if poet and poet != 'Unknown' and poet.strip():
            sources.append(f"{title} ({poet})")
        else:
            sources.append(f"{title}")
    unique_sources = list(dict.fromkeys(sources))
    top_poem_title = target_poem_title or (docs[0].metadata.get("poem_title") if docs else None)
    
    return {
        "answer": clean_answer,
        "context_sources": unique_sources,
        "top_poem_title": top_poem_title
    }

