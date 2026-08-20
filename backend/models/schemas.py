from pydantic import BaseModel
from typing import Optional, List, Any, Dict

class BasicInformation(BaseModel):
    poem_number: int
    anthology_name: str
    poem_title: str
    poet_name: str
    poet_gender: str
    poet_details: str
    original_tamil_text: str

class HistoricalInformation(BaseModel):
    historical_context: str
    time_period: str
    dynasty: str
    king_mentioned: str
    place_mentioned: str
    social_background: str

class MeaningInterpretation(BaseModel):
    simple_tamil_meaning: str
    detailed_tamil_explanation: str
    english_translation: str
    summary: Optional[str] = None
    core_message: Optional[str] = None
    thematic_tags: Optional[List[str]] = None

class PoemCreate(BaseModel):
    basic_information: BasicInformation
    historical_information: HistoricalInformation
    meaning_interpretation: MeaningInterpretation
    
    # New Optional fields for full JSON compatibility
    literary_classification: Optional[Dict[str, Any]] = None
    literary_analysis: Optional[Dict[str, Any]] = None
    language_analysis: Optional[Any] = None
    grammar_analysis: Optional[Any] = None
    detailed_glossary: Optional[List[Dict[str, Any]]] = None
    line_by_line_meaning: Optional[List[Dict[str, Any]]] = None
    keywords: Optional[List[str]] = None
    named_entities: Optional[Dict[str, Any]] = None
    poem_structure: Optional[Dict[str, Any]] = None
    references: Optional[Dict[str, Any]] = None

class PoemResponse(PoemCreate):
    id: int

    class Config:
        from_attributes = True

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    question: str
    chat_history: Optional[List[ChatMessage]] = []

class ChatResponse(BaseModel):
    answer: str
    context_sources: List[str]
    suggested_questions: List[str]
    suggested_question_ids: Optional[List[int]] = [] # For static suggestions
    is_verified_static: Optional[bool] = False

class PoemQACreate(BaseModel):
    id: int
    type: str
    question: str
    answer: str

class PoemQAUploadRequest(BaseModel):
    poem_id: Optional[int] = None
    poem_title: Optional[str] = None
    qa_pairs: List[PoemQACreate]

class PoemQAResponse(BaseModel):
    id: int
    poem_id: Optional[int]
    original_id: int
    type: str
    question: str
    answer: str

    class Config:
        from_attributes = True
