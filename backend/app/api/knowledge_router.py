from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from datetime import datetime
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from ..database.db import get_db
from ..database.models import KnowledgeDocument, KnowledgeChunk
from ..services.rag_service import rag_service
from llama_index.core import Document as LlamaDocument
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/api/admin/knowledge", tags=["Knowledge"])

# --- Pydantic Models ---
class URLRequest(BaseModel):
    url: str
    category: Optional[str] = "general"

class KnowledgeDocumentResponse(BaseModel):
    id: int
    title: str
    source_type: str
    source_url: Optional[str] = None
    file_url: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        orm_mode = True

# --- Helpers ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")

def index_document_in_rag(doc_id: int, title: str, content: str, category: str, source: str):
    """Index a single document in LlamaIndex / ChromaDB."""
    if not rag_service.index:
        print("RAG index not initialized. Skipping vector index injection.")
        return
        
    try:
        # Create LlamaIndex Document
        doc = LlamaDocument(
            text=content,
            metadata={
                "document_id": doc_id,
                "title": title,
                "category": category,
                "source": source
            }
        )
        
        # Insert document into ChromaDB index
        rag_service.index.insert_document(doc)
        print(f"Successfully indexed document #{doc_id} ('{title}') in ChromaDB.")
    except Exception as e:
        print(f"Error indexing document #{doc_id}: {e}")

# --- Endpoints ---

@router.get("", response_model=List[KnowledgeDocumentResponse])
async def list_knowledge(db: Session = Depends(get_db)):
    docs = db.query(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc()).all()
    return docs

@router.post("/upload", response_model=KnowledgeDocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form("general"),
    db: Session = Depends(get_db)
):
    # Determine save path
    category_dir = os.path.join(DATA_DIR, category)
    os.makedirs(category_dir, exist_ok=True)
    
    filepath = os.path.join(category_dir, file.filename)
    
    # Save file content locally
    try:
        content_bytes = await file.read()
        with open(filepath, "wb") as f:
            f.write(content_bytes)
        
        content_text = content_bytes.decode("utf-8", errors="ignore")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
        
    # Create DB entry
    db_doc = KnowledgeDocument(
        title=file.filename,
        source_type="file",
        file_url=filepath,
        content=content_text,
        status="approved"
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    
    # Index in vector store
    index_document_in_rag(
        doc_id=db_doc.id,
        title=db_doc.title,
        content=content_text,
        category=category,
        source=filepath
    )
    
    return db_doc

@router.post("/url", response_model=KnowledgeDocumentResponse)
async def add_knowledge_url(req: URLRequest, db: Session = Depends(get_db)):
    url = req.url
    category = req.category or "general"
    
    # Basic URL structure check
    parsed_url = urlparse(url)
    if not parsed_url.scheme or not parsed_url.netloc:
        raise HTTPException(status_code=400, detail="Invalid URL format.")
        
    # Crawl and parse URL content
    try:
        headers = {"User-Agent": "CarePilot AI Crawler"}
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {str(e)}")
        
    soup = BeautifulSoup(res.content, 'html.parser')
    
    # Extract title
    title_tag = soup.find('title')
    page_title = title_tag.get_text(strip=True) if title_tag else url
    
    # Remove script, style, nav, footer
    for element in soup(["script", "style", "nav", "footer", "noscript", "svg"]):
        element.extract()
        
    # Extract structural text
    text_content = []
    for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'ul', 'ol', 'table']):
        text = tag.get_text(separator=' ', strip=True)
        if text:
            text_content.append(text)
            
    final_content = "\n\n".join(text_content)
    
    # Create DB Entry
    db_doc = KnowledgeDocument(
        title=page_title,
        source_type="url",
        source_url=url,
        content=final_content,
        status="approved"
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    
    # Index in vector store
    index_document_in_rag(
        doc_id=db_doc.id,
        title=page_title,
        content=final_content,
        category=category,
        source=url
    )
    
    return db_doc

@router.delete("/{doc_id}")
async def delete_knowledge(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    # Delete from local file system if it is a file
    if doc.source_type == "file" and doc.file_url and os.path.exists(doc.file_url):
        try:
            os.remove(doc.file_url)
        except Exception as e:
            print(f"Warning: Could not remove local file {doc.file_url}: {e}")
            
    # Delete from Vector Store (ChromaDB)
    # LlamaIndex doesn't expose a straightforward delete-by-metadata on the index itself directly,
    # but we can filter or delete using the underlying chroma client collection
    if rag_service.chroma_collection:
        try:
            # Delete where metadata contains our doc id
            rag_service.chroma_collection.delete(where={"document_id": doc_id})
            print(f"Deleted document #{doc_id} chunks from ChromaDB.")
        except Exception as e:
            print(f"Warning: Could not delete chunks from ChromaDB: {e}")
            
    # Delete from SQLite
    db.delete(doc)
    db.commit()
    
    return {"status": "success", "message": "Document deleted successfully from DB and Vector Index."}

@router.post("/reindex")
async def trigger_reindex(db: Session = Depends(get_db)):
    """Wipe and rebuild vector store from all approved database documents."""
    if not rag_service.chroma_collection:
        raise HTTPException(status_code=500, detail="Chroma DB client is unavailable.")
        
    try:
        # 1. Clear Chroma collection
        # LlamaIndex doesn't clear the index in-memory directly, but we can reset the Chroma Collection
        db_client = rag_service.db
        db_client.delete_collection(rag_service.collection_name)
        rag_service.chroma_collection = db_client.get_or_create_collection(rag_service.collection_name)
        
        # Re-init index from empty collection
        rag_service._init_index()
        
        # 2. Fetch approved documents from relational DB
        docs = db.query(KnowledgeDocument).filter(KnowledgeDocument.status == "approved").all()
        
        # 3. Batch re-index
        for doc in docs:
            # Determine category based on filepath/url if possible
            category = "general"
            if doc.source_type == "file" and doc.file_url:
                parts = os.path.normpath(doc.file_url).split(os.sep)
                if len(parts) >= 2:
                    category = parts[-2]
            elif doc.source_url:
                if "/course" in doc.source_url.lower() or "/program" in doc.source_url.lower():
                    category = "courses"
                elif "/internship" in doc.source_url.lower():
                    category = "internships"
                    
            index_document_in_rag(
                doc_id=doc.id,
                title=doc.title,
                content=doc.content,
                category=category,
                source=doc.file_url or doc.source_url or "manual"
            )
            
        return {"status": "success", "message": f"Successfully reindexed {len(docs)} documents."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reindexing failed: {str(e)}")
