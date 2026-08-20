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
    # 1. Save to SQLite
    db_poems = []
    new_pydantic_poems = []
    
    for p in poems:
        existing = db.query(Poem).filter(Poem.poem_title == p.basic_information.poem_title).first()
        if not existing:
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
            new_pydantic_poems.append(p)
    db.commit()
    
    # 2. Add to Chroma Vector DB
    if new_pydantic_poems:
        add_to_vector_db(new_pydantic_poems)
        
    return {"message": f"Successfully uploaded {len(db_poems)} poems and indexed in vector database."}

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
    # Fetch specific starter questions based on IDs or randomly from Factual
    # We will pick original_id 1, 4, 9, 11
    starter_ids = [1, 4, 9, 11]
    starters = db.query(PoemQA).filter(PoemQA.original_id.in_(starter_ids)).all()
    # If not found, return up to 4 factual
    if not starters:
        starters = db.query(PoemQA).filter(PoemQA.type == 'factual').limit(4).all()
    return starters

import random

def get_related_questions(db: Session, qa: PoemQA):
    # Try to get next sequential questions (original_id + 1, +2, etc.) to feel more logical
    related = db.query(PoemQA).filter(
        PoemQA.poem_id == qa.poem_id, 
        PoemQA.original_id > qa.original_id
    ).order_by(PoemQA.original_id).limit(4).all()
    
    # Fallback to random if we reached the end
    if len(related) < 4:
        more = db.query(PoemQA).filter(
            PoemQA.poem_id == qa.poem_id, 
            PoemQA.id != qa.id,
            PoemQA.id.notin_([r.id for r in related]) if related else True
        ).order_by(func.random()).limit(4 - len(related)).all()
        related.extend(more)
    return related

@router.get("/qa/{question_id}", response_model=dict)
def get_qa_answer(question_id: int, db: Session = Depends(get_db)):
    qa = db.query(PoemQA).filter((PoemQA.id == question_id) | (PoemQA.original_id == question_id)).first()
    if not qa:
        raise HTTPException(status_code=404, detail="Question not found")
        
    related = get_related_questions(db, qa)
    
    return {
        "answer": qa.answer,
        "related_questions": [r.question for r in related],
        "related_question_ids": [r.id for r in related]
    }

@router.post("/chat", response_model=ChatResponse)
def chat_with_ai(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        # 1. Fuzzy String Matching for Highly Similar QA Pair
        import difflib
        
        all_qas = db.query(PoemQA).all()
        high_confidence_qa = None
        best_ratio = 0.0
        
        user_q = request.question.strip().lower()
        
        for qa in all_qas:
            db_q = qa.question.strip().lower()
            ratio = difflib.SequenceMatcher(None, user_q, db_q).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                if ratio > 0.75:  # 75% similarity threshold
                    high_confidence_qa = qa
                    
        if high_confidence_qa:
            related = get_related_questions(db, high_confidence_qa)
            return ChatResponse(
                answer=high_confidence_qa.answer,
                context_sources=["உறுதிசெய்யப்பட்ட வினா-விடை சான்று (Verified Dataset)"],
                suggested_questions=[r.question for r in related],
                suggested_question_ids=[r.id for r in related],
                is_verified_static=True
            )

        # 2. Otherwise fallback to RAG (which will now retrieve both Poem and QA chunks from Chroma DB)
        result = generate_answer(request.question, request.chat_history)
        
        top_poem_title = result.get("top_poem_title")
        related_qas = []
        if top_poem_title:
            poem = db.query(Poem).filter(Poem.poem_title == top_poem_title).first()
            if poem:
                # Fetch related questions for the poem identified by RAG
                related_qas = db.query(PoemQA).filter(PoemQA.poem_id == poem.id).limit(4).all()
        
        # If no poem matched or not enough questions, fallback to random static questions
        if len(related_qas) < 4:
            more_qas = db.query(PoemQA).filter(
                PoemQA.id.notin_([r.id for r in related_qas]) if related_qas else True
            ).order_by(func.random()).limit(4 - len(related_qas)).all()
            related_qas.extend(more_qas)
        
        return ChatResponse(
            answer=result["answer"],
            context_sources=result["context_sources"],
            suggested_questions=[r.question for r in related_qas],
            suggested_question_ids=[r.id for r in related_qas],
            is_verified_static=False
        )
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        raise HTTPException(status_code=500, detail=error_details)
