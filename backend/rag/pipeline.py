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
    model_name="qwen/qwen3.6-27b", 
    api_key=os.getenv("GROQ_API_KEY", "dummy_key_change_me")
)

prompt_template = """
You are an expert Sangam Tamil Literature AI assistant.
Answer the user's question clearly, concisely, and accurately in natural Tamil.

STRICT RAG RULES:
1. Answer STRICTLY and ONLY using the provided Context below.
2. DO NOT use external general knowledge or hallucinate any facts not explicitly present in the Context.
3. If the user's question cannot be answered using ONLY the provided Context, respond with exact JSON:
   {{"answer": "மன்னித்துக்கொள்ளுங்கள், இந்த கேள்விக்கான தகவல்கள் நமது தரவுத்தளத்தில் பதிவேற்றப்படவில்லை."}}
4. Provide ONLY a clean, well-formatted Tamil answer.
5. DO NOT include any debug labels, internal headers (like "Detailed Explanation:", "Static QA Pair:", "Question:", "Answer:").
6. YOU MUST RETURN YOUR RESPONSE AS A VALID JSON OBJECT with exactly one key: "answer".

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
    
    # Try parsing raw JSON structure if stringified JSON leaked
    trimmed = text.strip()
    if trimmed.startswith('{') and '"answer"' in trimmed:
        try:
            parsed = json.loads(trimmed)
            if isinstance(parsed, dict) and "answer" in parsed:
                text = str(parsed["answer"])
        except Exception:
            match = re.search(r'"answer"\s*:\s*"([^"]+)"', trimmed, re.DOTALL)
            if match:
                text = match.group(1)

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
    
    # Enhance search query if it's a single word or short phrase
    search_query = question
    if len(question.strip().split()) <= 2:
        search_query = f"{question} என்பதன் பொருள் என்ன?"
        
    # 1. Retrieve relevant context manually using enhanced search query
    docs = vector_store.similarity_search(search_query, k=3)
    
    # Strict validation: Check if user asked for a specific poem number (e.g. '89', '87', '101')
    requested_numbers = re.findall(r'\b\d+\b', question)
    if requested_numbers:
        found_in_docs = False
        for req_num in requested_numbers:
            for doc in docs:
                doc_title = str(doc.metadata.get('poem_title', ''))
                if req_num in doc_title or req_num in doc.page_content:
                    found_in_docs = True
                    break
            if found_in_docs:
                break
        
        # If user explicitly asked for a poem number not found in retrieved docs context
        if not found_in_docs:
            req_num_str = requested_numbers[0]
            return {
                "answer": f"மன்னித்துக்கொள்ளுங்கள், புறநானூறு {req_num_str} பற்றிய தகவல்கள் நமது தரவுத்தளத்தில் பதிவேற்றப்படவில்லை. Admin பதிவேற்றிய பாடல்கள் பற்றி மட்டுமே என்னால் தகவல் அளிக்க முடியும்.",
                "context_sources": [],
                "top_poem_title": None
            }

    context_text = "\n\n".join([doc.page_content for doc in docs])
    
    # 2. Invoke the LLM with the context, history, and original question
    content = ""
    try:
        response = chain.invoke({"context": context_text, "chat_history": history_str, "input": question})
        content = response.content
    except Exception as llm_err:
        print(f"LLM Invoke error: {llm_err}")
        if context_text and context_text.strip():
            content = context_text
        else:
            content = "மன்னித்துக்கொள்ளுங்கள், இந்த கேள்விக்கான தகவல் தரவுத்தளத்தில் கண்டறியப்படவில்லை."
    
    # 3. Parse JSON from response
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
    
    # Clean answer text from debug headers or leaked static QA blocks
    clean_answer = clean_answer_text(answer_text)
    if not clean_answer or len(clean_answer.strip()) < 5:
        clean_answer = "மன்னித்துக்கொள்ளுங்கள், புறநானூறு தரவுத்தளத்தில் உங்கள் கேள்விக்கான தகவலைத் தேடுவதில் ஒரு சிறிய சிக்கல் ஏற்பட்டது. தயவுசெய்து மீண்டும் கேட்கவும்."
    
    # Extract clean source names from metadata (remove duplicates)

    sources = []
    for doc in docs:
        title = doc.metadata.get('poem_title') or 'புறநானூறு'
        poet = doc.metadata.get('poet')
        if poet and poet != 'Unknown' and poet.strip():
            sources.append(f"{title} ({poet})")
        else:
            sources.append(f"{title}")
    unique_sources = list(dict.fromkeys(sources))
    top_poem_title = docs[0].metadata.get("poem_title") if docs else None
    
    return {
        "answer": clean_answer,
        "context_sources": unique_sources,
        "top_poem_title": top_poem_title
    }

