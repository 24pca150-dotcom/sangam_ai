from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy import func, or_

from models.database import get_db, Poem, PoemQA
from models.schemas import PoemCreate, PoemResponse, ChatRequest, ChatResponse, PoemQAUploadRequest, PoemQAResponse
from vector_db.qdrant_db import add_to_vector_db
from rag.pipeline import generate_answer

router = APIRouter()

@router.get("/health")
def health_check():
    return {"status": "ok"}

@router.post("/poems/upload", response_model=dict)
def upload_poems(poems: List[PoemCreate], db: Session = Depends(get_db)):
    db_poems = []
    pydantic_poems_to_index = []
    
    for p in poems:
        existing = db.query(Poem).filter(
            or_(Poem.poem_title == p.basic_information.poem_title, Poem.poem_number == p.basic_information.poem_number)
        ).first()
        
        if existing:
            # Update existing poem record safely (No duplicate rows)
            existing.poem_title = p.basic_information.poem_title
            existing.poem_number = p.basic_information.poem_number
            existing.anthology_name = p.basic_information.anthology_name
            existing.poet_name = p.basic_information.poet_name
            existing.basic_information = p.basic_information.model_dump()
            existing.historical_information = p.historical_information.model_dump()
            existing.meaning_interpretation = p.meaning_interpretation.model_dump()
            existing.literary_classification = p.literary_classification
            existing.literary_analysis = p.literary_analysis
            existing.language_analysis = p.language_analysis
            existing.grammar_analysis = p.grammar_analysis
            existing.detailed_glossary = p.detailed_glossary
            existing.line_by_line_meaning = p.line_by_line_meaning
            existing.keywords = p.keywords
            existing.named_entities = p.named_entities
            existing.poem_structure = p.poem_structure
            existing.references = p.references
            db_poems.append(existing)
            pydantic_poems_to_index.append(p)
        else:
            db_poem = Poem(
                poem_title=p.basic_information.poem_title,
                poem_number=p.basic_information.poem_number,
                anthology_name=p.basic_information.anthology_name,
                poet_name=p.basic_information.poet_name,
                basic_information=p.basic_information.model_dump(),
                historical_information=p.historical_information.model_dump(),
                meaning_interpretation=p.meaning_interpretation.model_dump(),
                literary_classification=p.literary_classification,
                literary_analysis=p.literary_analysis,
                language_analysis=p.language_analysis,
                grammar_analysis=p.grammar_analysis,
                detailed_glossary=p.detailed_glossary,
                line_by_line_meaning=p.line_by_line_meaning,
                keywords=p.keywords,
                named_entities=p.named_entities,
                poem_structure=p.poem_structure,
                references=p.references
            )
            db.add(db_poem)
            db_poems.append(db_poem)
            pydantic_poems_to_index.append(p)
            
    db.commit()
    
    # Index in Vector DB
    if pydantic_poems_to_index:
        add_to_vector_db(pydantic_poems_to_index)
        
    return {"message": f"Successfully processed {len(db_poems)} poems and indexed in vector database."}


@router.get("/poems/search", response_model=List[PoemResponse])
def search_poems(keyword: str = None, poet: str = None, db: Session = Depends(get_db)):
    query = db.query(Poem)
    if poet:
        query = query.filter(Poem.poet_name.ilike(f"%{poet}%"))
    # Keyword search fallback
    if keyword:
        query = query.filter(
            or_(
                Poem.poem_title.ilike(f"%{keyword}%"),
                Poem.poet_name.ilike(f"%{keyword}%"),
                Poem.anthology_name.ilike(f"%{keyword}%")
            )
        )
    return query.all()

@router.get("/poems/{identifier}", response_model=PoemResponse)
def get_poem(identifier: str, db: Session = Depends(get_db)):
    # Try fetching by poem_number if identifier is a digit
    if identifier.isdigit():
        poem = db.query(Poem).filter(Poem.poem_number == int(identifier)).first()
        if poem:
            return poem
            
    # Fallback to fetching by title
    poem = db.query(Poem).filter(Poem.poem_title == identifier).first()
    if not poem:
        raise HTTPException(status_code=404, detail="Poem not found")
    return poem

@router.post("/qa/upload")
def upload_qa_pairs(payload: PoemQAUploadRequest, db: Session = Depends(get_db)):
    db_qas = []
    poem_id = payload.poem_id
    # Ensure poem exists if poem_title is provided
    if payload.poem_title and not poem_id:
        poem = db.query(Poem).filter(Poem.poem_title == payload.poem_title).first()
        if poem:
            poem_id = poem.id
    
    for qa in payload.qa_pairs:
        # Check if already exists based on original_id and poem_id
        existing = db.query(PoemQA).filter(PoemQA.original_id == qa.id, PoemQA.poem_id == poem_id).first()
        if not existing:
            db_qa = PoemQA(
                poem_id=poem_id,
                original_id=qa.id,
                type=qa.type,
                question=qa.question,
                answer=qa.answer
            )
            db.add(db_qa)
            db_qas.append(db_qa)
    db.commit()
    
    # Also add the newly uploaded QA pairs to Chroma Vector DB
    from vector_db.qdrant_db import add_qa_to_vector_db
    if db_qas:
        add_qa_to_vector_db(db_qas, poem_title=payload.poem_title or "Unknown Poem")
        
    return {"message": f"Successfully uploaded {len(db_qas)} QA pairs and indexed in vector database."}

@router.get("/qa/starter", response_model=List[PoemQAResponse])
def get_starter_qa(db: Session = Depends(get_db)):
    # Fetch questions directly from the user's uploaded PoemQA database
    starters = db.query(PoemQA).filter(PoemQA.type == 'factual').limit(4).all()
    if not starters:
        starters = db.query(PoemQA).limit(4).all()
    return starters


import random

def get_smart_suggestions(db: Session, current_question: str, current_qa_id: int = None, target_poem_title: str = None, chat_history: list = None):
    import re
    def clean_str_local(s: str) -> str:
        return re.sub(r'[^\w\s]', '', s or '').strip().lower()

    asked_texts = set()
    if current_question:
        asked_texts.add(clean_str_local(current_question))
    if chat_history:
        for msg in chat_history:
            content = getattr(msg, 'content', None) or (msg.get('content') if isinstance(msg, dict) else None)
            if content:
                asked_texts.add(clean_str_local(content))
    
    target_nums = re.findall(r'\d+', f"{target_poem_title or ''} {current_question or ''}")
    candidate_qas = []
    
    if target_nums:
        req_num = target_nums[0]
        if req_num.isdigit():
            poems = db.query(Poem).filter(Poem.poem_number == int(req_num)).all()
            poem_ids = [p.id for p in poems]
            if poem_ids:
                candidate_qas = db.query(PoemQA).filter(PoemQA.poem_id.in_(poem_ids)).all()
        
        if not candidate_qas:
            candidate_qas = db.query(PoemQA).filter(
                or_(PoemQA.question.ilike(f"%{req_num}%"), PoemQA.answer.ilike(f"%{req_num}%"))
            ).all()

    if not candidate_qas and current_qa_id:
        qa_obj = db.query(PoemQA).filter(PoemQA.id == current_qa_id).first()
        if qa_obj and qa_obj.poem_id:
            candidate_qas = db.query(PoemQA).filter(PoemQA.poem_id == qa_obj.poem_id).all()
            
    if not candidate_qas:
        candidate_qas = db.query(PoemQA).all()

    final_suggestions = []
    for qa in candidate_qas:
        if current_qa_id and qa.id == current_qa_id:
            continue
        q_clean = clean_str_local(qa.question)
        if any(asked == q_clean for asked in asked_texts):
            continue
        final_suggestions.append(qa)
        if len(final_suggestions) >= 4:
            break
            
    if len(final_suggestions) < 4:
        all_other = db.query(PoemQA).all()
        for qa in all_other:
            if any(f.id == qa.id for f in final_suggestions):
                continue
            if current_qa_id and qa.id == current_qa_id:
                continue
            q_clean = clean_str_local(qa.question)
            if any(asked == q_clean for asked in asked_texts):
                continue
            final_suggestions.append(qa)
            if len(final_suggestions) >= 4:
                break
                
    return final_suggestions

def get_related_questions(db: Session, qa: PoemQA):
    return get_smart_suggestions(db, current_question=qa.question, current_qa_id=qa.id)

@router.get("/qa/{question_id}", response_model=dict)
def get_qa_answer(question_id: int, db: Session = Depends(get_db)):
    qa = db.query(PoemQA).filter((PoemQA.id == question_id) | (PoemQA.original_id == question_id)).first()
    if not qa:
        raise HTTPException(status_code=404, detail="Question not found")
        
    related = get_smart_suggestions(db, current_question=qa.question, current_qa_id=qa.id)
    
    return {
        "answer": qa.answer,
        "related_questions": [r.question for r in related],
        "related_question_ids": [r.id for r in related]
    }

@router.post("/chat", response_model=ChatResponse)
def chat_with_ai(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        # 1. Enhanced String & Keyword Matching for QA Pair
        import difflib, re
        
        def clean_str(s: str) -> str:
            return re.sub(r'[^\w\s]', '', s).strip().lower()

        user_q_clean = clean_str(request.question)
        user_words = [w for w in user_q_clean.split() if len(w) > 1]
        
        all_qas = db.query(PoemQA).all()
        high_confidence_qa = None
        best_ratio = 0.0
        
        user_nums = re.findall(r'\d+', request.question)
        
        for qa in all_qas:
            if user_nums:
                qa_text = f"{qa.question} {qa.poem_id or ''}"
                poem_obj = db.query(Poem).filter(Poem.id == qa.poem_id).first() if qa.poem_id else None
                poem_num_str = str(poem_obj.poem_number) if poem_obj else ""
                if not any(num in qa_text or num == poem_num_str for num in user_nums):
                    continue

            db_q_clean = clean_str(qa.question)
            ratio = difflib.SequenceMatcher(None, user_q_clean, db_q_clean).ratio()
            main_keywords = [w for w in re.sub(r'[^\w\s]', '', qa.question).split() if len(w) > 3]
            keyword_match = any(kw.lower() in user_q_clean for kw in main_keywords) if main_keywords else False
            
            if ratio > best_ratio:
                best_ratio = ratio
                if ratio > 0.65 or (ratio > 0.45 and keyword_match):
                    high_confidence_qa = qa
                    
        if high_confidence_qa:
            related = get_smart_suggestions(db, current_question=request.question, current_qa_id=high_confidence_qa.id, chat_history=request.chat_history)
            return ChatResponse(
                answer=high_confidence_qa.answer,
                context_sources=["உறுதிசெய்யப்பட்ட வினா-விடை சான்று (Verified Dataset)"],
                suggested_questions=[r.question for r in related],
                suggested_question_ids=[r.id for r in related],
                is_verified_static=True
            )

        # 2. Otherwise query RAG
        result = generate_answer(request.question, request.chat_history)
        
        top_poem_title = result.get("top_poem_title")
        related_qas = []
        is_not_found = "மன்னித்துக்கொள்ளுங்கள்" in result.get("answer", "") or not top_poem_title
        
        # Only fetch related questions if valid answer was found in database
        if not is_not_found:
            related_qas = get_smart_suggestions(
                db, 
                current_question=request.question, 
                target_poem_title=top_poem_title, 
                chat_history=request.chat_history
            )
        
        return ChatResponse(
            answer=result["answer"],
            context_sources=[] if is_not_found else result["context_sources"],
            suggested_questions=[r.question for r in related_qas],
            suggested_question_ids=[r.id for r in related_qas],
            is_verified_static=False
        )

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        raise HTTPException(status_code=500, detail=error_details)
