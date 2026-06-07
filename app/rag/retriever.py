"""
Document retriever for RAG — improved.

Key changes vs v1:
- Score-aware: passes score_threshold and use_mmr through to the pipeline so
  irrelevant chunks are dropped before reaching the LLM.
- format_context: no longer injects "[Document N]" labels that confuse the LLM
  into citing numbered sources.  Instead it emits clean, source-tagged blocks.
- Added retrieve_with_scores() for callers that need the raw (doc, score) pairs
  (e.g. the confidence evaluator in the agent).
- Graceful empty-result handling returns an empty string (not a "No relevant
  documents found." string that the LLM can mistake for real content).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Tuple

from langchain.schema import Document

from app.rag.ingestion import get_rag_pipeline

logger = logging.getLogger(__name__)


class DocumentRetriever:
    """Thin wrapper around the RAG pipeline for agent-facing retrieval."""

    def __init__(
        self,
        k: int = 5,
        score_threshold: float = 0.30,
        use_mmr: bool = True,
    ):
        """
        Args:
            k:                Max chunks to return.
            score_threshold:  Chroma cosine distance ceiling (lower = stricter).
                              0.30 keeps only clearly relevant chunks;
                              raise to 0.45 for smaller / sparser knowledge bases.
            use_mmr:          Deduplicate results with Maximal Marginal Relevance.
        """
        self.k = k
        self.score_threshold = score_threshold
        self.use_mmr = use_mmr
        self._pipeline = get_rag_pipeline()

    # ------------------------------------------------------------------

    def retrieve(self, query: str, k: Optional[int] = None) -> List[Document]:
        """Return the top-*k* relevant documents for *query*."""
        pairs = self.retrieve_with_scores(query, k=k)
        return [doc for doc, _ in pairs]

    def retrieve_with_scores(
        self,
        query: str,
        k: Optional[int] = None,
    ) -> List[Tuple[Document, float]]:
        """Return (document, similarity_score) pairs for *query*."""
        effective_k = k or self.k
        results = self._pipeline.retrieve_documents(
            query,
            k=effective_k,
            score_threshold=self.score_threshold,
            use_mmr=self.use_mmr,
            fetch_k=effective_k * 4,
        )

        if not results:
            logger.info("No documents retrieved for: %r", query[:80])

        return results

    # ------------------------------------------------------------------

    def format_context(self, documents: List[Document]) -> str:
        """
        Render retrieved documents as a clean context block for the LLM.

        Format:
            --- booking_policy.txt ---
            <chunk text>

            --- faqs.txt ---
            <chunk text>

        No "Document N" labels — they cause the LLM to say things like
        "According to Document 2" which sounds robotic in a voice response.
        """
        if not documents:
            return ""

        sections: List[str] = []
        for doc in documents:
            source = doc.metadata.get("filename") or Path(
                doc.metadata.get("source", "unknown")
            ).name
            sections.append(f"--- {source} ---\n{doc.page_content.strip()}")

        return "\n\n".join(sections)
