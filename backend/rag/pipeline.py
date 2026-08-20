from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from vector_db.qdrant_db import vector_store
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Groq LLM
# You need to set GROQ_API_KEY in your .env file
# Initialize Groq LLM
# You need to set GROQ_API_KEY in your .env file
llm = ChatGroq(
    temperature=0.6,
    model_name="llama-3.1-8b-instant", 
    api_key=os.getenv("GROQ_API_KEY", "dummy_key_change_me")
)

import json
import re

prompt_template = """
You are a highly accurate Sangam Tamil Literature AI assistant.
Your goal is to be exceptionally helpful and detailed.

Follow these strict rules:
1. If the user provides a single word or short phrase (e.g., 'உவமை', 'தேர்', 'திணை'), they are asking for its meaning. First, provide a clear, general definition of the word in Tamil using your own knowledge. Then, if the provided Context contains specific examples or usage of this word in the poems, explain that connection as well.
2. For specific questions about the poems, you MUST use the provided Context to explain thoroughly and accurately.
3. If the Context does NOT contain the answer to a poem-specific question, you MUST explicitly state that you don't have that information. Do not hallucinate facts about the poems.
4. DO NOT repeat sentences or get stuck in a loop.
5. YOU MUST RETURN YOUR RESPONSE AS A VALID JSON OBJECT. Do not include any other text outside the JSON.
6. The JSON must have exactly one key: "answer" (string).

Output Format:
```json
{{
  "answer": "your detailed response here..."
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

# Use standard LCEL chain to avoid module errors with newer langchain versions
chain = prompt | llm

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
    context_text = "\n\n".join([doc.page_content for doc in docs])
    
    # 2. Invoke the LLM with the context, history, and original question
    response = chain.invoke({"context": context_text, "chat_history": history_str, "input": question})
    content = response.content
    
    # 3. Parse JSON from response
    answer_text = content
    suggested_questions = []
    
    try:
        # Try to find JSON block if LLM wrapped it in markdown
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = content
            
        parsed_json = json.loads(json_str)
        answer_text = parsed_json.get("answer", content)
        suggested_questions = parsed_json.get("suggested_questions", [])
    except Exception as e:
        print(f"Failed to parse JSON response: {e}")
        # Fallback if LLM failed to return JSON
        answer_text = content.replace('```json', '').replace('```', '')
    
    # Extract clean source names from metadata (remove duplicates)
    unique_sources = list(set([f"{doc.metadata.get('poem_title', 'Unknown')} ({doc.metadata.get('poet', 'Unknown')})" for doc in docs]))
    
    top_poem_title = docs[0].metadata.get("poem_title") if docs else None
    
    return {
        "answer": answer_text,
        "context_sources": unique_sources,
        "top_poem_title": top_poem_title
    }
