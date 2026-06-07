"""
Document management API routes.
"""
import logging
from fastapi import APIRouter, File, UploadFile, HTTPException
from typing import List
from app.rag.ingestion import get_rag_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@router.post("/ingest")
def ingest_documents():
    """Ingest all documents from the documents directory."""
    try:
        pipeline = get_rag_pipeline()
        result = pipeline.ingest_documents()

        if result["status"] == "success":
            return {
                "status": "success",
                "message": "Documents ingested successfully",
                "documents_processed": result["documents_processed"],
                "chunks_created": result["chunks_created"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])

    except Exception as e:
        logger.error(f"Error ingesting documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
def get_document_status():
    """Get document ingestion status."""
    try:
        pipeline = get_rag_pipeline()

        # Try to get collection stats
        stats = {
            "vector_store_initialized": pipeline.vector_store is not None,
            "vector_store_path": pipeline.vector_store._client._persist_directory if pipeline.vector_store else None
        }

        return stats

    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
