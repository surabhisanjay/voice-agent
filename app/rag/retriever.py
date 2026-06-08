"""
Document retriever for RAG — improved.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import List, Optional, Tuple

from langchain.schema import Document

from app.rag.ingestion import get_rag_pipeline

logger = logging.getLogger(__name__)


class DocumentRetriever:
    """Thin wrapper around the RAG pipeline for agent-facing retrieval."""

    def __init__(self, k: int = 5, score_threshold: float = 0.45, use_mmr: bool = True):
        self.k = k
        self.score_threshold = score_threshold
        self.use_mmr = use_mmr
        self._pipeline = get_rag_pipeline()

    def retrieve(self, query: str, k: Optional[int] = None) -> List[Document]:
        pairs = self.retrieve_with_scores(query, k=k)
        return [doc for doc, _ in pairs]

    def retrieve_with_scores(self, query: str, k: Optional[int] = None) -> List[Tuple[Document, float]]:
        effective_k = k or self.k
        results = self._pipeline.retrieve_documents(
            query, k=effective_k,
            score_threshold=self.score_threshold,
            use_mmr=self.use_mmr,
            fetch_k=effective_k * 4,
        )
        if not results:
            logger.info("No documents retrieved for: %r", query[:80])
            return results

        # Sort results by score so the most relevant documents appear first.
        # Some vector backends return similarity scores (higher is better),
        # while others may use distance/loss (lower is better). Here we assume
        # similarity-style scores when the maximum score exceeds 1.0.
        scores = [score for _, score in results]
        if max(scores, default=0.0) > 1.0:
            results.sort(key=lambda pair: pair[1], reverse=True)
        else:
            results.sort(key=lambda pair: pair[1])

        return results

    def format_context(self, documents: List[Document]) -> str:
        if not documents:
            return ""
        sections: List[str] = []
        for doc in documents:
            source = doc.metadata.get("filename") or Path(
                doc.metadata.get("source", "unknown")
            ).name
            clean_text = re.sub(r"^#{1,6}\s+", "", doc.page_content, flags=re.MULTILINE)
            sections.append(f"[{source}]\n{clean_text.strip()}")
        return "\n\n".join(sections)
