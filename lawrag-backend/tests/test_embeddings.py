"""
Tests for the embedding module.
Uses MockEmbedder for all tests — no network or API calls.
"""
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["EMBEDDING_PROVIDER"] = "mock"

from app.retrieval.embeddings import MockEmbedder, HuggingFaceEmbedder, get_embedder, EmbeddingCache


class TestMockEmbedder:
    def test_returns_list_of_floats(self):
        emb = MockEmbedder()
        result = emb.embed_texts(["Test legal text"])
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], list)
        assert all(isinstance(v, float) for v in result[0])

    def test_correct_dimension(self):
        emb = MockEmbedder()
        result = emb.embed_texts(["text one", "text two"])
        assert len(result) == 2
        assert len(result[0]) == 384
        assert len(result[1]) == 384

    def test_deterministic(self):
        """Same text must always produce the same vector."""
        emb = MockEmbedder()
        text = "The court held that due process is essential."
        v1 = emb.embed_texts([text])[0]
        v2 = emb.embed_texts([text])[0]
        assert v1 == v2

    def test_different_texts_different_vectors(self):
        emb = MockEmbedder()
        v1 = emb.embed_texts(["natural justice hearing"])[0]
        v2 = emb.embed_texts(["bail application section 302"])[0]
        assert v1 != v2

    def test_embed_query(self):
        emb = MockEmbedder()
        result = emb.embed_query("What is natural justice?")
        assert isinstance(result, list)
        assert len(result) == 384

    def test_empty_batch(self):
        emb = MockEmbedder()
        result = emb.embed_texts([])
        assert result == []

    def test_model_id(self):
        emb = MockEmbedder()
        assert "mock" in emb.model_id.lower()

    def test_dimension_property(self):
        emb = MockEmbedder()
        assert emb.dimension == 384


class TestGetEmbedder:
    def test_returns_mock_when_provider_is_mock(self):
        with patch.dict(os.environ, {"EMBEDDING_PROVIDER": "mock"}):
            from importlib import reload
            import app.config as cfg
            reload(cfg)
            from app.retrieval.embeddings import get_embedder as _ge
            emb = _ge()
            assert isinstance(emb, MockEmbedder)

    def test_invalid_provider_raises(self):
        with patch.dict(os.environ, {"EMBEDDING_PROVIDER": "unknown_provider"}):
            from importlib import reload
            import app.config as cfg
            reload(cfg)
            with pytest.raises(ValueError, match="Unknown EMBEDDING_PROVIDER"):
                from app.retrieval.embeddings import get_embedder as _ge
                _ge()


class TestEmbeddingCache:
    def test_cache_stores_and_retrieves(self, tmp_path):
        cache = EmbeddingCache(tmp_path / "cache", "test-model")
        text = "section 302 ipc"
        emb = [0.1, 0.2, 0.3]
        cache.put(text, emb)
        result = cache.get(text)
        assert result == emb

    def test_cache_miss_returns_none(self, tmp_path):
        cache = EmbeddingCache(tmp_path / "cache", "test-model")
        result = cache.get("text not in cache")
        assert result is None

    def test_cache_key_includes_model(self, tmp_path):
        """Same text with different models should not collide."""
        cache1 = EmbeddingCache(tmp_path / "cache", "model-A")
        cache2 = EmbeddingCache(tmp_path / "cache", "model-B")
        text = "same text"
        cache1.put(text, [1.0, 2.0])
        cache2.put(text, [3.0, 4.0])
        assert cache1.get(text) == [1.0, 2.0]
        assert cache2.get(text) == [3.0, 4.0]

    def test_corrupt_cache_returns_none(self, tmp_path):
        """Corrupt pickle files should not crash — return None instead."""
        cache = EmbeddingCache(tmp_path / "cache", "model")
        text = "test text"
        import hashlib
        key = hashlib.sha256(f"model:{text}".encode()).hexdigest()
        corrupt_file = tmp_path / "cache" / (key + ".pkl")
        corrupt_file.parent.mkdir(parents=True, exist_ok=True)
        corrupt_file.write_bytes(b"not a valid pickle")
        result = cache.get(text)
        assert result is None


class TestHuggingFaceEmbedderRetry:
    """Test retry and error handling without making real network calls."""

    def _make_embedder(self):
        """Create HF embedder with test config."""
        with patch.dict(os.environ, {
            "EMBEDDING_PROVIDER": "huggingface",
            "EMBEDDING_API_KEY": "test-key",
            "EMBEDDING_MODEL": "sentence-transformers/all-MiniLM-L6-v2",
            "EMBEDDING_MAX_RETRIES": "2",
            "EMBEDDING_BATCH_SIZE": "2",
        }):
            from importlib import reload
            import app.config as cfg
            reload(cfg)
            return HuggingFaceEmbedder()

    def test_raises_on_401(self):
        embedder = self._make_embedder()
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        with patch("requests.post", return_value=mock_resp):
            with pytest.raises(PermissionError, match="401"):
                embedder._embed_batch(["text"])

    def test_raises_on_404(self):
        embedder = self._make_embedder()
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.text = "Not found"
        with patch("requests.post", return_value=mock_resp):
            with pytest.raises(ValueError, match="not found"):
                embedder._embed_batch(["text"])

    def test_retries_on_429_then_fails(self):
        """429 should trigger retries and eventually raise."""
        embedder = self._make_embedder()
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.text = "Rate limited"
        with patch("requests.post", return_value=mock_resp), \
             patch("time.sleep"):  # speed up test
            with pytest.raises(RuntimeError, match="failed after"):
                embedder._embed_batch(["text"])

    def test_never_returns_zeros_on_failure(self):
        """Failures must raise, not return zero/empty vectors."""
        embedder = self._make_embedder()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal server error"
        with patch("requests.post", return_value=mock_resp), \
             patch("time.sleep"):
            with pytest.raises((RuntimeError, Exception)):
                embedder._embed_batch(["text"])
