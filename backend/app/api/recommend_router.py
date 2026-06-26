from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json

from ..database.db import get_db
from ..database.models import RecommendationLog, ChatSession, ChatMessage
from ..services.llm_service import llm_service
from pydantic import BaseModel
from typing import Optional, Dict

router = APIRouter(prefix="/api/recommend", tags=["Recommendations"])

# --- Pydantic Models ---
class RecommendRequest(BaseModel):
    session_id: str
    user_profile: Dict[str, str]  # status, interested_field, study_mode, skill_level, location
    user_goal: str

class RecommendationResponse(BaseModel):
    recommended_program: str
    reason: str
    next_question: str
    lead_capture_needed: bool
    cta: str

# --- Program List Helper ---
AVAILABLE_PROGRAMS = """
1. UI/UX Portfolio Building Program: 3 months, live online design fundamentals, Figma, SaaS project, portfolio creation. Validated by Kochi & Dubai recruiters.
2. Full Stack Development Course: Python/React based coding cohort with live projects.
3. Python Django Course: Backend focused programming.
4. Flutter Development Course: Cross-platform mobile development.
5. AI/ML Course: Modern machine learning and neural nets.
6. Digital Marketing Course: PPC, SEO, branding campaigns.
7. Product Management Course: PRDs, wireframing, agile delivery.
8. AICTE Internship: AICTE-approved academic internship for Indian engineering/technical degrees.
9. FYUGP Internship: Kerala FYUGP structure compliant internship.
10. MBA/BBA Marketing Internship: Hands-on business dev and marketing.
11. ₹10 Crore Scholarship Program: Fee reduction program for eligible students.
12. Free Portfolio/Resume Review: Submit current files for senior design critique.
"""

# --- Endpoints ---

@router.post("/program", response_model=RecommendationResponse)
async def recommend_program(req: RecommendRequest, db: Session = Depends(get_db)):
    # 1. Compile conversation history if available
    history_messages = db.query(ChatMessage).filter(ChatMessage.session_id == req.session_id).order_by(ChatMessage.created_at.asc()).all()
    summary = " ".join([f"{msg.sender.upper()}: {msg.message}" for msg in history_messages[-6:]]) if history_messages else "No chat history."

    # 2. Build Prompt Template (Section 16)
    prompt = f"""
Recommend the best next step or program from the list of available Portfolio Builders options.
You MUST output ONLY a valid JSON object matching the exact schema below. Do not add markdown wrapping or other text.

Available Portfolio Builders programs:
{AVAILABLE_PROGRAMS}

User profile:
{json.dumps(req.user_profile, indent=2)}

Conversation summary:
{summary}

User goal:
{req.user_goal}

Response JSON Schema:
{{
  "recommended_program": "Name of the program recommended",
  "reason": "Detailed explanation of why this program matches the user's profile and goal",
  "next_question": "A friendly follow-up question to keep the conversation going",
  "lead_capture_needed": true or false,
  "cta": "WhatsApp / Call Counsellor / Application Form link"
}}

Answer:"""

    raw_reply = llm_service.generate_reply(prompt)
    
    # Try parsing response as JSON
    try:
        # Strip potential markdown code block markers
        clean_reply = raw_reply.strip()
        if clean_reply.startswith("```json"):
            clean_reply = clean_reply[7:]
        if clean_reply.endswith("```"):
            clean_reply = clean_reply[:-3]
        clean_reply = clean_reply.strip()
        
        parsed_rec = json.loads(clean_reply)
    except Exception as e:
        print(f"Error parsing recommendation JSON output: {e}. Raw response: {raw_reply}")
        # Fallback response
        parsed_rec = {
            "recommended_program": "UI/UX Portfolio Building Program",
            "reason": "Based on your interest in launching a career, our flagship portfolio program provides structured mentor support.",
            "next_question": "Would you like me to share the detailed syllabus and class times with you?",
            "lead_capture_needed": True,
            "cta": "WhatsApp"
        }

    # 3. Log Recommendation in SQLite
    log_entry = RecommendationLog(
        session_id=req.session_id,
        user_type=req.user_profile.get("status", "unknown"),
        detected_goal=req.user_goal,
        recommended_program=parsed_rec.get("recommended_program", ""),
        reason=parsed_rec.get("reason", "")
    )
    db.add(log_entry)
    
    # Update session details with detected persona
    session = db.query(ChatSession).filter(ChatSession.session_id == req.session_id).first()
    if session:
        session.user_type = req.user_profile.get("status", "unknown")
        session.intent = req.user_goal
        
    db.commit()

    return RecommendationResponse(
        recommended_program=parsed_rec.get("recommended_program", ""),
        reason=parsed_rec.get("reason", ""),
        next_question=parsed_rec.get("next_question", ""),
        lead_capture_needed=parsed_rec.get("lead_capture_needed", True),
        cta=parsed_rec.get("cta", "WhatsApp")
    )

@router.post("/scholarship", response_model=RecommendationResponse)
async def recommend_scholarship(req: RecommendRequest, db: Session = Depends(get_db)):
    req.user_goal = "Explore scholarship eligibility and applications."
    return await recommend_program(req, db)

@router.post("/internship", response_model=RecommendationResponse)
async def recommend_internship(req: RecommendRequest, db: Session = Depends(get_db)):
    req.user_goal = "Explore academic / corporate internship programs (AICTE, FYUGP)."
    return await recommend_program(req, db)
