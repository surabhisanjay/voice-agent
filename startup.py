#!/usr/bin/env python3
"""
Startup script for the Inbound Voice Agent.
"""
import sys
import logging
from app.database import init_db
from app.rag.ingestion import get_rag_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Initialize and start the agent."""
    logger.info("=" * 50)
    logger.info("Inbound Voice Agent - Initialization")
    logger.info("=" * 50)

    # Initialize database
    logger.info("Initializing database...")
    try:
        init_db()
        logger.info("✓ Database initialized successfully")
    except Exception as e:
        logger.error(f"✗ Failed to initialize database: {e}")
        return False

    # Initialize vector store
    logger.info("Initializing vector store...")
    try:
        pipeline = get_rag_pipeline()
        logger.info("✓ Vector store initialized successfully")
    except Exception as e:
        logger.error(f"✗ Failed to initialize vector store: {e}")
        return False

    # Ingest documents
    logger.info("Ingesting documents...")
    try:
        result = pipeline.ingest_documents()
        if result["status"] == "success":
            logger.info(f"✓ Documents ingested successfully")
            logger.info(f"  - Documents processed: {result['documents_processed']}")
            logger.info(f"  - Chunks created: {result['chunks_created']}")
        else:
            logger.warning(f"⚠ Document ingestion incomplete: {result['message']}")
    except Exception as e:
        logger.error(f"✗ Failed to ingest documents: {e}")
        return False

    logger.info("=" * 50)
    logger.info("Agent ready! Start the server with:")
    logger.info("  uvicorn app.main:app --reload")
    logger.info("=" * 50)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
