"""
Main FastAPI application for the Inbound Voice Agent.
"""
import logging
import os
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.database import init_db
from app.api import agent_routes, document_routes

# Ensure the log directory exists before creating handlers
log_dir = os.path.dirname(settings.log_file)
if log_dir:
    os.makedirs(log_dir, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(settings.log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for app startup and shutdown."""
    # Startup
    logger.info("Starting Inbound Voice Agent...")
    os.makedirs(os.path.dirname(settings.log_file), exist_ok=True)
    init_db()
    logger.info("Database initialized")

    yield

    # Shutdown
    logger.info("Shutting down Inbound Voice Agent...")


# Create FastAPI app
app = FastAPI(
    title="Inbound Voice Agent API",
    description="Voice-based AI agent for customer support",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(agent_routes.router)
app.include_router(document_routes.router)


# Mount the static UI
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/ui")
def ui_redirect():
    """Redirect to the interactive UI page."""
    return RedirectResponse(url="/static/index.html")

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "agent": "Inbound Voice Agent"
    }


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "Inbound Voice Agent API",
        "endpoints": {
            "health": "/health",
            "query": "/api/v1/agent/query",
            "voice_query": "/api/v1/agent/voice-query",
            "ingest_documents": "/api/v1/documents/ingest",
            "document_status": "/api/v1/documents/status"
        }
    }
