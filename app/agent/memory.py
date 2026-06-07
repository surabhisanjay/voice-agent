"""
Conversation memory management.
"""
import logging
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import ChatMessage, ChatSession
from app.database import get_db
from app.config import settings
import uuid

logger = logging.getLogger(__name__)


class ConversationMemory:
    """Manage conversation history and context."""

    def __init__(self, session_id: str, db: Session):
        """Initialize conversation memory."""
        self.session_id = session_id
        self.db = db
        self.messages: List[dict] = []
        self._load_history()

    def _load_history(self):
        """Load conversation history from database."""
        messages = self.db.query(ChatMessage).filter(
            ChatMessage.session_id == self.session_id
        ).order_by(ChatMessage.timestamp).limit(settings.max_conversation_history).all()

        self.messages = [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
                "confidence_score": msg.confidence_score
            }
            for msg in messages
        ]
        logger.info(f"Loaded {len(self.messages)} messages for session {self.session_id}")

    def add_message(self, role: str, content: str, confidence_score: Optional[float] = None,
                   retrieved_documents: Optional[str] = None):
        """Add message to memory."""
        msg_id = str(uuid.uuid4())
        message = ChatMessage(
            id=msg_id,
            session_id=self.session_id,
            role=role,
            content=content,
            timestamp=datetime.utcnow(),
            confidence_score=confidence_score,
            retrieved_documents=retrieved_documents
        )
        self.db.add(message)
        self.db.commit()

        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "confidence_score": confidence_score
        })
        logger.info(f"Added {role} message to session {self.session_id}")

    def get_history(self, max_messages: Optional[int] = None) -> List[dict]:
        """Get conversation history."""
        limit = max_messages or settings.max_conversation_history
        return self.messages[-limit:]

    def get_context_string(self) -> str:
        """Get conversation history as formatted string for LLM."""
        if not self.messages:
            return ""

        context = "Previous conversation:\n"
        for msg in self.messages[-5:]:  # Last 5 messages
            context += f"{msg['role'].upper()}: {msg['content']}\n"
        return context

    def clear(self):
        """Clear conversation memory."""
        self.messages = []
        logger.info(f"Cleared memory for session {self.session_id}")


def create_session(customer_id: str, db: Session) -> str:
    """Create a new chat session."""
    session_id = str(uuid.uuid4())
    session = ChatSession(
        id=session_id,
        customer_id=customer_id,
        status="active"
    )
    db.add(session)
    db.commit()
    logger.info(f"Created new session {session_id} for customer {customer_id}")
    return session_id


def get_or_create_memory(session_id: str, customer_id: str, db: Session) -> ConversationMemory:
    """Get existing memory or create new session."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()

    if not session:
        session_id = create_session(customer_id, db)

    return ConversationMemory(session_id, db)
