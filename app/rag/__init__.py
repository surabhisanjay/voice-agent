"""RAG module for document retrieval and augmented generation."""
from app.rag.ingestion import DocumentIngestionPipeline, get_rag_pipeline
from app.rag.retriever import DocumentRetriever

__all__ = ["DocumentIngestionPipeline", "get_rag_pipeline", "DocumentRetriever"]
