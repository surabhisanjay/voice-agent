"""
FastAPI application with voice endpoints for the Inbound Agent.
"""
import logging
import io
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.agent.inbound_agent import InboundVoiceAgent
from app.agent.memory import get_or_create_memory
from app.agent.voice_processor import FFMPEG_PATH, PIPER_PATH, get_speech_to_text, get_text_to_speech
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


class QueryRequest(BaseModel):
    """Request model for text queries."""

    session_id: Optional[str] = None
    customer_id: str
    query: str


class VoiceQueryRequest(BaseModel):
    """Request model for voice queries."""

    session_id: Optional[str] = None
    customer_id: str


class QueryResponse(BaseModel):
    """Response model."""

    session_id: str
    response: str
    confidence_score: float
    escalated: bool
    escalation_reason: Optional[str] = None


@router.post("/query", response_model=QueryResponse)
def query_text(request: QueryRequest, db: Session = Depends(get_db)):
    """Answer a text query."""
    try:
        # Initialize agent
        agent = InboundVoiceAgent(db)

        # Create or get session
        session_id = request.session_id or str(uuid.uuid4())
        memory = get_or_create_memory(session_id, request.customer_id, db)

        # Process query
        result = agent.process_query(request.query, session_id, memory)

        # Store message in memory
        memory.add_message(
            role="user",
            content=request.query,
            confidence_score=1.0
        )
        memory.add_message(
            role="assistant",
            content=result["response"],
            confidence_score=result["confidence_score"],
            retrieved_documents=",".join(result["retrieved_documents"][:3]) if result["retrieved_documents"] else None
        )

        return QueryResponse(
            session_id=session_id,
            response=result["response"],
            confidence_score=result["confidence_score"],
            escalated=result["should_escalate"],
            escalation_reason=result.get("escalation_reason")
        )

    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/voice-query")
def query_voice(
    customer_id: str = Form(...),
    audio_file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Answer a voice query with voice response."""
    try:
        # Initialize components
        agent = InboundVoiceAgent(db)
        stt = get_speech_to_text()
        tts = get_text_to_speech()

        if PIPER_PATH is None:
            logger.warning("Piper is unavailable; returning text-only voice response.")

        # Create or get session
        session_id = session_id or str(uuid.uuid4())
        memory = get_or_create_memory(session_id, customer_id, db)

        # Read audio file
        audio_data = audio_file.file.read()

        # Transcribe audio
        logger.info("Transcribing audio...")
        user_query, transcription_confidence, detected_language = stt.transcribe(audio_data)

        if detected_language and detected_language.lower() not in {"en", "eng", "english"}:
            logger.warning("Non-English audio detected: %s", detected_language)
            return {
                "session_id": session_id,
                "response": (
                    "Please speak in English only. "
                    "I can only handle English voice queries at this time."
                ),
                "confidence_score": 0.0,
                "escalated": False,
                "transcript": "",
            }

        if not user_query:
            # Return JSON fallback if transcription fails
            logger.warning("Transcription returned empty query")
            if FFMPEG_PATH is None:
                fallback_text = (
                    "Sorry, voice transcription is unavailable because ffmpeg is not installed "
                    "on the server. Please install ffmpeg or use text input."
                )
            else:
                fallback_text = (
                    "Sorry, I couldn't understand your voice message. "
                    "Please try again or contact a human representative."
                )
            return {
                "session_id": session_id,
                "response": fallback_text,
                "confidence_score": 0.0,
                "escalated": True,
                "transcript": ""
            }

        logger.info(f"Transcribed: {user_query}")

        # Process query
        result = agent.process_query(user_query, session_id, memory)

        # Store messages in memory
        memory.add_message("user", user_query, transcription_confidence)
        memory.add_message(
            "assistant",
            result["response"],
            result["confidence_score"],
            ",".join(result["retrieved_documents"][:3]) if result["retrieved_documents"] else None
        )

        # Synthesize response
        logger.info("Synthesizing speech...")
        if PIPER_PATH is None:
            logger.warning("Piper unavailable; returning text-only voice response.")
            return {
                "session_id": session_id,
                "response": result["response"],
                "confidence_score": result["confidence_score"],
                "escalated": result["should_escalate"],
                "transcript": user_query
            }

        try:
            response_audio = tts.synthesize(result["response"])
            if response_audio and len(response_audio) > 0:
                return StreamingResponse(
                    io.BytesIO(response_audio),
                    media_type="audio/wav",
                    headers={
                        "X-Session-ID": session_id,
                        "X-Confidence-Score": str(result["confidence_score"]),
                        "X-Escalated": str(result["should_escalate"]),
                        "X-Transcript": user_query
                    }
                )
            else:
                # Fallback to JSON response if TTS produced no audio
                return {
                    "session_id": session_id,
                    "response": result["response"],
                    "confidence_score": result["confidence_score"],
                    "escalated": result["should_escalate"],
                    "transcript": user_query
                }
        except Exception as tts_e:
            logger.error(f"TTS error: {tts_e}")
            # Return JSON fallback so client can use browser TTS
            return {
                "session_id": session_id,
                "response": result["response"],
                "confidence_score": result["confidence_score"],
                "escalated": result["should_escalate"],
                "transcript": user_query
            }

    except Exception as e:
        logger.error(f"Error processing voice query: {e}")
        # Return JSON fallback for voice clients
        fallback_text = (
            "Sorry, I'm currently unable to process your voice request. "
            "Please try again later or contact a human representative."
        )
        return {
            "session_id": session_id or str(uuid.uuid4()),
            "response": fallback_text,
            "confidence_score": 0.0,
            "escalated": True,
            "transcript": ""
        }


@router.get("/session/{session_id}/history")
def get_conversation_history(session_id: str, db: Session = Depends(get_db)):
    """Get conversation history for a session."""
    try:
        from app.models import ChatMessage

        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.timestamp).all()

        return {
            "session_id": session_id,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
                    "confidence_score": msg.confidence_score
                }
                for msg in messages
            ]
        }

    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
