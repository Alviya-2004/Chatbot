from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from ..database.db import get_db
from ..database.models import Lead, BotAnalytics
from ..services.lead_scoring import get_lead_category
from pydantic import BaseModel, EmailStr
from typing import Optional, List

router = APIRouter(prefix="/api/leads", tags=["Leads"])

# --- Pydantic Models ---
class LeadCreate(BaseModel):
    name: str
    phone: str
    email: EmailStr
    location: Optional[str] = None
    current_status: Optional[str] = None
    interested_program: Optional[str] = None
    goal: Optional[str] = None
    preferred_mode: Optional[str] = None
    urgency: Optional[str] = None
    lead_score: Optional[int] = 0
    source_page: Optional[str] = None
    conversation_summary: Optional[str] = None

class LeadResponse(BaseModel):
    id: int
    name: str
    phone: str
    email: str
    lead_score: int
    lead_temperature: str
    status: str
    created_at: datetime

    class Config:
        orm_mode = True

class LeadDetailResponse(LeadResponse):
    location: Optional[str] = None
    current_status: Optional[str] = None
    interested_program: Optional[str] = None
    goal: Optional[str] = None
    preferred_mode: Optional[str] = None
    urgency: Optional[str] = None
    conversation_summary: Optional[str] = None
    assigned_to: Optional[str] = None

class StatusUpdate(BaseModel):
    status: str

class WhatsAppNotificationRequest(BaseModel):
    lead_id: int

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

@router.post("/create", response_model=LeadResponse)
async def create_lead(req: LeadCreate, db: Session = Depends(get_db)):
    # Calculate lead temperature category
    temp = get_lead_category(req.lead_score or 0)
    
    # Create lead record
    new_lead = Lead(
        name=req.name,
        phone=req.phone,
        email=req.email,
        location=req.location,
        current_status=req.current_status,
        interested_program=req.interested_program,
        goal=req.goal,
        preferred_mode=req.preferred_mode,
        urgency=req.urgency,
        lead_score=req.lead_score or 0,
        lead_temperature=temp,
        source_page=req.source_page,
        conversation_summary=req.conversation_summary,
        status="New"
    )
    db.add(new_lead)
    db.commit()
    db.refresh(new_lead)
    
    # Increment total leads inside daily stats
    increment_analytics(db, "total_leads")
    
    return new_lead

@router.get("/admin", response_model=List[LeadResponse])
async def get_all_leads(db: Session = Depends(get_db)):
    # Retrieve leads sorted by score descending
    leads = db.query(Lead).order_by(Lead.lead_score.desc()).all()
    return leads

@router.get("/admin/{lead_id}", response_model=LeadDetailResponse)
async def get_lead_details(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return lead

@router.put("/admin/{lead_id}/status", response_model=LeadResponse)
async def update_lead_status(lead_id: int, req: StatusUpdate, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")
    
    lead.status = req.status
    db.commit()
    db.refresh(lead)
    return lead

@router.post("/send-whatsapp-notification")
async def send_whatsapp_notification(req: WhatsAppNotificationRequest, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == req.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")
    
    # Generate the formatted WhatsApp message context to team as requested in Section 18
    message_content = f"""
New Hot Lead from CarePilot AI

Name: {lead.name}
Phone: {lead.phone}
Email: {lead.email}
Interest: {lead.interested_program or 'Not Specified'}
Goal: {lead.goal or 'Not Specified'}
Status: {lead.current_status or 'Not Specified'}
Lead Score: {lead.lead_score}/100
Source Page: {lead.source_page or 'Not Specified'}
Summary: {lead.conversation_summary or 'No summary recorded.'}
"""
    # Increment whatsapp clicks counter in daily stats
    increment_analytics(db, "whatsapp_clicks")

    # In a production environment, this would call a WhatsApp Business API webhook (e.g. Twilio, Meta API)
    # For now, we return the structured payload that the dashboard or widget can use to trigger an URL redirect or SMS alert.
    return {
        "status": "success",
        "message": "WhatsApp notification compiled successfully.",
        "payload": {
            "to_counsellor_number": "+917994721792",
            "message": message_content.strip()
        }
    }
