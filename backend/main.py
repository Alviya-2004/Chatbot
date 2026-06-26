from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

load_dotenv()

# Import DB configurations and schemas
from app.database.db import engine, Base, get_db
from app.database.models import KnowledgeDocument

# Import RAG services
from app.services.rag_service import rag_service
from app.api.knowledge_router import index_document_in_rag

# Import API Routers
from app.api.chat_router import router as chat_router
from app.api.leads_router import router as leads_router
from app.api.knowledge_router import router as knowledge_router
from app.api.analytics_router import router as analytics_router
from app.api.recommend_router import router as recommend_router

# Initialize Database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI App
app = FastAPI(
    title="CarePilot AI Backend",
    description="Production-Ready Modular Backend for Portfolio Builders AI Chatbot",
    version="1.0.0"
)

# Enable CORS for frontend widgets
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(chat_router)
app.include_router(leads_router)
app.include_router(knowledge_router)
app.include_router(analytics_router)
app.include_router(recommend_router)

# Seed Local Markdown files into DB and Vector Store on Startup
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

def seed_knowledge_base():
    db = next(get_db())
    try:
        if db.query(KnowledgeDocument).count() > 0:
            print("Knowledge base already seeded in DB.")
            return
            
        print("Knowledge base is empty. Seeding from local data/ directory...")
        if not os.path.exists(DATA_DIR):
            print(f"Warning: data directory not found at {DATA_DIR}")
            return
            
        seeded_count = 0
        for root, dirs, files in os.walk(DATA_DIR):
            for file in files:
                if file.endswith((".md", ".txt")):
                    filepath = os.path.join(root, file)
                    # Deduce category from folder name
                    category = "general"
                    if "courses" in root:
                        category = "courses"
                    elif "internships" in root:
                        category = "internships"
                        
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            content = f.read()
                            
                        # Save document record in SQLite
                        doc = KnowledgeDocument(
                            title=file,
                            source_type="file",
                            file_url=filepath,
                            content=content,
                            status="approved"
                        )
                        db.add(doc)
                        db.commit()
                        db.refresh(doc)
                        
                        # Index in ChromaDB Vector Database
                        index_document_in_rag(
                            doc_id=doc.id,
                            title=file,
                            content=content,
                            category=category,
                            source=filepath
                        )
                        seeded_count += 1
                    except Exception as e:
                        print(f"Failed to seed file {file}: {e}")
                        
        print(f"Seeding completed. Ingested {seeded_count} documents.")
    except Exception as e:
        print(f"Error during knowledge base seeding: {e}")
    finally:
        db.close()

@app.on_event("startup")
def startup_event():
    # Make sure we seed documents into vector database
    seed_knowledge_base()

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "CarePilot AI Backend",
        "documentation": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
