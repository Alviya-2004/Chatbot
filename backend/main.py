from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import re
import os
from dotenv import load_dotenv

load_dotenv()

from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter
from llama_index.core.prompts import PromptTemplate
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.groq import Groq

# Configure LlamaIndex to use Free Models
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
Settings.llm = Groq(model="llama3-8b-8192")

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

# --- LlamaIndex Setup ---
# Instead of ChromaDB connecting to a complex cluster for MVP, we load the structured markdown directly.
# LlamaIndex will automatically read the metadata from the top of the markdown files!
index = None

@app.on_event("startup")
def load_knowledge_base():
    global index
    print("Loading Knowledge Base from structured data...")
    try:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        
        # SimpleDirectoryReader reads the Markdown Frontmatter automatically
        reader = SimpleDirectoryReader(input_dir=data_dir, recursive=True, required_exts=[".md"])
        documents = reader.load_data()
        
        # Build Vector Index in-memory for the MVP (can be swapped to ChromaDB easily)
        index = VectorStoreIndex.from_documents(documents)
        print(f"Loaded {len(documents)} document chunks successfully.")
    except Exception as e:
        print(f"Warning: Could not load knowledge base: {e}")

# Strict RAG Prompt
QA_PROMPT = PromptTemplate(
    "You are CarePilot AI, the official AI career assistant of Portfolio Builders.\n"
    "Your role is to help students, parents, and professionals choose the right course, internship, or scholarship.\n"
    "Context information is below.\n"
    "---------------------\n"
    "{context_str}\n"
    "---------------------\n"
    "Given the context above, answer the query warmly and clearly. Do not invent fees, batch dates, or guarantees.\n"
    "If you are unsure, say you will connect them to a counsellor.\n"
    "Query: {query_str}\n"
    "Answer: "
)

# --- Endpoints ---
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    # 1. Update Score & Category
    new_score = evaluate_lead_score(req.message, req.current_score, req.current_page_url or "")
    category = get_lead_category(new_score)
    
    # Trigger form if Warm lead or above (score > 30)
    trigger_form = new_score > 30 
    
    # 2. RAG Retrieval
    if not index:
        return ChatResponse(
            reply="I'm still setting up my knowledge base. Please try again in a moment!",
            new_score=new_score,
            lead_category=category,
            trigger_form=trigger_form
        )
        
    # Build Metadata Filters based on context
    filters = None
    if req.current_page_url:
        if "course" in req.current_page_url.lower():
            filters = MetadataFilters(filters=[ExactMatchFilter(key="category", value="courses")])
        elif "internship" in req.current_page_url.lower():
            filters = MetadataFilters(filters=[ExactMatchFilter(key="category", value="internships")])

    query_engine = index.as_query_engine(
        filters=filters,
        text_qa_template=QA_PROMPT,
        similarity_top_k=3
    )
    
    context_query = f"[User is browsing: {req.current_page_url}] User says: {req.message}"
    response = query_engine.query(context_query)
    
    return ChatResponse(
        reply=str(response),
        new_score=new_score,
        lead_category=category,
        trigger_form=trigger_form
    )

if __name__ == "__main__":
    import uvicorn
    # Make sure to run this using: uvicorn backend.main:app --reload
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
