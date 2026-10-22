"""
state.py — Typed state definition for LawRAG LangGraph workflow
================================================================
Defines the shared state dictionary passed across nodes in the Agentic
RAG graph.
"""

from __future__ import annotations

from typing import Any, TypedDict


class Citation(TypedDict):
    """Structured citation referencing a retrieved record."""
    chunk_id: str
    source_file: str | None
    source_id: str | None
    chunk_index: int
    total_pages: int
    excerpt: str


class LawRAGState(TypedDict, total=False):
    """
    State schema for the LawRAG Agentic retrieval-augmented generation graph.

    Mandatory fields:
    ----------------
    question          : Original legal question from the user
    retrieved_chunks  : List of retrieved chunks from hybrid retrieval
    evidence_status   : "sufficient" | "weak" | "insufficient" | "unsupported"
    retry_count       : Number of query rewriting and re-retrieval attempts (max 1)
    answer            : Final generated answer or abstention notice
    citations         : Validated citations pointing strictly to retrieved records
    warnings          : Disclosures, missing metadata notices, or conflict flags

    Operational / tracking fields:
    -----------------------------
    search_query      : Active search query used for retrieval
    rewritten_queries : List of alternative search queries attempted
    conflicts_detected: Whether conflicting positions were found in retrieved passages
    metadata          : Latency, timings, retrieval breakdown, and audit metadata
    """
    question: str
    retrieved_chunks: list[dict[str, Any]]
    evidence_status: str
    retry_count: int
    answer: str
    citations: list[dict[str, Any]]
    warnings: list[str]
    search_query: str
    rewritten_queries: list[str]
    conflicts_detected: bool
    metadata: dict[str, Any]
