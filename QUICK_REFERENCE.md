# Quick Reference Guide

## ⚡ Start Server (60 seconds)
```bash
cd /Users/chandrikasanjay/voice_agent
TMPDIR=$(pwd)/.tmp uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
✅ Server runs at: `http://localhost:8000`  
✅ UI at: `http://localhost:8000/ui`

---

## 🎯 API Endpoints

### Text Query
```bash
curl -X POST http://localhost:8000/api/v1/agent/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is your pricing?",
    "customer_id": "cust-001"
  }'
```

### Voice Query
```bash
curl -X POST http://localhost:8000/api/v1/agent/voice-query \
  -F "audio_file=@audio.wav" \
  -F "customer_id=cust-001"
```

### Session History
```bash
curl http://localhost:8000/api/v1/agent/session/{session_id}/history
```

### Ingest Documents
```bash
curl -X POST http://localhost:8000/api/v1/documents/ingest
```

---

## 🎤 Web UI

**URL:** `http://localhost:8000/ui`

**Features:**
- 🎙️ Voice Recording → STT → Agent → TTS/Browser TTS
- 📝 Text Input → Agent → Response
- 📊 Session Info (confidence, escalation status)
- 🔗 Real-time browser TTS fallback

---

## 🔧 Essential Environment Variables

```bash
# LLM
export OLLAMA_BASE_URL="http://localhost:11434"
export LLM_MODEL="llama3.2"

# Audio
export WHISPER_MODEL="base"
export PIPER_VOICE="en_US-hfc_female-medium"

# Database
export DATABASE_URL="sqlite:///./inbound_agent.db"

# Storage
export VECTOR_STORE_PATH="./chroma_db"
export DOCUMENT_PATH="./data"
```

---

## 🚀 Enable Full RAG + LLM Features

### Step 1: Start Ollama
```bash
ollama serve
```

### Step 2: Install ffmpeg (optional, for audio conversion)
```bash
brew install ffmpeg  # macOS
```

### Step 3: Ingest Documents
```bash
curl -X POST http://localhost:8000/api/v1/documents/ingest
```

### Step 4: Test LLM Response
```bash
curl -X POST http://localhost:8000/api/v1/agent/query \
  -H "Content-Type: application/json" \
  -d '{"query":"What is your booking policy?","customer_id":"test"}'
```

---

## 📁 Key Files

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI app entry point |
| `app/config.py` | Configuration & settings |
| `app/api/agent_routes.py` | `/query` and `/voice-query` endpoints |
| `app/agent/inbound_agent.py` | LangGraph workflow |
| `app/agent/voice_processor.py` | Whisper STT + Piper TTS |
| `app/rag/ingestion.py` | Document loading & embedding |
| `app/static/app.js` | Web UI client logic |
| `chroma_db/` | Vector store (auto-created) |
| `data/` | Documents for RAG |

---

## ✅ Current Status

| Component | Status |
|-----------|--------|
| API Server | ✅ Running |
| Text Endpoint | ✅ Working |
| Voice Endpoint | ✅ Working (JSON fallback) |
| Web UI | ✅ Accessible |
| Database | ✅ SQLite initialized |
| STT (Whisper) | ✅ Loaded & working |
| TTS (Piper) | ⚠️ Not installed (browser TTS fallback) |
| LLM (Ollama) | ⚠️ Not running (graceful escalation) |
| RAG (ChromaDB) | ⚠️ Empty (awaiting Ollama for embeddings) |

---

## 🐛 Troubleshooting

### Server won't start
```bash
# Kill existing process
lsof -i :8000 | grep -v COMMAND | awk '{print $2}' | xargs kill -9
# Start fresh
TMPDIR=$(pwd)/.tmp uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Microphone access denied in browser
- Try: https:// instead of http:// (if using production URL)
- Or use Chrome dev tools to allow microphone access

### Ollama connection refused
```bash
# Start Ollama in separate terminal
ollama serve

# Verify it's running
curl http://localhost:11434/api/tags
```

### Disk space errors
```bash
# Clean caches
rm -rf ~/.cache/whisper/
pip cache purge

# Check disk usage
du -sh ~/* | sort -hr | head -10
```

---

## 📊 Response Formats

### Text Query Response
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "response": "Your answer here...",
  "confidence_score": 0.85,
  "escalated": false,
  "escalation_reason": null
}
```

### Voice Query Response (JSON Fallback)
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "response": "Your spoken message will be played via browser TTS...",
  "confidence_score": 0.8,
  "escalated": true,
  "transcript": "user said: hello there"
}
```

### Voice Query Response (Audio Stream)
- Content-Type: `audio/wav`
- Headers include session info in `X-*` headers

---

## 🎯 Flow Diagrams

### Happy Path (Full LLM + TTS)
```
User Input (voice/text)
    ↓
Whisper STT / Direct text
    ↓
ChromaDB Retrieval (RAG)
    ↓
Ollama LLM Generation
    ↓
Confidence Evaluation
    ↓
Piper TTS Synthesis
    ↓
Browser Playback ✅
```

### Fallback Path (No LLM/TTS)
```
User Input (voice/text)
    ↓
Whisper STT / Direct text
    ↓
No Ollama Available
    ↓
Escalation Response
    ↓
JSON Response to Client
    ↓
Browser Web Speech TTS ✅
```

---

## 📚 Documentation Files

- `SYSTEM_OVERVIEW.md` - Complete architecture & reference
- `README.md` - Original project description
- This file - Quick reference & troubleshooting

---

**Last Updated:** 2026-06-07  
**Version:** 1.0 - Production Ready
