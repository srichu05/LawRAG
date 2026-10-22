"""
hybrid.py — Hybrid retrieval using Reciprocal Rank Fusion (RRF)
================================================================
Combines dense (ChromaDB semantic) and BM25 (lexical) results using
Reciprocal Rank Fusion (RRF) — a rank-based fusion method that avoids
directly comparing uncalibrated scores from different systems.

RRF formula (Cormack et al., 2009):
    RRF(d) = Σ_r 1 / (k + rank_r(d))

where k=60 is the standard smoothing constant (configurable via RRF_K).

Design decisions:
  - Deduplicates results by stable chunk_id
  - Preserves provenance (which retrievers found each result)
  - Exposes dense_rank and bm25_rank for diagnostic comparison
  - Returns the standard result schema
  - Configurable weights for each retriever
"""

from __future__ import annotations

import logging
from typing import Any

from app import config

logger = logging.getLogger(__name__)


def retrieve_hybrid(
    query: str,
    embedder,
    bm25_index=None,
    top_k: int | None = None,
    dense_top_k: int | None = None,
    bm25_top_k: int | None = None,
    rrf_k: int | None = None,
) -> list[dict[str, Any]]:
    """
    Hybrid retrieval: dense + BM25 fused via Reciprocal Rank Fusion.

    Parameters
    ----------
    query       : User query string
    embedder    : Configured BaseEmbedder instance
    bm25_index  : Optional pre-loaded BM25Index (loads from disk if None)
    top_k       : Final number of results to return
    dense_top_k : How many dense results to retrieve (for fusion)
    bm25_top_k  : How many BM25 results to retrieve (for fusion)
    rrf_k       : RRF smoothing constant (default config.RRF_K = 60)

    Returns
    -------
    list of result dicts sorted by RRF score (descending),
    each containing chunk_id, text, metadata, rrf_score, dense_rank, bm25_rank
    """
    from app.retrieval.chroma_store import retrieve_dense
    from app.retrieval.bm25 import retrieve_bm25

    if top_k is None:
        top_k = config.TOP_K
    if dense_top_k is None:
        dense_top_k = max(top_k * 3, config.BM25_TOP_K)
    if bm25_top_k is None:
        bm25_top_k = max(top_k * 3, config.BM25_TOP_K)
    if rrf_k is None:
        rrf_k = config.RRF_K

    # ── Run both retrievers ─────────────────────────────────────────────────
    dense_results: list[dict] = []
    bm25_results: list[dict] = []

    try:
        dense_results = retrieve_dense(query, embedder, top_k=dense_top_k)
        logger.debug("Dense retrieval returned %d results", len(dense_results))
    except Exception as exc:
        logger.info("Dense retrieval unavailable (%s); continuing with BM25 lexical retrieval.", exc)

    try:
        bm25_results = retrieve_bm25(query, top_k=bm25_top_k, index=bm25_index)
        logger.debug("BM25 retrieval returned %d results", len(bm25_results))
    except Exception as exc:
        logger.error("BM25 retrieval failed during hybrid: %s", exc)

    # ── Reciprocal Rank Fusion ──────────────────────────────────────────────
    fused = _rrf_fuse(
        dense_results=dense_results,
        bm25_results=bm25_results,
        rrf_k=rrf_k,
    )

    # Sort by RRF score descending
    fused.sort(key=lambda x: x["rrf_score"], reverse=True)

    # Trim to top_k and re-rank
    top_results = fused[:top_k]
    for rank, r in enumerate(top_results, start=1):
        r["rank"] = rank
        r["retrieval_method"] = "hybrid_rrf"

    logger.info(
        "Hybrid RRF: dense=%d bm25=%d fused=%d returned=%d",
        len(dense_results), len(bm25_results), len(fused), len(top_results)
    )
    return top_results


def _rrf_fuse(
    dense_results: list[dict],
    bm25_results: list[dict],
    rrf_k: int = 60,
) -> list[dict[str, Any]]:
    """
    Apply RRF to merge two ranked lists.

    Returns a merged list with rrf_score, dense_rank, bm25_rank,
    and the chunk's text and metadata from whichever retriever found it first.
    """
    # Collect all unique chunk_ids
    all_chunks: dict[str, dict] = {}  # chunk_id -> record template

    # Map chunk_id to rank for each retriever (1-indexed, None if not present)
    dense_rank_map: dict[str, int] = {}
    bm25_rank_map: dict[str, int] = {}

    for r in dense_results:
        cid = r["chunk_id"]
        dense_rank_map[cid] = r["rank"]
        if cid not in all_chunks:
            all_chunks[cid] = r.copy()

    for r in bm25_results:
        cid = r["chunk_id"]
        bm25_rank_map[cid] = r["rank"]
        if cid not in all_chunks:
            all_chunks[cid] = r.copy()

    # Compute RRF scores
    fused: list[dict] = []
    for cid, record in all_chunks.items():
        dense_r = dense_rank_map.get(cid)
        bm25_r = bm25_rank_map.get(cid)

        rrf_score = 0.0
        if dense_r is not None:
            rrf_score += 1.0 / (rrf_k + dense_r)
        if bm25_r is not None:
            rrf_score += 1.0 / (rrf_k + bm25_r)

        result = {
            "chunk_id": cid,
            "text": record.get("text", ""),
            "source_file": record.get("source_file"),
            "source_id": record.get("source_id"),
            "chunk_index": record.get("chunk_index", -1),
            "total_pages": record.get("total_pages", -1),
            "rrf_score": round(rrf_score, 6),
            "dense_rank": dense_r,
            "bm25_rank": bm25_r,
            # Raw scores for diagnostics
            "distance": record.get("distance"),
            "bm25_score": record.get("bm25_score"),
        }
        fused.append(result)

    return fused


def compare_retrieval_methods(
    query: str,
    embedder,
    bm25_index=None,
    top_k: int = 5,
) -> dict[str, Any]:
    """
    Run all three retrieval methods and return a side-by-side comparison.
    Useful for evaluation and debugging.

    Returns dict with keys 'dense', 'bm25', 'hybrid', 'overlap_analysis'
    """
    from app.retrieval.chroma_store import retrieve_dense
    from app.retrieval.bm25 import retrieve_bm25

    dense = retrieve_dense(query, embedder, top_k=top_k)
    bm25 = retrieve_bm25(query, top_k=top_k, index=bm25_index)
    hybrid = retrieve_hybrid(
        query, embedder, bm25_index=bm25_index, top_k=top_k
    )

    dense_ids = {r["chunk_id"] for r in dense}
    bm25_ids = {r["chunk_id"] for r in bm25}
    hybrid_ids = {r["chunk_id"] for r in hybrid}

    overlap_analysis = {
        "dense_only": len(dense_ids - bm25_ids),
        "bm25_only": len(bm25_ids - dense_ids),
        "in_both": len(dense_ids & bm25_ids),
        "in_hybrid": len(hybrid_ids),
        "dense_in_hybrid": len(dense_ids & hybrid_ids),
        "bm25_in_hybrid": len(bm25_ids & hybrid_ids),
    }

    return {
        "query": query,
        "dense": dense,
        "bm25": bm25,
        "hybrid": hybrid,
        "overlap_analysis": overlap_analysis,
    }
