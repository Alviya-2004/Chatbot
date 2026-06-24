from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import re
import os
from dotenv import load_dotenv

load_dotenv()

from groq import Groq
import markdown
import json

# Initialize Groq Client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Initialize FastAPI
app = FastAPI(
    title="CarePilot AI Backend",
    description="Backend for Portfolio Builders AI Chatbot",
    version="1.0.0"
)

# Allow CORS for React widget
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models ---
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

# --- Lead Scoring System ---
def evaluate_lead_score(message: str, current_score: int, current_page_url: str = "") -> int:
    msg_lower = message.lower()
    score = current_score
    
    # +30: Asked for counselor
    if any(kw in msg_lower for kw in ["counselor", "counsellor", "call", "talk to human", "schedule a call"]):
        score += 30
    # +25: Shared phone number (Basic regex)
    if re.search(r'\b\d{10}\b', message):
        score += 25
    # +20: Asked for WhatsApp
    if any(kw in msg_lower for kw in ["whatsapp", "wa.me", "wp"]):
        score += 20
    # +15: Asked about fee
    if any(kw in msg_lower for kw in ["fee", "cost", "price", "charge", "emi"]):
        score += 15
    # +15: Asked about batch date
    if any(kw in msg_lower for kw in ["batch", "date", "when does it start", "start date"]):
        score += 15
    # +10: Asked about course
    if any(kw in msg_lower for kw in ["course", "learn", "syllabus", "program"]):
        score += 10
    # +10: Asked about placement
    if any(kw in msg_lower for kw in ["placement", "job", "hiring", "guarantee"]):
        score += 10
    # +10: Asked about certificate
    if any(kw in msg_lower for kw in ["certificate", "validity", "approved"]):
        score += 10
    # +10: Visited pricing page
    if current_page_url and "pricing" in current_page_url.lower():
        score += 10
        
    return min(score, 100) # Cap at 100

def get_lead_category(score: int) -> str:
    if score <= 30: return "Cold lead"
    elif score <= 60: return "Warm lead"
    elif score <= 80: return "Hot lead"
    else: return "High priority lead"

# --- Custom Knowledge Base ---
documents = []

@app.on_event("startup")
def load_knowledge_base():
    global documents
    print("Loading Knowledge Base from structured data...")
    try:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        for root, dirs, files in os.walk(data_dir):
            for file in files:
                if file.endswith(".md"):
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        content = f.read()
                        documents.append({
                            "content": content,
                            "path": os.path.join(root, file),
                            "category": "courses" if "courses" in root else "general"
                        })
        print(f"Loaded {len(documents)} documents successfully.")
    except Exception as e:
        print(f"Warning: Could not load knowledge base: {e}")

def get_relevant_context(query: str, category_filter: str = None) -> str:
    # Simple keyword search for the MVP
    query_words = set(query.lower().split())
    matches = []
    for doc in documents:
        if category_filter and doc["category"] != category_filter:
            continue
        score = sum(1 for word in query_words if word in doc["content"].lower())
        if score > 0:
            matches.append((score, doc["content"]))
    
    matches.sort(key=lambda x: x[0], reverse=True)
    return "\n\n".join([m[1] for m in matches[:3]])



# --- Endpoints ---
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    # 1. Update Score & Category
    new_score = evaluate_lead_score(req.message, req.current_score, req.current_page_url or "")
    category = get_lead_category(new_score)
    
    # Trigger form if Warm lead or above (score > 30)
    trigger_form = new_score > 30 
    
    # 2. Retrieval
    category_filter = None
    if req.current_page_url:
        if "course" in req.current_page_url.lower():
            category_filter = "courses"
        elif "internship" in req.current_page_url.lower():
            category_filter = "internships"

    context = get_relevant_context(req.message, category_filter)
    
    # 3. Groq Chat Completion with Refined Prompt
    prompt = f"""
You are CarePilot AI, the official AI assistant of Portfolio Builders.
Your goal is to provide VERY CONCISE answers based ONLY on the provided context.

RULES:
1. Use ONLY the information in the 'Context information' section.
2. If the answer is not in the context, say: "I'm sorry, I don't have that specific information right now. Please chat with us on WhatsApp at +91 7994721792 for more details!"
3. Keep answers under 3-4 sentences. Use bullet points if listing items.
4. Be professional and warm, but direct.

Context information:
---------------------
{context}
---------------------

Query: {req.message}
Answer:"""

    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )
        reply = completion.choices[0].message.content
    except Exception as e:
        reply = f"I'm having trouble connecting to my brain right now. Error: {str(e)}"
    
    return ChatResponse(
        reply=reply,
        new_score=new_score,
        lead_category=category,
        trigger_form=trigger_form
    )

if __name__ == "__main__":
    import uvicorn
    # Make sure to run this using: uvicorn backend.main:app --reload
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
