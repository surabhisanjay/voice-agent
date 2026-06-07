# Inbound Voice Agent

A production-ready **voice-based AI customer support agent** that answers customer questions based on company documents using LangGraph, LangChain, Ollama, Whisper, and Piper TTS.

## Features

✅ **Voice-based Conversations** - Accept speech input and respond with natural speech output
✅ **RAG Pipeline** - Retrieve answers from company documents, FAQs, policies, and knowledge base
✅ **LangGraph Workflow** - Orchestrated agent workflow with decision logic and escalation
✅ **Conversation Memory** - Maintains context across multi-turn conversations
✅ **Document Ingestion** - Automatically process and vectorize documents
✅ **FastAPI Backend** - RESTful API with text and voice endpoints
✅ **Escalation Support** - Flag unanswered questions for human review
✅ **SQLite Logging** - Complete conversation and interaction logging
✅ **Production-Ready** - Comprehensive error handling and monitoring

## Tech Stack

- **LLM**: Ollama (Llama 2, Llama 3.2, or Qwen)
- **Speech-to-Text**: OpenAI Whisper
- **Text-to-Speech**: Piper TTS
- **Orchestration**: LangGraph
- **RAG**: LangChain + ChromaDB
- **Vector Store**: ChromaDB (embeddings from Ollama)
- **Database**: SQLite
- **API**: FastAPI + Uvicorn
- **Language**: Python 3.9+

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Customer (Voice)                     │
└──────────────┬──────────────────────────────────────────┘
               │
               ↓
       ┌───────────────┐
       │ Speech-to-Text│ (Whisper)
       │   (Optional)  │
       └───────┬───────┘
               │
               ↓
       ┌─────────────────────┐
       │  FastAPI Endpoint   │
       │   /voice-query      │
       └───────┬─────────────┘
               │
               ↓
       ┌──────────────────────────┐
       │  Inbound Voice Agent     │
       │   (LangGraph Workflow)   │
       └───────┬──────────────────┘
               │
        ┌──────┴──────┐
        ↓             ↓
    ┌────────┐   ┌─────────────┐
    │ RAG    │   │ Conversation│
    │Pipeline│   │  Memory     │
    └────┬───┘   └─────────────┘
         │
    ┌────┴─────────┐
    ↓              ↓
┌───────────┐ ┌──────────────┐
│ChromaDB   │ │SQLite        │
│(Vectors)  │ │(History/Logs)│
└───────────┘ └──────────────┘
       │
       ↓
┌──────────────────┐
│Document Files   │
│(Policies, FAQs) │
└──────────────────┘
               │
               ↓
       ┌────────────────┐
       │Text-to-Speech  │ (Piper)
       │   (Optional)   │
       └────────┬───────┘
                │
                ↓
        ┌───────────────────┐
        │Customer Hears     │
        │Response (Voice)   │
        └───────────────────┘
```

## Installation

### Prerequisites

1. **Ollama** - Download and install from [ollama.ai](https://ollama.ai)
   ```bash
   # Pull a model
   ollama pull llama2
   # Run Ollama server
   ollama serve
   ```

2. **Python 3.9+**

3. **FFmpeg** (for audio processing)
   ```bash
   # macOS
   brew install ffmpeg
   # Ubuntu
   sudo apt-get install ffmpeg
   # Windows
   choco install ffmpeg
   ```

### Setup

1. **Clone and navigate to the project**
   ```bash
   cd voice_agent
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize the application**
   ```bash
   python startup.py
   ```

5. **Start the API server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

The API will be available at `http://localhost:8000`

## Quick Start

### 1. Ingest Documents

```bash
curl -X POST http://localhost:8000/api/v1/documents/ingest
```

Response:
```json
{
  "status": "success",
  "message": "Documents ingested successfully",
  "documents_processed": 3,
  "chunks_created": 45
}
```

### 2. Ask a Text Question

```bash
curl -X POST http://localhost:8000/api/v1/agent/query \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "cust_001",
    "query": "What documents are required for event booking?"
  }'
```

Response:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "response": "According to the booking policy document, customers must provide a valid ID proof, booking form, advance payment receipt, and event details before confirmation.",
  "confidence_score": 0.89,
  "escalated": false,
  "escalation_reason": null
}
```

### 3. Ask a Voice Question (with Whisper)

```bash
curl -X POST http://localhost:8000/api/v1/agent/voice-query \
  -F "customer_id=cust_001" \
  -F "audio_file=@question.wav"
```

Response: Returns audio (WAV format) with headers:
- `X-Session-ID`: Session identifier
- `X-Confidence-Score`: Confidence in response
- `X-Escalated`: Whether query was escalated
- `X-Transcript`: Transcribed customer question

### 4. Get Conversation History

```bash
curl http://localhost:8000/api/v1/session/{session_id}/history
```

## Sample Documents

The following sample documents are included in `/documents/`:

1. **booking_policy.txt** - Booking procedures, required documents, cancellation policy
2. **pricing_guide.txt** - Service packages, add-ons, discounts, payment terms
3. **faqs.txt** - Frequently asked questions about services, venues, catering

## Example Test Conversations

Run tests with:
```bash
python tests/test_runner.py
```

This runs 7 test conversations including:
- Booking document requirements
- Pricing and discount queries
- Cancellation and rescheduling
- Payment and billing questions
- Venue and facilities questions
- Catering and add-ons
- Escalation scenarios

Results are saved to `test_results.json`

## Configuration

Edit `.env` to customize:

```env
# LLM Configuration
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=llama2

# Voice Configuration
WHISPER_MODEL=base              # tiny, base, small, medium, large
TTS_MODEL=en_US-lessac-medium

# Database
DATABASE_URL=sqlite:///./inbound_agent.db

# Vector Store
VECTOR_STORE_PATH=./chroma_db

# Agent Behavior
ESCALATION_CONFIDENCE_THRESHOLD=0.5
MAX_CONVERSATION_HISTORY=10

# Documents
DOCUMENT_PATH=./documents
CHUNK_SIZE=512
CHUNK_OVERLAP=100
```

## API Endpoints

### Document Management
- `POST /api/v1/documents/ingest` - Ingest documents from `/documents` directory
- `GET /api/v1/documents/status` - Get vector store status

### Agent Queries
- `POST /api/v1/agent/query` - Process text question
- `POST /api/v1/agent/voice-query` - Process voice question (returns audio)
- `GET /api/v1/session/{session_id}/history` - Get conversation history

### Utility
- `GET /health` - Health check
- `GET /` - API information

## Database Schema

### chat_sessions
Stores customer conversation sessions:
- `id` (string, PK)
- `customer_id` (string)
- `created_at` (datetime)
- `updated_at` (datetime)
- `status` (string: active, closed, escalated)

### chat_messages
Stores conversation messages:
- `id` (string, PK)
- `session_id` (string, FK)
- `role` (string: user, assistant)
- `content` (text)
- `timestamp` (datetime)
- `confidence_score` (float)
- `retrieved_documents` (text, JSON)

### escalation_logs
Tracks escalated queries:
- `id` (string, PK)
- `session_id` (string, FK)
- `message_id` (string, FK)
- `reason` (string)
- `confidence_score` (float)
- `escalated_at` (datetime)
- `resolved` (boolean)

### document_logs
Tracks ingested documents:
- `id` (string, PK)
- `document_name` (string)
- `document_path` (string)
- `ingested_at` (datetime)
- `chunk_count` (integer)
- `vector_ids` (text, JSON)

## Workflow Logic

The agent uses LangGraph to orchestrate:

```
Customer Query
    ↓
Retrieve Documents (RAG)
    ↓
Generate Response (LLM)
    ↓
Evaluate Confidence
    ↓
Should Escalate? ──YES──> Handle Escalation
    │                      ↓
    NO                    Respond
    ↓
    └─────────────────────→ Respond
                           ↓
                       Return Response
```

**Escalation Triggers:**
- No relevant documents found
- Response contains "not found", "don't have", "no information"
- Confidence score below threshold
- Manual escalation request

## Adding Documents

1. Place document files in `/documents/` directory
2. Supported formats: `.txt`, `.pdf`
3. Run ingest endpoint or restart application
4. Documents are automatically chunked and vectorized

## Production Deployment

### Docker

Create a `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t inbound-agent .
docker run -p 8000:8000 inbound-agent
```

### Environment Setup

For production:
1. Use environment variables instead of `.env`
2. Configure logging to external service
3. Set up database backups
4. Enable HTTPS
5. Add authentication/authorization
6. Configure rate limiting

## Performance Tuning

1. **Reduce Whisper Model Size**: Use `tiny` or `small` instead of `base`
2. **Batch Processing**: Process multiple queries in parallel
3. **Vector Store Optimization**: Use FAISS instead of ChromaDB for larger datasets
4. **LLM Optimization**: Use quantized models (GGUF format)
5. **Caching**: Cache common queries and responses

## Troubleshooting

**Ollama Connection Error**
```bash
# Ensure Ollama is running
ollama serve
```

**Model Not Found**
```bash
# Pull the model
ollama pull llama2
```

**Audio Processing Error**
```bash
# Ensure FFmpeg is installed
brew install ffmpeg  # macOS
sudo apt-get install ffmpeg  # Linux
```

**Out of Memory**
- Use smaller Whisper model
- Reduce chunk size
- Use CPU-only inference

## Project Structure

```
voice_agent/
├── app/
│   ├── __init__.py
│   ├── config.py              # Configuration
│   ├── database.py            # Database setup
│   ├── models.py              # SQLAlchemy models
│   ├── main.py                # FastAPI app
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── inbound_agent.py   # LangGraph workflow
│   │   ├── memory.py          # Conversation memory
│   │   └── voice_processor.py # Whisper & Piper
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── ingestion.py       # Document pipeline
│   │   └── retriever.py       # RAG retrieval
│   └── api/
│       ├── __init__.py
│       ├── agent_routes.py    # Agent endpoints
│       └── document_routes.py # Document endpoints
├── documents/                 # Document repository
│   ├── booking_policy.txt
│   ├── pricing_guide.txt
│   └── faqs.txt
├── tests/
│   ├── test_conversations.py  # Test data
│   └── test_runner.py         # Test runner
├── requirements.txt           # Python dependencies
├── .env                       # Configuration
├── startup.py                 # Initialization script
└── README.md                  # This file
```

## Contributing

This is a production-ready system. For improvements:
1. Add more test conversations
2. Expand document repository
3. Fine-tune confidence thresholds
4. Add custom LLM prompts
5. Implement analytics

## License

Copyright © 2024. All rights reserved.

## Support

For issues or questions, review the troubleshooting section or check logs in `/logs/`.
