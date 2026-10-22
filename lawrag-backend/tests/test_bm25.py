"""
Tests for BM25 retrieval module.
Tests run offline — no network or API calls.
"""
import json
import pickle
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.retrieval.bm25 import BM25Index, tokenize, retrieve_bm25


# ---------------------------------------------------------------------------
# Sample records
# ---------------------------------------------------------------------------

SAMPLE_RECORDS = [
    {
        "chunk_id": "1",
        "text": "The Supreme Court held that bail cannot be granted in murder cases under section 302 IPC without exceptional circumstances.",
        "source_file": "bail_murder.pdf",
        "source_id": "1",
        "chunk_index": 0,
        "total_pages": 10,
        "metadata": {"source": "bail_murder.pdf", "chunk_index": 0, "total_pages": 10},
    },
    {
        "chunk_id": "2",
        "text": "The principles of natural justice require that no person shall be condemned unheard. This is the audi alteram partem rule.",
        "source_file": "natural_justice.pdf",
        "source_id": "2",
        "chunk_index": 1,
        "total_pages": 5,
        "metadata": {"source": "natural_justice.pdf", "chunk_index": 1, "total_pages": 5},
    },
    {
        "chunk_id": "3",
        "text": "Article 21 of the Constitution guarantees the right to life and personal liberty which cannot be taken away except by procedure established by law.",
        "source_file": "fundamental_rights.pdf",
        "source_id": "3",
        "chunk_index": 0,
        "total_pages": 20,
        "metadata": {"source": "fundamental_rights.pdf", "chunk_index": 0, "total_pages": 20},
    },
    {
        "chunk_id": "4",
        "text": "Breach of contract occurs when a party fails to fulfill their contractual obligations without lawful excuse.",
        "source_file": "contract_law.pdf",
        "source_id": "4",
        "chunk_index": 0,
        "total_pages": 8,
        "metadata": {"source": "contract_law.pdf", "chunk_index": 0, "total_pages": 8},
    },
    {
        "chunk_id": "5",
        "text": "The writ of habeas corpus is a fundamental writ that secures release from unlawful detention.",
        "source_file": "writs.pdf",
        "source_id": "5",
        "chunk_index": 0,
        "total_pages": 12,
        "metadata": {"source": "writs.pdf", "chunk_index": 0, "total_pages": 12},
    },
]


# ---------------------------------------------------------------------------
# Tests for tokenizer
# ---------------------------------------------------------------------------

class TestTokenize:
    def test_basic_tokenization(self):
        tokens = tokenize("bail denied murder")
        assert "bail" in tokens
        assert "denied" in tokens
        assert "murder" in tokens

    def test_lowercases(self):
        tokens = tokenize("Section 302 IPC")
        assert "section" in tokens
        assert "ipc" in tokens

    def test_filters_short_tokens(self):
        tokens = tokenize("a I am the")
        # Single-char tokens filtered
        assert "a" not in tokens
        assert "i" not in tokens

    def test_empty_string(self):
        assert tokenize("") == []

    def test_none(self):
        assert tokenize(None) == []

    def test_punctuation_removed(self):
        tokens = tokenize("natural justice, fairness; audi alteram partem!")
        assert "natural" in tokens
        assert "justice" in tokens
        assert "audi" in tokens


# ---------------------------------------------------------------------------
# Tests for BM25Index
# ---------------------------------------------------------------------------

class TestBM25Index:
    def test_build_and_retrieve(self):
        idx = BM25Index()
        idx.build(SAMPLE_RECORDS)
        results = idx.retrieve("bail murder section 302", top_k=3)
        assert len(results) >= 1
        # Record about bail/murder should rank highest
        top_id = results[0]["chunk_id"]
        assert top_id == "1", f"Expected '1', got '{top_id}'. Results: {results[:3]}"

    def test_natural_justice_query(self):
        idx = BM25Index()
        idx.build(SAMPLE_RECORDS)
        results = idx.retrieve("natural justice audi alteram partem", top_k=3)
        assert len(results) >= 1
        assert results[0]["chunk_id"] == "2"

    def test_article_21_query(self):
        idx = BM25Index()
        idx.build(SAMPLE_RECORDS)
        results = idx.retrieve("article 21 right to life liberty", top_k=3)
        assert results[0]["chunk_id"] == "3"

    def test_result_schema(self):
        idx = BM25Index()
        idx.build(SAMPLE_RECORDS)
        results = idx.retrieve("contract breach", top_k=1)
        assert len(results) == 1
        r = results[0]
        required_keys = {"chunk_id", "text", "source_file", "source_id",
                         "chunk_index", "total_pages", "bm25_score", "rank", "retrieval_method"}
        assert required_keys.issubset(set(r.keys()))
        assert r["retrieval_method"] == "bm25"

    def test_empty_query_returns_empty(self):
        idx = BM25Index()
        idx.build(SAMPLE_RECORDS)
        results = idx.retrieve("", top_k=5)
        assert results == []

    def test_empty_index_returns_empty(self):
        idx = BM25Index()
        idx.build([])
        results = idx.retrieve("murder bail", top_k=5)
        assert results == []

    def test_top_k_respected(self):
        idx = BM25Index()
        idx.build(SAMPLE_RECORDS)
        results = idx.retrieve("law court", top_k=2)
        assert len(results) <= 2

    def test_ranks_are_sequential(self):
        idx = BM25Index()
        idx.build(SAMPLE_RECORDS)
        results = idx.retrieve("fundamental rights", top_k=5)
        ranks = [r["rank"] for r in results]
        assert ranks == list(range(1, len(results) + 1))

    def test_source_metadata_preserved(self):
        idx = BM25Index()
        idx.build(SAMPLE_RECORDS)
        results = idx.retrieve("habeas corpus writ detention", top_k=1)
        r = results[0]
        assert r["source_file"] is not None
        assert r["chunk_id"] is not None

    def test_save_and_load(self, tmp_path):
        idx = BM25Index()
        idx.build(SAMPLE_RECORDS)
        path = tmp_path / "bm25.pkl"
        idx.save(path)
        assert path.exists()

        idx2 = BM25Index()
        idx2.load(path)
        assert idx2.doc_count == len(SAMPLE_RECORDS)

        results = idx2.retrieve("murder bail section 302", top_k=1)
        assert results[0]["chunk_id"] == "1"

    def test_load_missing_file_raises(self, tmp_path):
        idx = BM25Index()
        with pytest.raises(FileNotFoundError):
            idx.load(tmp_path / "missing.pkl")

    def test_not_built_retrieve_raises(self):
        idx = BM25Index()
        with pytest.raises(RuntimeError, match="not been built"):
            idx.retrieve("any query", top_k=5)

    def test_vocabulary_mismatch_returns_results(self):
        """Querying with terms not in corpus should return (possibly low-score) results."""
        idx = BM25Index()
        idx.build(SAMPLE_RECORDS)
        results = idx.retrieve("cryptocurrency bitcoin blockchain", top_k=3)
        # Should not crash, may return results with low scores
        assert isinstance(results, list)


class TestRetrieveBm25Function:
    def test_raises_on_empty_query(self, tmp_path):
        idx = BM25Index()
        idx.build(SAMPLE_RECORDS)
        with pytest.raises(ValueError, match="non-empty"):
            retrieve_bm25("", top_k=5, index=idx)

    def test_raises_on_invalid_top_k(self, tmp_path):
        idx = BM25Index()
        idx.build(SAMPLE_RECORDS)
        with pytest.raises(ValueError, match="positive integer"):
            retrieve_bm25("murder", top_k=0, index=idx)
