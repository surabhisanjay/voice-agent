# Inbound Voice Agent — Project File Summary

This document describes the repository structure and the purpose of each file and folder in the `voice_agent` project.

---

## Root Files

- `.DS_Store`
  - macOS Finder metadata file. Not part of application logic.

- `.env`
  - Optional environment file for overriding settings such as database URL, model selection, and logging configuration.

- `.tmp/`
  - Temporary directory used by the project for ephemeral files.

- `QUICK_REFERENCE.md`

- `README.md`
  - Main project documentation and setup guide.

- `SYSTEM_OVERVIEW.md`
  - High-level architecture description, component flow, and system design details.

- `requirements.txt`
  - Python dependency list required to install and run the application.

- `run_server.py`
  - Development launcher script that starts the FastAPI server with Uvicorn.

- `startup.py`
  - Initialization script that sets up the SQLite database, initializes the RAG pipeline, and ingests documents.

- `test_results.json`
  - Results output from test conversation runs, showing sampled agent responses and coverage.

- `prev_results.json`
  - Previous test or debug result file used for comparison or retention.

- `inbound_agent.db`
  - SQLite database file used by the application to store chat sessions, messages, escalation logs, and document ingestion history.

## Top-level Directories

### `app/`
Contains the application code and backend service components.

### `chroma_db/`
Persistence directory for ChromaDB vector embeddings.

### `data/`
Default document source directory used for RAG ingestion.

### `documents/`
Source text documents such as policies, FAQ files, and other knowledge-base content.

### `logs/`
Logging output directory used by the application.

### `tests/`
Contains test helpers and conversation test data.

### `venv/`
Python virtual environment directory (local development environment).

---

## `app/` Directory

- `__init__.py`
  - Package marker for the `app` module.

- `config.py`
  - Application settings managed by `pydantic-settings`.
  - Defines configuration values for Ollama, database, vector store, document paths, logging, and voice models.

- `database.py`
  - SQLAlchemy database engine and session management.
  - Provides `init_db()` and `get_db()` functions.

- `logging_config.py`
  - Logging utilities and configuration helpers for the application.

- `main.py`
  - FastAPI application entrypoint.
  - Configures logging, CORS, routers, static file mounting, and app lifecycle startup actions.

- `models.py`
  - SQLAlchemy ORM models for `ChatSession`, `ChatMessage`, `DocumentLog`, and `EscalationLog`.

### `app/agent/`
Agent workflow, memory, and voice processing logic.

- `__init__.py`
  - Package marker for the `app.agent` module.

- `inbound_agent.py`
  - Core LangGraph-based agent workflow implementation.
  - Handles document retrieval, LLM response generation, confidence evaluation, and escalation logic.

- `memory.py`
  - Conversation memory management for session history.
  - Loads and persists chat messages to the database and builds the history context string for prompts.

- `voice_processor.py`
  - Speech-to-text and text-to-speech integration.
  - Uses Whisper for transcription and Piper for TTS.
  - Includes audio conversion fallback logic for browser-recorded formats.

### `app/api/`
FastAPI route definitions.

- `__init__.py`
  - Package marker for the `app.api` module.

- `agent_routes.py`
  - Text query endpoint: `/api/v1/agent/query`
  - Voice query endpoint: `/api/v1/agent/voice-query`
  - Session history endpoint: `/api/v1/agent/session/{session_id}/history`
  - Handles session creation, conversation memory, transcription fallback, and TTS response streaming.

- `document_routes.py`
  - Document ingestion endpoint: `/api/v1/documents/ingest`
  - Document status endpoint: `/api/v1/documents/status`
  - Exposes RAG pipeline ingestion and persistence health.

### `app/rag/`
Retrieval-Augmented Generation pipeline code.

- `__init__.py`
  - Package marker for the `app.rag` module.

- `ingestion.py`
  - Document ingestion pipeline for loading source files, chunking them, embedding them, and persisting into ChromaDB.
  - Supports `.txt`, `.pdf`, `.docx`, and `.xlsx` ingestion.

- `retriever.py`
  - Document retrieval wrapper used by the agent.
  - Retrieves relevant documents from ChromaDB and formats them into prompt context.

### `app/static/`
Browser UI and frontend assets.

- `index.html`
  - Demo user interface for recording voice, sending text, and displaying responses.

- `app.js`
  - Frontend logic for recording audio, uploading it to the voice endpoint, handling responses, and playing audio or browser TTS.

- `styles.css`
  - Styling for the demo UI.

---

## `tests/` Directory

- `test_conversations.py`
  - Defines sample customer conversations and expected topics used for test runs.

- `test_runner.py`
  - Test harness for running sample conversations through the agent.
  - Reports metrics like confidence, escalations, and topic coverage.

---

## Important Data and Runtime Files

- `documents/booking_policy.txt`
  - Example document file used for answering booking-related questions.

- `documents/faqs.txt`
  - Example FAQ content used in the knowledge base.

- `documents/pricing_guide.txt`
  - Example pricing information used to answer cost-related queries.

- `logs/`
  - Stores the application log file referenced by `app/config.py`.

- `chroma_db/`
  - Holds the persisted ChromaDB vector store data and metadata.

---

## Summary

This project is organized into three main layers:

1. **API layer** (`app/main.py`, `app/api/`)
2. **Agent/AI layer** (`app/agent/`, `app/rag/`)
3. **Data layer** (`app/models.py`, `app/database.py`, `documents/`, `chroma_db/`, `inbound_agent.db`)

The `startup.py` script initializes the database and document embeddings, while `run_server.py` launches the FastAPI service.

If you want, I can also add a companion `FILE_TREE.md` with a visual directory tree. 