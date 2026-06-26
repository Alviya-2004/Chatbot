from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from ..database.db import get_db
from ..database.models import ChatSession, ChatMessage, BotFallback, BotAnalytics
from ..services.rag_service import rag_service
from ..services.lead_scoring import evaluate_lead_score, get_lead_category
from ..services.llm_service import llm_service
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/api/chat", tags=["Chat"])

# --- Pydantic Models ---
class ChatStartRequest(BaseModel):
    visitor_id: Optional[str] = None
    source_page: Optional[str] = None

class ChatStartResponse(BaseModel):
    session_id: str
    reply: str

class ChatRequest(BaseModel):
    session_id: str
    message: str
    user_persona: Optional[str] = None
    current_page_url: Optional[str] = None
    current_score: int = 0

class ChatResponse(BaseModel):
    reply: str
    new_score: int
    lead_category: str
    trigger_form: bool
    suggested_replies: List[str] = []

class ChatMessageModel(BaseModel):
    id: int
    sender: str
    message: str
    created_at: datetime

    class Config:
        orm_mode = True

# --- Analytics Helper ---
def increment_analytics(db: Session, metric_name: str):
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    record = db.query(BotAnalytics).filter(BotAnalytics.date == date_str).first()
    if not record:
        record = BotAnalytics(date=date_str)
        db.add(record)
        db.flush()
    
    current_val = getattr(record, metric_name) or 0
    setattr(record, metric_name, current_val + 1)
    
    # Recalculate conversion rate
    total_chats = record.total_chats or 0
    total_leads = record.total_leads or 0
    if total_chats > 0:
        record.conversion_rate = round((total_leads / total_chats) * 100, 2)
        
    db.commit()

# --- Endpoints ---

@router.post("/start", response_model=ChatStartResponse)
async def chat_start(req: ChatStartRequest, db: Session = Depends(get_db)):
    session_id = str(uuid.uuid4())
    
    # Create database entry
    new_session = ChatSession(
        session_id=session_id,
        visitor_id=req.visitor_id,
        source_page=req.source_page,
        status="active"
    )
    db.add(new_session)
    db.commit()
    
    # Increment total chats count in daily stats
    increment_analytics(db, "total_chats")
    
    # AI Greeting Text
    reply = "Hi there! I am CarePilot, your personal career assistant at Portfolio Builders. Are you looking for a course, internship, portfolio review, or career guidance today?"
    
    # Save greeting to session messages
    welcome_msg = ChatMessage(
        session_id=session_id,
        sender="ai",
        message=reply
    )
    db.add(welcome_msg)
    db.commit()
    
    return ChatStartResponse(session_id=session_id, reply=reply)

@router.post("/message", response_model=ChatResponse)
async def chat_message(req: ChatRequest, db: Session = Depends(get_db)):
    # 1. Look up session
    session = db.query(ChatSession).filter(ChatSession.session_id == req.session_id).first()
    if not session:
        # Create session if missing (fallback for widget reconnects)
        session = ChatSession(
            session_id=req.session_id,
            source_page=req.current_page_url,
            status="active"
        )
        db.add(session)
        db.commit()
        increment_analytics(db, "total_chats")

    # 2. Evaluate and Update Lead Score
    new_score = evaluate_lead_score(req.message, req.current_score, req.current_page_url or "")
    category = get_lead_category(new_score)
    trigger_form = new_score > 30

    # If lead score crosses threshold, we can flag this in daily analytics
    if new_score >= 61 and req.current_score < 61:
        # Just crossed into 'Hot' lead range
        increment_analytics(db, "hot_leads")

    # 3. Store User Message
    user_msg = ChatMessage(
        session_id=req.session_id,
        sender="user",
        message=req.message,
        intent=req.user_persona
    )
    db.add(user_msg)
    db.commit()

    # 4. RAG Retrieval
    category_filter = None
    if req.current_page_url:
        if "course" in req.current_page_url.lower():
            category_filter = "courses"
        elif "internship" in req.current_page_url.lower():
            category_filter = "internships"

    context = rag_service.query_context(req.message, category_filter)

    # 5. Groq Chat Completion with Prompt Template
    prompt = f"""
You are CarePilot AI, the official AI assistant of Portfolio Builders.
CRITICAL CONTEXT: Portfolio Builders is an EdTech and Career Guidance company focused on UI/UX courses, Full Stack Development, Internships (AICTE/FYUGP), and career portfolio building. It is strictly NOT a finance or investment company.

Your goal is to provide VERY CONCISE answers based ONLY on the provided context.

RULES:
1. Use ONLY the information in the 'Context information' section.
2. If the answer is not in the context, say: "I'm sorry, I don't have that specific information right now. Please chat with us on WhatsApp at +91 7994721792 for more details!"
3. Keep answers under 3-4 sentences. Use bullet points if listing items.
4. Be professional and warm, but direct.

CRITICAL INSTRUCTION: You must respond in valid JSON format.
The JSON must contain two keys: "reply" (your response to the user) and "suggested_replies" (an array of 2-3 short, relevant follow-up questions the user might ask next, based on the current context).

Context information:
---------------------
{context}
---------------------

Query: {req.message}
"""

    llm_output = llm_service.generate_json_reply(prompt)
    reply = llm_output.get("reply", "I'm sorry, I encountered an error formatting my response.")
    suggested_replies = llm_output.get("suggested_replies", [])

    # 6. Fallback and Low-Confidence Handling
    # If RAG returned no context or LLM response indicates lack of info, treat as fallback
    is_fallback = False
    if not context or "don't have that specific information" in reply or "sorry" in reply.lower() and "whatsapp" in reply.lower():
        is_fallback = True
        
    if is_fallback:
        # Create a bot fallback entry
        fallback = BotFallback(
            user_question=req.message,
            bot_response=reply,
            session_id=req.session_id,
            resolved_status="unresolved"
        )
        db.add(fallback)
        db.commit()
        # Increment unanswered question counter
        increment_analytics(db, "unanswered_questions")

    # 7. Store AI Response
    ai_msg = ChatMessage(
        session_id=req.session_id,
        sender="ai",
        message=reply,
        source_used=context[:200] if context else None
    )
    db.add(ai_msg)
    db.commit()

    return ChatResponse(
        reply=reply,
        new_score=new_score,
        lead_category=category,
        trigger_form=trigger_form,
        suggested_replies=suggested_replies
    )

@router.get("/session/{session_id}", response_model=List[ChatMessageModel])
async def get_session_history(session_id: str, db: Session = Depends(get_db)):
    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc()).all()
    # Manual conversion to handle pydantic v1/v2 compatibility issues if orm_mode is finicky
    return [
        ChatMessageModel(
            id=msg.id,
            sender=msg.sender,
            message=msg.message,
            created_at=msg.created_at
        ) for msg in messages
    ]

@router.post("/end")
async def end_session(session_id: str, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
    if session:
        session.status = "completed"
        db.commit()
        return {"status": "success", "message": "Session marked as completed."}
    raise HTTPException(status_code=404, detail="Session not found.")
