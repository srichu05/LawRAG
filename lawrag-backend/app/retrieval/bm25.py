"""
bm25.py — BM25 lexical retrieval
===================================
Implements BM25 retrieval over the normalized corpus.
Important for legal queries with exact terminology, case names,
section numbers, and statutory references.

BM25 is built from normalized records at index time and persisted
as a pickle file so retrieval does not require re-reading the corpus.

Library: rank_bm25 (BM25Okapi implementation)

Design decisions:
  - Tokenization is consistent between index and query time
  - Original chunk metadata is preserved in results
  - Returns the same result schema as dense retrieval
  - Handles empty queries and empty index gracefully
"""

from __future__ import annotations

import logging
import pickle
import re
from pathlib import Path
from typing import Any

from app import config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

def tokenize(text: str) -> list[str]:
    """
    Simple whitespace+punctuation tokenizer suitable for legal text.
    - Lowercase
    - Split on whitespace and punctuation
    - Filter empty tokens
    - Keeps abbreviations and statute references like "IPC", "S.302"
    """
    if not text:
        return []
    # Lower-case and split on non-alphanumeric (except dot in abbreviations)
    tokens = re.split(r"[\s\,\;\:\!\?\(\)\[\]\{\}\"\'\—\–\-\/\\]+", text.lower())
    return [t for t in tokens if t and len(t) >= 2]


# ---------------------------------------------------------------------------
# BM25 index builder
# ---------------------------------------------------------------------------

class BM25Index:
    """
    Wrapper around rank_bm25.BM25Okapi with document metadata.

    Attributes
    ----------
    _bm25       : rank_bm25.BM25Okapi instance
    _chunk_ids  : list of chunk_ids in corpus order
    _records    : list of full record dicts in corpus order
    """

    def __init__(self) -> None:
        self._bm25 = None
        self._chunk_ids: list[str] = []
        self._records: list[dict] = []
        self._model_tag: str = ""
        self._is_built: bool = False

    def build(self, records: list[dict], model_tag: str = "") -> None:
        """
        Build BM25 index from a list of normalized records.

        Parameters
        ----------
        records   : list of dicts with at least "chunk_id" and "text"
        model_tag : embedding model id (stored for compatibility check)
        """
        try:
            from rank_bm25 import BM25Okapi  # type: ignore
        except ImportError:
            raise ImportError(
                "rank_bm25 is not installed. Run: pip install rank-bm25"
            )

        self._model_tag = model_tag
        self._records = []
        self._chunk_ids = []
        tokenized_corpus: list[list[str]] = []

        for record in records:
            text = record.get("text", "")
            if not text or not text.strip():
                continue
            tokens = tokenize(text)
            if tokens:
                tokenized_corpus.append(tokens)
                self._records.append(record)
                self._chunk_ids.append(record["chunk_id"])

        if tokenized_corpus:
            self._bm25 = BM25Okapi(tokenized_corpus)
        else:
            self._bm25 = None
        self._is_built = True
        logger.info(
            "BM25 index built with %d documents.", len(self._records)
        )

    def retrieve(self, query: str, top_k: int) -> list[dict[str, Any]]:
        """
        Retrieve top-k documents by BM25 score.

        Returns
        -------
        list of result dicts (same schema as dense retrieval)
        """
        if not self._is_built:
            raise RuntimeError("BM25 index has not been built or loaded.")

        if not query or not query.strip():
            logger.warning("BM25 retrieve called with empty query.")
            return []

        if not self._records or self._bm25 is None:
            logger.warning("BM25 index is empty.")
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        k = min(top_k, len(self._records))
        scores = self._bm25.get_scores(query_tokens)

        # Get top-k indices by score
        import numpy as np  # type: ignore
        top_indices = np.argsort(scores)[::-1][:k]

        results = []
        for rank, idx in enumerate(top_indices, start=1):
            record = self._records[int(idx)]
            results.append({
                "chunk_id": record["chunk_id"],
                "text": record["text"],
                "source_file": record.get("source_file"),
                "source_id": record.get("source_id"),
                "chunk_index": record.get("chunk_index", -1),
                "total_pages": record.get("total_pages", -1),
                "bm25_score": float(scores[int(idx)]),
                "retrieval_method": "bm25",
                "rank": rank,
            })

        return results

    def save(self, path: Path) -> None:
        """Persist the BM25 index to disk."""
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "bm25": self._bm25,
            "chunk_ids": self._chunk_ids,
            "records": self._records,
            "model_tag": self._model_tag,
        }
        with open(path, "wb") as fh:
            pickle.dump(payload, fh)
        logger.info("BM25 index saved to %s (%d docs)", path, len(self._records))

    def load(self, path: Path) -> None:
        """Load a previously persisted BM25 index."""
        if not path.exists():
            raise FileNotFoundError(
                f"BM25 index not found: {path}. "
                f"Run: python scripts/build_index.py first."
            )
        with open(path, "rb") as fh:
            payload = pickle.load(fh)
        self._bm25 = payload["bm25"]
        self._chunk_ids = payload["chunk_ids"]
        self._records = payload["records"]
        self._model_tag = payload.get("model_tag", "")
        self._is_built = True
        logger.info(
            "BM25 index loaded from %s (%d docs)", path, len(self._records)
        )

    @property
    def doc_count(self) -> int:
        return len(self._records)


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

def build_bm25_index(normalized_records_path: Path) -> BM25Index:
    """
    Build and return a BM25Index from the normalized JSONL file.
    Also saves the index to config.BM25_INDEX_PATH.
    """
    from app.ingestion.normalize import load_normalized_records

    logger.info("Building BM25 index from %s…", normalized_records_path)
    records = list(load_normalized_records(normalized_records_path))
    idx = BM25Index()
    idx.build(records, model_tag=config.EMBEDDING_MODEL)
    idx.save(config.BM25_INDEX_PATH)
    return idx


def load_bm25_index() -> BM25Index:
    """Load the persisted BM25 index."""
    idx = BM25Index()
    idx.load(config.BM25_INDEX_PATH)
    return idx


def retrieve_bm25(
    query: str,
    top_k: int | None = None,
    index: BM25Index | None = None,
) -> list[dict[str, Any]]:
    """
    BM25 retrieval entry point.

    Parameters
    ----------
    query  : User query string
    top_k  : Number of results (defaults to config.BM25_TOP_K)
    index  : Optional pre-loaded BM25Index (loads from disk if None)

    Returns
    -------
    list of result dicts
    """
    if top_k is None:
        top_k = config.BM25_TOP_K

    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    if not isinstance(top_k, int) or top_k < 1:
        raise ValueError(f"top_k must be a positive integer, got {top_k!r}")
    top_k = min(top_k, 200)

    if index is None:
        index = load_bm25_index()

    return index.retrieve(query, top_k)
