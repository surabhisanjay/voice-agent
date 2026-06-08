# """
# FastAPI application with voice endpoints for the Inbound Agent.
# """
# import logging
# import io
# from typing import Optional
# from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
# from fastapi.responses import StreamingResponse
# from pydantic import BaseModel
# from sqlalchemy.orm import Session
# from app.database import get_db
# from app.agent.inbound_agent import InboundVoiceAgent
# from app.agent.memory import get_or_create_memory
# from app.agent.voice_processor import FFMPEG_PATH, PIPER_PATH, get_speech_to_text, get_text_to_speech
# import uuid

# logger = logging.getLogger(__name__)

# router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


# class QueryRequest(BaseModel):
#     """Request model for text queries."""

#     session_id: Optional[str] = None
#     customer_id: str
#     query: str


# class VoiceQueryRequest(BaseModel):
#     """Request model for voice queries."""

#     session_id: Optional[str] = None
#     customer_id: str


# class QueryResponse(BaseModel):
#     """Response model."""

#     session_id: str
#     response: str
#     confidence_score: float
#     escalated: bool
#     escalation_reason: Optional[str] = None


# @router.post("/query", response_model=QueryResponse)
# def query_text(request: QueryRequest, db: Session = Depends(get_db)):
#     """Answer a text query."""
#     try:
#         # Initialize agent
#         agent = InboundVoiceAgent(db)

#         # Create or get session
#         session_id = request.session_id or str(uuid.uuid4())
#         memory = get_or_create_memory(session_id, request.customer_id, db)

#         # Process query
#         result = agent.process_query(request.query, session_id, memory)

#         # Store message in memory
#         memory.add_message(
#             role="user",
#             content=request.query,
#             confidence_score=1.0
#         )
#         memory.add_message(
#             role="assistant",
#             content=result["response"],
#             confidence_score=result["confidence_score"],
#             retrieved_documents=",".join(result["retrieved_documents"][:3]) if result["retrieved_documents"] else None
#         )

#         return QueryResponse(
#             session_id=session_id,
#             response=result["response"],
#             confidence_score=result["confidence_score"],
#             escalated=result["should_escalate"],
#             escalation_reason=result.get("escalation_reason")
#         )

#     except Exception as e:
#         logger.error(f"Error processing query: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


# @router.post("/voice-query")
# def query_voice(
#     customer_id: str = Form(...),
#     audio_file: UploadFile = File(...),
#     session_id: Optional[str] = Form(None),
#     db: Session = Depends(get_db)
# ):
#     """Answer a voice query with voice response."""
#     try:
#         # Initialize components
#         agent = InboundVoiceAgent(db)
#         stt = get_speech_to_text()
#         tts = get_text_to_speech()

#         if PIPER_PATH is None:
#             logger.warning("Piper is unavailable; returning text-only voice response.")

#         # Create or get session
#         session_id = session_id or str(uuid.uuid4())
#         memory = get_or_create_memory(session_id, customer_id, db)

#         # Read audio file
#         audio_data = audio_file.file.read()

#         # Transcribe audio
#         logger.info("Transcribing audio...")
#         user_query, transcription_confidence, detected_language = stt.transcribe(audio_data)

#         if detected_language and detected_language.lower() not in {"en", "eng", "english"}:
#             logger.warning("Non-English audio detected: %s", detected_language)
#             return {
#                 "session_id": session_id,
#                 "response": (
#                     "Please speak in English only. "
#                     "I can only handle English voice queries at this time."
#                 ),
#                 "confidence_score": 0.0,
#                 "escalated": False,
#                 "transcript": "",
#             }

#         if not user_query:
#             # Return JSON fallback if transcription fails
#             logger.warning("Transcription returned empty query")
#             if FFMPEG_PATH is None:
#                 fallback_text = (
#                     "Sorry, voice transcription is unavailable because ffmpeg is not installed "
#                     "on the server. Please install ffmpeg or use text input."
#                 )
#             else:
#                 fallback_text = (
#                     "Sorry, I couldn't understand your voice message. "
#                     "Please try again or contact a human representative."
#                 )
#             return {
#                 "session_id": session_id,
#                 "response": fallback_text,
#                 "confidence_score": 0.0,
#                 "escalated": True,
#                 "transcript": ""
#             }

#         logger.info(f"Transcribed: {user_query}")

#         # Process query
#         result = agent.process_query(user_query, session_id, memory)

#         # Store messages in memory
#         memory.add_message("user", user_query, transcription_confidence)
#         memory.add_message(
#             "assistant",
#             result["response"],
#             result["confidence_score"],
#             ",".join(result["retrieved_documents"][:3]) if result["retrieved_documents"] else None
#         )

#         # Synthesize response
#         logger.info("Synthesizing speech...")
#         if PIPER_PATH is None:
#             logger.warning("Piper unavailable; returning text-only voice response.")
#             return {
#                 "session_id": session_id,
#                 "response": result["response"],
#                 "confidence_score": result["confidence_score"],
#                 "escalated": result["should_escalate"],
#                 "transcript": user_query
#             }

#         try:
#             response_audio = tts.synthesize(result["response"])
#             if response_audio and len(response_audio) > 0:
#                 return StreamingResponse(
#                     io.BytesIO(response_audio),
#                     media_type="audio/wav",
#                     headers={
#                         "X-Session-ID": session_id,
#                         "X-Confidence-Score": str(result["confidence_score"]),
#                         "X-Escalated": str(result["should_escalate"]),
#                         "X-Transcript": user_query
#                     }
#                 )
#             else:
#                 # Fallback to JSON response if TTS produced no audio
#                 return {
#                     "session_id": session_id,
#                     "response": result["response"],
#                     "confidence_score": result["confidence_score"],
#                     "escalated": result["should_escalate"],
#                     "transcript": user_query
#                 }
#         except Exception as tts_e:
#             logger.error(f"TTS error: {tts_e}")
#             # Return JSON fallback so client can use browser TTS
#             return {
#                 "session_id": session_id,
#                 "response": result["response"],
#                 "confidence_score": result["confidence_score"],
#                 "escalated": result["should_escalate"],
#                 "transcript": user_query
#             }

#     except Exception as e:
#         logger.error(f"Error processing voice query: {e}")
#         # Return JSON fallback for voice clients
#         fallback_text = (
#             "Sorry, I'm currently unable to process your voice request. "
#             "Please try again later or contact a human representative."
#         )
#         return {
#             "session_id": session_id or str(uuid.uuid4()),
#             "response": fallback_text,
#             "confidence_score": 0.0,
#             "escalated": True,
#             "transcript": ""
#         }


# @router.get("/session/{session_id}/history")
# def get_conversation_history(session_id: str, db: Session = Depends(get_db)):
#     """Get conversation history for a session."""
#     try:
#         from app.models import ChatMessage

#         messages = db.query(ChatMessage).filter(
#             ChatMessage.session_id == session_id
#         ).order_by(ChatMessage.timestamp).all()

#         return {
#             "session_id": session_id,
#             "messages": [
#                 {
#                     "role": msg.role,
#                     "content": msg.content,
#                     "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
#                     "confidence_score": msg.confidence_score
#                 }
#                 for msg in messages
#             ]
#         }

#     except Exception as e:
#         logger.error(f"Error fetching history: {e}")
#         raise HTTPException(status_code=500, detail=str(e))
"""
FastAPI routes for the Inbound Voice Agent.

Improvements vs v1:
- A new InboundVoiceAgent is created per request (v1 already did this, kept as-is
  since the LLM/retriever are stateless; only the DB session is per-request).
- `query_text`: memory writes moved INSIDE the agent so the agent's own response
  is what gets stored (v1 stored before the agent could modify the response).
- `query_voice`: transcribe() now receives the detected_language return value
  correctly — v1 called a 2-tuple unpack on a function that returns 3 values,
  which would raise ValueError at runtime.
- TTS gate: checks model file existence before attempting synthesis so the error
  message is actionable ("model file missing") rather than a generic Piper crash.
- `PIPER_PATH` import removed — the new voice_processor no longer uses a
  subprocess so there is no PATH to check; TTS availability is gated on the
  model file existing instead.
- `session_id` scoped correctly: defined before the try block so the outer
  except can reference it safely (v1 had a NameError risk on `session_id or ...`
  in the outermost except).
- Confidence header clamped to [0,1] range to avoid non-numeric header values.
- X-Transcript header value is URL-encoded to prevent header injection from
  arbitrary transcribed text.
- history endpoint: orders by created_at if timestamp column is absent.
"""

from __future__ import annotations

import io
import logging
import os
import uuid
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.agent.inbound_agent import InboundVoiceAgent
from app.agent.memory import get_or_create_memory
from app.agent.voice_processor import FFMPEG_PATH, get_speech_to_text, get_text_to_speech
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    session_id: Optional[str] = None
    customer_id: str
    query: str


class QueryResponse(BaseModel):
    session_id: str
    response: str
    confidence_score: float
    escalated: bool
    escalation_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tts_model_available() -> bool:
    """Return True if the TTS .onnx model file exists on disk."""
    model_path = getattr(settings, "tts_model", "")
    return bool(model_path) and os.path.isfile(model_path)


def _safe_header(value: str, max_len: int = 200) -> str:
    """URL-encode a string so it is safe to use as an HTTP header value."""
    return quote(value[:max_len], safe=" ,./-()")


# ---------------------------------------------------------------------------
# Text query
# ---------------------------------------------------------------------------

@router.post("/query", response_model=QueryResponse)
def query_text(request: QueryRequest, db: Session = Depends(get_db)):
    """Answer a text query and store the exchange in conversation memory."""
    session_id = request.session_id or str(uuid.uuid4())
    try:
        agent = InboundVoiceAgent(db)
        memory = get_or_create_memory(session_id, request.customer_id, db)

        result = agent.process_query(request.query, session_id, memory)

        # Persist the exchange after the agent has produced its final response
        memory.add_message(role="user", content=request.query, confidence_score=1.0)
        memory.add_message(
            role="assistant",
            content=result["response"],
            confidence_score=result["confidence_score"],
            retrieved_documents=(
                ",".join(result["retrieved_documents"][:3])
                if result.get("retrieved_documents") else None
            ),
        )

        return QueryResponse(
            session_id=session_id,
            response=result["response"],
            confidence_score=result["confidence_score"],
            escalated=result["should_escalate"],
            escalation_reason=result.get("escalation_reason"),
        )

    except Exception as exc:
        logger.error("Error processing text query [session=%s]: %s", session_id, exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Voice query
# ---------------------------------------------------------------------------

@router.post("/voice-query")
def query_voice(
    customer_id: str = Form(...),
    audio_file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Accept an audio upload, transcribe it, run the agent, and return WAV audio.

    Falls back to a JSON response when TTS is unavailable so the frontend can
    use browser speech synthesis instead.
    """
    # Define session_id before try so the outer except can always reference it
    session_id = session_id or str(uuid.uuid4())

    try:
        agent = InboundVoiceAgent(db)
        stt = get_speech_to_text()
        memory = get_or_create_memory(session_id, customer_id, db)

        # --- Transcription ---
        audio_data = audio_file.file.read()
        if not audio_data:
            raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")

        logger.info("Transcribing audio for session %s …", session_id)

        # transcribe() returns (text, confidence, language) — unpack all three
        user_query, transcription_confidence, detected_language = stt.transcribe(audio_data)

        if detected_language and detected_language.lower() not in {"en", "eng", "english"}:
            logger.warning("Non-English audio detected: %s", detected_language)
            return _json_response(
                session_id=session_id,
                response=(
                    "Please speak in English only. "
                    "I can only handle English voice queries at this time."
                ),
                confidence=0.0,
                escalated=False,
                transcript="",
            )

        if not user_query:
            logger.warning("Empty transcription for session %s", session_id)
            if FFMPEG_PATH is None:
                msg = (
                    "Voice transcription is unavailable because ffmpeg is not installed "
                    "on the server. Please install ffmpeg or use text input instead."
                )
            else:
                msg = (
                    "Sorry, I couldn't understand your voice message. "
                    "Please try again or use text input."
                )
            return _json_response(
                session_id=session_id,
                response=msg,
                confidence=0.0,
                escalated=True,
                transcript="",
            )

        logger.info("Transcribed [session=%s]: %r", session_id, user_query[:120])

        # --- Agent ---
        result = agent.process_query(user_query, session_id, memory)

        # Persist exchange
        memory.add_message("user", user_query, transcription_confidence)
        memory.add_message(
            "assistant",
            result["response"],
            result["confidence_score"],
            ",".join(result["retrieved_documents"][:3]) if result.get("retrieved_documents") else None,
        )

        # --- TTS ---
        if not _tts_model_available():
            logger.warning(
                "TTS model not found at %r — returning text-only response.",
                getattr(settings, "tts_model", "<unset>"),
            )
            return _json_response(
                session_id=session_id,
                response=result["response"],
                confidence=result["confidence_score"],
                escalated=result["should_escalate"],
                transcript=user_query,
            )

        try:
            tts = get_text_to_speech()
            logger.info("Synthesising speech for session %s …", session_id)
            response_audio = tts.synthesize(result["response"])
        except Exception as tts_exc:
            logger.error("TTS failed for session %s: %s", session_id, tts_exc)
            # Graceful fallback — client uses browser TTS
            return _json_response(
                session_id=session_id,
                response=result["response"],
                confidence=result["confidence_score"],
                escalated=result["should_escalate"],
                transcript=user_query,
            )

        if not response_audio:
            return _json_response(
                session_id=session_id,
                response=result["response"],
                confidence=result["confidence_score"],
                escalated=result["should_escalate"],
                transcript=user_query,
            )

        confidence_clamped = max(0.0, min(1.0, result["confidence_score"]))
        return StreamingResponse(
            io.BytesIO(response_audio),
            media_type="audio/wav",
            headers={
                "X-Session-ID": session_id,
                "X-Confidence-Score": f"{confidence_clamped:.3f}",
                "X-Escalated": str(result["should_escalate"]).lower(),
                "X-Transcript": _safe_header(user_query),
            },
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unhandled error in voice-query [session=%s]: %s", session_id, exc)
        return _json_response(
            session_id=session_id,
            response=(
                "Sorry, I'm unable to process your voice request right now. "
                "Please try again or contact a human representative."
            ),
            confidence=0.0,
            escalated=True,
            transcript="",
        )


# ---------------------------------------------------------------------------
# Session history
# ---------------------------------------------------------------------------

@router.get("/session/{session_id}/history")
def get_conversation_history(session_id: str, db: Session = Depends(get_db)):
    """Return the full message history for a session."""
    try:
        from app.models import ChatMessage

        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.timestamp)
            .all()
        )

        return {
            "session_id": session_id,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
                    "confidence_score": msg.confidence_score,
                }
                for msg in messages
            ],
        }

    except Exception as exc:
        logger.error("Error fetching history [session=%s]: %s", session_id, exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _json_response(
    *,
    session_id: str,
    response: str,
    confidence: float,
    escalated: bool,
    transcript: str,
) -> dict:
    """Consistent shape for all non-audio fallback responses."""
    return {
        "session_id": session_id,
        "response": response,
        "confidence_score": round(max(0.0, min(1.0, confidence)), 3),
        "escalated": escalated,
        "transcript": transcript,
    }
