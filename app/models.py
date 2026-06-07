"""
Database models for storing conversations and customer interactions.
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Text, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class ChatSession(Base):
    """Chat session model for tracking customer conversations."""

    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True, index=True)
    customer_id = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String, default="active")  # active, closed, escalated


class ChatMessage(Base):
    """Chat message model for storing conversation history."""

    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, index=True)
    role = Column(String)  # user or assistant
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    confidence_score = Column(Float, nullable=True)
    retrieved_documents = Column(Text, nullable=True)  # JSON list of doc IDs


class DocumentLog(Base):
    """Document log model for tracking document ingestion."""

    __tablename__ = "document_logs"

    id = Column(String, primary_key=True, index=True)
    document_name = Column(String, index=True)
    document_path = Column(String)
    ingested_at = Column(DateTime, default=datetime.utcnow)
    chunk_count = Column(Integer)
    vector_ids = Column(Text)  # JSON list of vector IDs


class EscalationLog(Base):
    """Escalation log model for tracking escalated queries."""

    __tablename__ = "escalation_logs"

    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, index=True)
    message_id = Column(String, index=True)
    reason = Column(String)  # low_confidence, no_documents_found, manual_request
    confidence_score = Column(Float)
    escalated_at = Column(DateTime, default=datetime.utcnow)
    resolved = Column(Boolean, default=False)
