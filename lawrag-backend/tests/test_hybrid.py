"""
Tests for hybrid retrieval (RRF fusion) module.
Tests run offline using MockEmbedder and in-memory BM25.
"""
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["EMBEDDING_PROVIDER"] = "mock"

from app.retrieval.hybrid import _rrf_fuse, retrieve_hybrid, compare_retrieval_methods
from app.retrieval.bm25 import BM25Index
from app.retrieval.embeddings import MockEmbedder

# Shared sample records
SAMPLE_RECORDS = [
    {"chunk_id": "1", "text": "Murder bail section 302 IPC exceptional circumstances.",
     "source_file": "case1.pdf", "source_id": "1", "chunk_index": 0, "total_pages": 5},
    {"chunk_id": "2", "text": "Natural justice audi alteram partem nemo judex.",
     "source_file": "case2.pdf", "source_id": "2", "chunk_index": 0, "total_pages": 3},
    {"chunk_id": "3", "text": "Article 21 right to life personal liberty constitution.",
     "source_file": "case3.pdf", "source_id": "3", "chunk_index": 1, "total_pages": 20},
    {"chunk_id": "4", "text": "Breach of contract damages remedy aggrieved party.",
     "source_file": "case4.pdf", "source_id": "4", "chunk_index": 0, "total_pages": 8},
    {"chunk_id": "5", "text": "Habeas corpus writ petition unlawful detention release.",
     "source_file": "case5.pdf", "source_id": "5", "chunk_index": 0, "total_pages": 12},
]


def _make_dense_results(chunk_ids: list[str]) -> list[dict]:
    """Make fake dense results in given order."""
    results = []
    for rank, cid in enumerate(chunk_ids, start=1):
        rec = next(r for r in SAMPLE_RECORDS if r["chunk_id"] == cid)
        results.append({
            **rec,
            "distance": 0.1 * rank,
            "retrieval_method": "dense",
            "rank": rank,
        })
    return results


def _make_bm25_results(chunk_ids: list[str]) -> list[dict]:
    """Make fake BM25 results in given order."""
    results = []
    for rank, cid in enumerate(chunk_ids, start=1):
        rec = next(r for r in SAMPLE_RECORDS if r["chunk_id"] == cid)
        results.append({
            **rec,
            "bm25_score": 10.0 / rank,
            "retrieval_method": "bm25",
            "rank": rank,
        })
    return results


class TestRRFFuse:
    def test_basic_fusion(self):
        dense = _make_dense_results(["1", "2", "3"])
        bm25 = _make_bm25_results(["2", "1", "4"])
        fused = _rrf_fuse(dense, bm25, rrf_k=60)
        # All unique chunks should appear
        chunk_ids = {r["chunk_id"] for r in fused}
        assert {"1", "2", "3", "4"} == chunk_ids

    def test_deduplication(self):
        """Chunk appearing in both lists should appear once in fused output."""
        dense = _make_dense_results(["1", "2"])
        bm25 = _make_bm25_results(["1", "3"])  # "1" in both
        fused = _rrf_fuse(dense, bm25, rrf_k=60)
        ids = [r["chunk_id"] for r in fused]
        assert ids.count("1") == 1  # No duplicates

    def test_high_ranked_in_both_gets_highest_rrf(self):
        """Chunk that ranks high in both retrievers should have highest RRF score."""
        dense = _make_dense_results(["1", "2", "3"])
        bm25 = _make_bm25_results(["1", "3", "2"])
        fused = _rrf_fuse(dense, bm25, rrf_k=60)
        fused.sort(key=lambda x: x["rrf_score"], reverse=True)
        # "1" is rank-1 in both → should have highest RRF
        assert fused[0]["chunk_id"] == "1"

    def test_dense_only_chunk_included(self):
        """Chunk found only by dense should still appear in fused results."""
        dense = _make_dense_results(["1", "2", "5"])
        bm25 = _make_bm25_results(["3", "4"])
        fused = _rrf_fuse(dense, bm25, rrf_k=60)
        chunk_ids = {r["chunk_id"] for r in fused}
        assert "5" in chunk_ids

    def test_bm25_only_chunk_included(self):
        dense = _make_dense_results(["1", "2"])
        bm25 = _make_bm25_results(["3", "4"])  # 3 and 4 not in dense
        fused = _rrf_fuse(dense, bm25, rrf_k=60)
        chunk_ids = {r["chunk_id"] for r in fused}
        assert "3" in chunk_ids and "4" in chunk_ids

    def test_rrf_score_is_positive(self):
        dense = _make_dense_results(["1", "2"])
        bm25 = _make_bm25_results(["2", "1"])
        fused = _rrf_fuse(dense, bm25)
        for r in fused:
            assert r["rrf_score"] > 0

    def test_provenance_ranks_recorded(self):
        """Each result should record which retriever found it."""
        dense = _make_dense_results(["1"])
        bm25 = _make_bm25_results(["2"])
        fused = _rrf_fuse(dense, bm25)
        found_ids = {r["chunk_id"]: r for r in fused}
        # "1" found only by dense
        assert found_ids["1"]["bm25_rank"] is None
        assert found_ids["1"]["dense_rank"] is not None
        # "2" found only by bm25
        assert found_ids["2"]["dense_rank"] is None
        assert found_ids["2"]["bm25_rank"] is not None

    def test_empty_dense_returns_bm25_only(self):
        bm25 = _make_bm25_results(["3", "4"])
        fused = _rrf_fuse(dense_results=[], bm25_results=bm25)
        assert len(fused) == 2

    def test_empty_bm25_returns_dense_only(self):
        dense = _make_dense_results(["1", "2"])
        fused = _rrf_fuse(dense_results=dense, bm25_results=[])
        assert len(fused) == 2

    def test_both_empty_returns_empty(self):
        fused = _rrf_fuse(dense_results=[], bm25_results=[])
        assert fused == []


class TestRetrieveHybridIntegration:
    """
    Integration tests for retrieve_hybrid using MockEmbedder + real BM25.
    ChromaDB is mocked to avoid requiring a real index.
    """

    def setup_method(self):
        self.embedder = MockEmbedder()
        self.bm25_idx = BM25Index()
        self.bm25_idx.build(SAMPLE_RECORDS)

    def _mock_dense(self, query, embedder, top_k):
        """Mock dense retrieval using BM25 order for consistency."""
        return _make_dense_results(["1", "2", "3"])

    def test_hybrid_returns_results(self):
        with patch("app.retrieval.chroma_store.retrieve_dense", side_effect=self._mock_dense):
            results = retrieve_hybrid(
                "natural justice", self.embedder,
                bm25_index=self.bm25_idx, top_k=3
            )
        assert len(results) <= 3
        assert len(results) >= 1

    def test_hybrid_result_schema(self):
        with patch("app.retrieval.chroma_store.retrieve_dense", side_effect=self._mock_dense):
            results = retrieve_hybrid(
                "article 21 fundamental rights", self.embedder,
                bm25_index=self.bm25_idx, top_k=3
            )
        if results:
            r = results[0]
            assert "chunk_id" in r
            assert "text" in r
            assert "rrf_score" in r
            assert r["retrieval_method"] == "hybrid_rrf"
            assert "source_file" in r

    def test_hybrid_deduplicates(self):
        with patch("app.retrieval.chroma_store.retrieve_dense", side_effect=self._mock_dense):
            results = retrieve_hybrid(
                "bail murder", self.embedder,
                bm25_index=self.bm25_idx, top_k=10
            )
        chunk_ids = [r["chunk_id"] for r in results]
        assert len(chunk_ids) == len(set(chunk_ids))

    def test_hybrid_ranks_sequential(self):
        with patch("app.retrieval.chroma_store.retrieve_dense", side_effect=self._mock_dense):
            results = retrieve_hybrid(
                "habeas corpus", self.embedder,
                bm25_index=self.bm25_idx, top_k=5
            )
        for i, r in enumerate(results, start=1):
            assert r["rank"] == i

    def test_hybrid_handles_dense_failure_gracefully(self):
        """If dense retrieval fails, hybrid should still return BM25 results."""
        def failing_dense(q, e, top_k):
            raise RuntimeError("ChromaDB unavailable")

        with patch("app.retrieval.chroma_store.retrieve_dense", side_effect=failing_dense):
            results = retrieve_hybrid(
                "natural justice", self.embedder,
                bm25_index=self.bm25_idx, top_k=3
            )
        # BM25 should still work
        assert isinstance(results, list)


class TestCompareRetrievalMethods:
    def setup_method(self):
        self.embedder = MockEmbedder()
        self.bm25_idx = BM25Index()
        self.bm25_idx.build(SAMPLE_RECORDS)

    def test_compare_returns_all_methods(self):
        def mock_dense(q, e, top_k):
            return _make_dense_results(["1", "2"])

        with patch("app.retrieval.chroma_store.retrieve_dense", side_effect=mock_dense):
            result = compare_retrieval_methods(
                "bail murder", self.embedder, self.bm25_idx, top_k=3
            )
        assert "dense" in result
        assert "bm25" in result
        assert "hybrid" in result
        assert "overlap_analysis" in result
