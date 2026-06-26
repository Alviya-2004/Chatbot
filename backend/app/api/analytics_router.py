from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from ..database.db import get_db
from ..database.models import Lead, ChatSession, ChatMessage, BotFallback, BotAnalytics, KnowledgeDocument
from ..api.knowledge_router import index_document_in_rag
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/api/admin/analytics", tags=["Analytics"])

# --- Pydantic Models ---
class FallbackResolveRequest(BaseModel):
    admin_answer: str

class BotAnalyticsResponse(BaseModel):
    date: str
    total_chats: int
    total_leads: int
    hot_leads: int
    whatsapp_clicks: int
    unanswered_questions: int
    conversion_rate: float

    class Config:
        orm_mode = True

class UnansweredQuestionResponse(BaseModel):
    id: int
    user_question: str
    bot_response: str
    session_id: Optional[str] = None
    resolved_status: str
    admin_answer: Optional[str] = None
    created_at: datetime

    class Config:
        orm_mode = True

# --- Endpoints ---

@router.get("/chat", response_model=List[BotAnalyticsResponse])
async def get_chat_analytics(db: Session = Depends(get_db)):
    # Returns last 30 days of analytics
    records = db.query(BotAnalytics).order_by(BotAnalytics.date.desc()).limit(30).all()
    return records

@router.get("/leads")
async def get_lead_analytics(db: Session = Depends(get_db)):
    # Calculate counts by lead temperature
    leads = db.query(Lead).all()
    
    temperatures = {"Cold lead": 0, "Warm lead": 0, "Hot lead": 0, "High priority lead": 0}
    statuses = {"New": 0, "Contacted": 0, "Enrolled": 0, "Junk": 0}
    program_interests = {}
    
    for lead in leads:
        # Temperature distribution
        temp = lead.lead_temperature or "Cold lead"
        temperatures[temp] = temperatures.get(temp, 0) + 1
        
        # Status distribution
        status = lead.status or "New"
        statuses[status] = statuses.get(status, 0) + 1
        
        # Course/Internship interests
        prog = lead.interested_program
        if prog:
            program_interests[prog] = program_interests.get(prog, 0) + 1
            
    # Calculate conversion metrics
    total_sessions = db.query(ChatSession).count()
    total_leads = len(leads)
    conversion_rate = round((total_leads / total_sessions) * 100, 2) if total_sessions > 0 else 0.0
    
    return {
        "total_sessions": total_sessions,
        "total_leads": total_leads,
        "conversion_rate": conversion_rate,
        "temperature_distribution": temperatures,
        "status_distribution": statuses,
        "program_interests": program_interests
    }

@router.get("/unanswered-questions", response_model=List[UnansweredQuestionResponse])
async def get_unanswered_questions(db: Session = Depends(get_db)):
    # Retrieve all unresolved fallback questions
    records = db.query(BotFallback).order_by(BotFallback.created_at.desc()).all()
    return records

@router.put("/unanswered-questions/{fallback_id}/resolve")
async def resolve_unanswered_question(
    fallback_id: int, 
    req: FallbackResolveRequest, 
    db: Session = Depends(get_db)
):
    fallback = db.query(BotFallback).filter(BotFallback.id == fallback_id).first()
    if not fallback:
        raise HTTPException(status_code=404, detail="Fallback question not found.")
        
    # Update fallback details
    fallback.admin_answer = req.admin_answer
    fallback.resolved_status = "resolved"
    db.commit()
    
    # Ingest the resolution into the knowledge base document list and vector store!
    # This acts as a feedback loop.
    title = f"Resolved FAQ: {fallback.user_question[:50]}..."
    qa_text = f"Question: {fallback.user_question}\nAnswer: {req.admin_answer}"
    
    # Save as knowledge document in SQLite
    new_doc = KnowledgeDocument(
        title=title,
        source_type="manual",
        content=qa_text,
        status="approved"
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    
    # Index in ChromaDB
    index_document_in_rag(
        doc_id=new_doc.id,
        title=title,
        content=qa_text,
        category="general",
        source="admin_resolved_fallback"
    )
    
    return {"status": "success", "message": "Question resolved and successfully indexed into knowledge base."}
