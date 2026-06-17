from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import re
import os
from dotenv import load_dotenv

import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import VectorStoreIndex
from llama_index.core.vector_stores import ExactMatchFilter, MetadataFilters
from llama_index.core.prompts import PromptTemplate

# Load environment variables (e.g., OPENAI_API_KEY)
load_dotenv()

app = FastAPI(
    title="Portfolio Builders Backend",
    description="AI Career Counsellor, Admission Assistant, and Lead Engine API",
    version="1.0.0"
)

# --- Pydantic Models ---

class ChatRequest(BaseModel):
    session_id: str
    message: str
    user_persona: Optional[str] = None
    current_score: int = 0

class ChatResponse(BaseModel):
    reply: str
    new_score: int
    trigger_form: bool

# --- Lead Scoring Logic ---

def calculate_score(message: str, current_score: int) -> int:
    """
    Rigid evaluation function to calculate lead priority based purely on the point system.
    Returns the accumulated score.
    """
    msg_lower = message.lower()
    score_increment = 0
    
    # Asked for counsel call: +30
    if any(kw in msg_lower for kw in ["counsel", "counselor", "counsellor", "call", "schedule a call"]):
        score_increment += 30
        
    # Shared phone number: +25
    # Regex to match 10 digit numbers or generic phone number formats
    phone_pattern = re.compile(r'\b\d{10}\b|\+?\d{1,3}[-\.\s]?\(?\d{1,4}?\)[-\.\s]?\d{1,4}[-\.\s]?\d{1,9}\b')
    if phone_pattern.search(message): # Search original message to keep formatting
        score_increment += 25
        
    # Asked for WhatsApp link: +20
    if any(kw in msg_lower for kw in ["whatsapp", "wa.me", "wp"]):
        score_increment += 20
        
    # Asked about fee: +5
    if any(kw in msg_lower for kw in ["fee", "cost", "price", "charge"]):
        score_increment += 5
        
    # Asked about batch date: +5
    if any(kw in msg_lower for kw in ["batch", "date", "when does it start", "start date", "schedule"]):
        score_increment += 5
        
    # The following are explicitly +0 points according to requirements
    # Asked about course: +0
    # Asked about placement: +0
    # Asked about certificate: +0
    # Visited pricing page: +0
    # Repeated questions about same program: +0
    
    return current_score + score_increment

# --- LlamaIndex Setup ---

def get_index():
    """
    Load the ChromaDB index. 
    In a real app, you might want to cache this globally to avoid reloading on every request.
    """
    try:
        db = chromadb.PersistentClient(path="./chroma_db")
        chroma_collection = db.get_collection("portfolio_builders")
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        return VectorStoreIndex.from_vector_store(vector_store=vector_store)
    except Exception as e:
        print(f"Error loading VectorStoreIndex: {e}")
        return None

# Template to force strict RAG behavior
QA_PROMPT_TMPL = (
    "You are an AI Career Counsellor and Admission Assistant for 'Portfolio Builders'.\n"
    "Context information is below.\n"
    "---------------------\n"
    "{context_str}\n"
    "---------------------\n"
    "Given the context information and no prior knowledge, answer the query.\n"
    "If the answer is not contained in the context, politely state that you do not have that information.\n"
    "Query: {query_str}\n"
    "Answer: "
)
qa_prompt = PromptTemplate(QA_PROMPT_TMPL)

# --- API Endpoints ---

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    # 1. Evaluate Lead Score
    new_score = calculate_score(req.message, req.current_score)
    
    # Check if trigger form condition is met (score >= 50)
    trigger_form = new_score >= 50
    
    # 2. Retrieve Answer using LlamaIndex
    index = get_index()
    if not index:
        return ChatResponse(
            reply="I'm currently unable to access the knowledge base. Please try again later.",
            new_score=new_score,
            trigger_form=trigger_form
        )
        
    # Build metadata filters to enforce fetching answers exclusively relevant to the user persona
    filters = None
    if req.user_persona:
        filters = MetadataFilters(
            filters=[ExactMatchFilter(key="persona", value=req.user_persona)]
        )
        
    query_engine = index.as_query_engine(
        filters=filters,
        text_qa_template=qa_prompt,
        similarity_top_k=3 # Fetch top 3 relevant chunks
    )
    
    try:
        response = query_engine.query(req.message)
        reply_text = str(response)
    except Exception as e:
        print(f"Query error: {e}")
        reply_text = "I'm sorry, I encountered an error while processing your request."
        
    return ChatResponse(
        reply=reply_text,
        new_score=new_score,
        trigger_form=trigger_form
    )

if __name__ == "__main__":
    import uvicorn
    # Run the application using uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
