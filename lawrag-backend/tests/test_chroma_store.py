"""
Integration tests for ChromaDB store using a temporary local collection.
Tests run with MockEmbedder — no real embedding API calls.

These tests require chromadb to be installed.
Run: pip install chromadb
"""
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["EMBEDDING_PROVIDER"] = "mock"

# Mark as integration test
pytestmark = pytest.mark.integration

try:
    import chromadb  # type: ignore
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False


SAMPLE_RECORDS = [
    {"chunk_id": "1", "text": "Murder bail section 302 IPC exceptional circumstances.",
     "source_file": "bail_murder.pdf", "source_id": "1", "chunk_index": 0, "total_pages": 5,
     "metadata": {"source": "bail_murder.pdf", "chunk_index": 0, "total_pages": 5}},
    {"chunk_id": "2", "text": "Natural justice audi alteram partem principle.",
     "source_file": "natural_justice.pdf", "source_id": "2", "chunk_index": 0, "total_pages": 3,
     "metadata": {"source": "natural_justice.pdf", "chunk_index": 0, "total_pages": 3}},
    {"chunk_id": "3", "text": "Article 21 right to life and personal liberty constitution India.",
     "source_file": "fundamental.pdf", "source_id": "3", "chunk_index": 1, "total_pages": 20,
     "metadata": {"source": "fundamental.pdf", "chunk_index": 1, "total_pages": 20}},
]


class _MockChromaCollection:
    def __init__(self, name, metadata=None):
        self.name = name
        self.metadata = dict(metadata or {})
        self.docs = {}

    def count(self):
        return len(self.docs)

    def upsert(self, ids, embeddings, documents, metadatas):
        for i, doc_id in enumerate(ids):
            self.docs[doc_id] = {
                "id": doc_id,
                "embedding": embeddings[i],
                "document": documents[i],
                "metadata": metadatas[i],
            }

    def query(self, query_embeddings, n_results=5, include=None):
        import numpy as np
        if not self.docs:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
        q_emb = np.array(query_embeddings[0], dtype=float)
        scored = []
        for doc_id, d in self.docs.items():
            emb = np.array(d["embedding"], dtype=float)
            dist = float(np.linalg.norm(q_emb - emb))
            scored.append((dist, d))
        scored.sort(key=lambda x: x[0])
        top = scored[:n_results]
        return {
            "ids": [[item[1]["id"] for item in top]],
            "documents": [[item[1]["document"] for item in top]],
            "metadatas": [[item[1]["metadata"] for item in top]],
            "distances": [[item[0] for item in top]],
        }


class _MockChromaClient:
    def __init__(self, path=None):
        self.collections = {}

    def list_collections(self):
        return list(self.collections.values())

    def get_collection(self, name):
        if name not in self.collections:
            raise ValueError(f"Collection {name} does not exist.")
        return self.collections[name]

    def create_collection(self, name, metadata=None):
        col = _MockChromaCollection(name, metadata)
        self.collections[name] = col
        return col

    def get_or_create_collection(self, name, metadata=None):
        if name in self.collections:
            return self.collections[name]
        return self.create_collection(name, metadata)


_GLOBAL_MOCK_CLIENT = _MockChromaClient()


@pytest.fixture
def chroma_tmp_path(tmp_path):
    """Provide a temporary ChromaDB path and patch the config and client."""
    chroma_dir = tmp_path / "chroma"
    chroma_dir.mkdir()
    client = _MockChromaClient() if not CHROMA_AVAILABLE else None
    with patch.dict(os.environ, {
        "CHROMA_PATH": str(chroma_dir),
        "CHROMA_MODE": "local",
        "CHROMA_COLLECTION": "test_lawrag_chunks",
        "EMBEDDING_PROVIDER": "mock",
        "EMBEDDING_MODEL": "mock/test-model",
    }):
        from importlib import reload
        import app.config as cfg
        reload(cfg)
        if not CHROMA_AVAILABLE:
            with patch("app.retrieval.chroma_store.get_chroma_client", return_value=client):
                yield chroma_dir
        else:
            yield chroma_dir


@pytest.fixture
def normalized_jsonl(tmp_path):
    """Write sample normalized records to a temp JSONL file."""
    path = tmp_path / "normalized.jsonl"
    with open(path, "w") as fh:
        for r in SAMPLE_RECORDS:
            fh.write(json.dumps(r) + "\n")
    return path


class TestChromaStoreIntegration:
    def test_index_records(self, chroma_tmp_path, normalized_jsonl):
        from app.retrieval.embeddings import MockEmbedder
        from app.retrieval.chroma_store import index_records

        embedder = MockEmbedder()
        report = index_records(
            normalized_records_path=normalized_jsonl,
            embedder=embedder,
            reports_dir=chroma_tmp_path / "reports",
            batch_size=2,
        )
        assert report["indexed"] == 3
        assert report["skipped_blank"] == 0
        assert report["collection_total_count"] == 3

    def test_idempotent_indexing(self, chroma_tmp_path, normalized_jsonl):
        """Running indexing twice should not create duplicates."""
        from app.retrieval.embeddings import MockEmbedder
        from app.retrieval.chroma_store import index_records

        embedder = MockEmbedder()
        reports = chroma_tmp_path / "reports"

        report1 = index_records(normalized_jsonl, embedder, reports, batch_size=2)
        report2 = index_records(normalized_jsonl, embedder, reports, batch_size=2)

        # Collection count should be the same after second run (upsert, not duplicate)
        assert report1["collection_total_count"] == report2["collection_total_count"]

    def test_dense_retrieval_returns_results(self, chroma_tmp_path, normalized_jsonl):
        from app.retrieval.embeddings import MockEmbedder
        from app.retrieval.chroma_store import index_records, retrieve_dense

        embedder = MockEmbedder()
        index_records(normalized_jsonl, embedder, chroma_tmp_path / "reports")

        results = retrieve_dense("bail murder section 302", embedder, top_k=3)
        assert len(results) > 0

    def test_dense_result_schema(self, chroma_tmp_path, normalized_jsonl):
        from app.retrieval.embeddings import MockEmbedder
        from app.retrieval.chroma_store import index_records, retrieve_dense

        embedder = MockEmbedder()
        index_records(normalized_jsonl, embedder, chroma_tmp_path / "reports")

        results = retrieve_dense("natural justice", embedder, top_k=1)
        assert len(results) == 1
        r = results[0]
        required = {"chunk_id", "text", "source_file", "source_id",
                    "chunk_index", "total_pages", "distance", "rank", "retrieval_method"}
        assert required.issubset(set(r.keys()))
        assert r["chunk_id"] is not None
        assert isinstance(r["distance"], float)

    def test_source_metadata_traceable(self, chroma_tmp_path, normalized_jsonl):
        from app.retrieval.embeddings import MockEmbedder
        from app.retrieval.chroma_store import index_records, retrieve_dense

        embedder = MockEmbedder()
        index_records(normalized_jsonl, embedder, chroma_tmp_path / "reports")

        results = retrieve_dense("fundamental rights article 21", embedder, top_k=3)
        for r in results:
            # Every result must have at least source_file or source_id
            has_trace = bool(r.get("source_file")) or bool(r.get("source_id"))
            assert has_trace, f"Result has no source traceability: {r['chunk_id']}"

    def test_empty_collection_returns_empty(self, chroma_tmp_path):
        """Querying an empty collection should return empty list, not raise."""
        from app.retrieval.embeddings import MockEmbedder
        from app.retrieval.chroma_store import retrieve_dense, get_chroma_client, get_or_create_collection

        embedder = MockEmbedder()
        client = get_chroma_client()
        get_or_create_collection(client, embedder.model_id, embedder.dimension)

        results = retrieve_dense("any query", embedder, top_k=5)
        assert results == []

    def test_dimension_mismatch_raises(self, chroma_tmp_path, normalized_jsonl):
        """Indexing with model A then trying to use model B should raise."""
        from app.retrieval.embeddings import MockEmbedder
        from app.retrieval.chroma_store import index_records, get_chroma_client, get_or_create_collection

        embedder = MockEmbedder()
        index_records(normalized_jsonl, embedder, chroma_tmp_path / "reports")

        # Try to get collection with different model — should detect mismatch
        client = get_chroma_client()
        with pytest.raises(ValueError, match="built with model|different model|incompatible"):
            get_or_create_collection(client, "different-model/some-model", 384)

    def test_invalid_query_raises(self, chroma_tmp_path, normalized_jsonl):
        from app.retrieval.embeddings import MockEmbedder
        from app.retrieval.chroma_store import index_records, retrieve_dense

        embedder = MockEmbedder()
        index_records(normalized_jsonl, embedder, chroma_tmp_path / "reports")

        with pytest.raises(ValueError, match="non-empty string"):
            retrieve_dense("", embedder)

    def test_indexing_report_saved(self, chroma_tmp_path, normalized_jsonl):
        from app.retrieval.embeddings import MockEmbedder
        from app.retrieval.chroma_store import index_records

        embedder = MockEmbedder()
        reports_dir = chroma_tmp_path / "reports"
        index_records(normalized_jsonl, embedder, reports_dir)
        assert (reports_dir / "indexing_report.json").exists()
