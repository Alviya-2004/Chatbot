from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .db import Base

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(String, nullable=True)
    visitor_id = Column(String, nullable=True)
    source_page = Column(String, nullable=True)
    user_type = Column(String, nullable=True)  # beginner, switcher, final_year, etc.
    intent = Column(String, nullable=True)
    status = Column(String, default="active")  # active, completed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("chat_sessions.session_id"), nullable=False)
    sender = Column(String, nullable=False)  # user, ai, system
    message = Column(Text, nullable=False)
    intent = Column(String, nullable=True)
    confidence_score = Column(Float, nullable=True)
    source_used = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("ChatSession", back_populates="messages")

class Lead(Base):
    __tablename__ = "leads"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    email = Column(String, nullable=False)
    location = Column(String, nullable=True)
    current_status = Column(String, nullable=True)  # student, graduate, working professional, parent
    interested_program = Column(String, nullable=True)
    goal = Column(String, nullable=True)  # job, internship, portfolio review
    preferred_mode = Column(String, nullable=True)  # online, offline, hybrid
    urgency = Column(String, nullable=True)  # immediate, next 3 months, exploring
    lead_score = Column(Integer, default=0)
    lead_temperature = Column(String, default="Cold")  # Cold, Warm, Hot, High Priority
    source_page = Column(String, nullable=True)
    conversation_summary = Column(Text, nullable=True)
    assigned_to = Column(String, nullable=True)
    status = Column(String, default="New")  # New, Contacted, Enrolled, Junk
    created_at = Column(DateTime, default=datetime.utcnow)

class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    source_type = Column(String, nullable=False)  # file, url, manual
    source_url = Column(String, nullable=True)
    file_url = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    status = Column(String, default="approved")  # draft, approved
    approved_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    chunks = relationship("KnowledgeChunk", back_populates="document", cascade="all, delete-orphan")

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("knowledge_documents.id"), nullable=False)
    chunk_text = Column(Text, nullable=False)
    chunk_metadata = Column(Text, nullable=True)  # JSON string of chunk metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    document = relationship("KnowledgeDocument", back_populates="chunks")

class BotFallback(Base):
    __tablename__ = "bot_fallbacks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_question = Column(Text, nullable=False)
    bot_response = Column(Text, nullable=False)
    confidence_score = Column(Float, nullable=True)
    session_id = Column(String, nullable=True)
    resolved_status = Column(String, default="unresolved")  # unresolved, resolved
    admin_answer = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class RecommendationLog(Base):
    __tablename__ = "recommendation_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, nullable=False)
    user_type = Column(String, nullable=False)
    detected_goal = Column(String, nullable=False)
    recommended_program = Column(String, nullable=False)
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class BotAnalytics(Base):
    __tablename__ = "bot_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, unique=True, index=True, nullable=False)  # YYYY-MM-DD
    total_chats = Column(Integer, default=0)
    total_leads = Column(Integer, default=0)
    hot_leads = Column(Integer, default=0)
    whatsapp_clicks = Column(Integer, default=0)
    unanswered_questions = Column(Integer, default=0)
    conversion_rate = Column(Float, default=0.0)
