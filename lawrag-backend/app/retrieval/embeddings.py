"""
embeddings.py — Hosted embedding provider abstraction
======================================================
Provides a provider-agnostic interface for generating text embeddings.

Supported providers (configured via EMBEDDING_PROVIDER env var):
  - "huggingface"  : HuggingFace Inference API (default)
  - "mock"         : Deterministic mock for offline unit tests

Design decisions:
  - Same model used for document and query embeddings
  - Batched requests to reduce API calls
  - Exponential backoff on transient failures (429, 503, 500)
  - Failed embeddings raise, never return zeros or random vectors
  - Embeddings cached on disk using sha256(text + model_id) as key
  - API keys are read from config, never logged

IMPORTANT: Verify the model supports InferenceAPI feature-extraction before use.
The model "sentence-transformers/all-MiniLM-L6-v2" (dim=384) is confirmed to
support the HuggingFace Inference API as of the implementation date.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import pickle
import time
from pathlib import Path
from typing import TYPE_CHECKING

from app import config

logger = logging.getLogger(__name__)

# Type hint only — avoid import at module level
if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def get_embedder() -> "BaseEmbedder":
    """
    Return an embedder appropriate for the configured provider.
    Does NOT make a network call at construction time.
    """
    provider = config.EMBEDDING_PROVIDER.lower()
    if provider == "mock":
        return MockEmbedder()
    elif provider in ("huggingface", "hf"):
        return HuggingFaceEmbedder()
    else:
        raise ValueError(
            f"Unknown EMBEDDING_PROVIDER='{provider}'. "
            f"Valid options: 'huggingface', 'mock'"
        )


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class BaseEmbedder:
    """Abstract embedder interface."""

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> list[float]:
        results = self.embed_texts([text])
        return results[0]

    @property
    def model_id(self) -> str:
        raise NotImplementedError

    @property
    def dimension(self) -> int:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# HuggingFace Inference API embedder
# ---------------------------------------------------------------------------

class HuggingFaceEmbedder(BaseEmbedder):
    """
    Embeds text via the HuggingFace Inference API (feature-extraction).

    Requires:
        EMBEDDING_API_KEY  : HF read token (at minimum, anonymous works for
                             public models, but rate limits are tight)
        EMBEDDING_MODEL    : HF model repo id
        EMBEDDING_BATCH_SIZE, EMBEDDING_TIMEOUT, EMBEDDING_MAX_RETRIES
    """

    def __init__(self) -> None:
        self._model = config.EMBEDDING_MODEL
        self._api_key = config.EMBEDDING_API_KEY
        self._batch_size = config.EMBEDDING_BATCH_SIZE
        self._timeout = config.EMBEDDING_TIMEOUT
        self._max_retries = config.EMBEDDING_MAX_RETRIES
        self._cache = EmbeddingCache(config.CACHE_DIR, self._model)

        if not self._api_key:
            logger.warning(
                "EMBEDDING_API_KEY is not set. "
                "Anonymous HF Inference API requests are rate-limited. "
                "Set EMBEDDING_API_KEY to a HuggingFace token."
            )

    @property
    def model_id(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return config.EMBEDDING_DIMENSION

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a list of texts, using cache where possible.
        Batches requests to respect API limits.
        Raises on failure — never returns zeros.
        """
        results: list[list[float]] = [None] * len(texts)  # type: ignore
        uncached_indices: list[int] = []
        uncached_texts: list[str] = []

        # Check cache first
        for i, text in enumerate(texts):
            cached = self._cache.get(text)
            if cached is not None:
                results[i] = cached
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)

        if uncached_texts:
            logger.debug(
                "Embedding %d texts (%d from cache, %d uncached) via HF API…",
                len(texts), len(texts) - len(uncached_texts), len(uncached_texts)
            )
            # Process in batches
            for batch_start in range(0, len(uncached_texts), self._batch_size):
                batch = uncached_texts[batch_start: batch_start + self._batch_size]
                batch_embeddings = self._embed_batch(batch)
                for j, emb in enumerate(batch_embeddings):
                    global_idx = uncached_indices[batch_start + j]
                    results[global_idx] = emb
                    self._cache.put(uncached_texts[batch_start + j], emb)

        return results

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Call HF Inference API for one batch, with retries."""
        import requests  # always available in the project deps

        url = f"https://api-inference.huggingface.co/models/{self._model}"
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        payload = {"inputs": texts, "options": {"wait_for_model": True}}

        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                resp = requests.post(
                    url, json=payload, headers=headers, timeout=self._timeout
                )

                if resp.status_code == 200:
                    data = resp.json()
                    embeddings = self._parse_response(data, len(texts))
                    return embeddings

                elif resp.status_code in (429, 503):
                    # Rate limit or model loading — backoff and retry
                    wait = 2 ** attempt + 1
                    logger.warning(
                        "HF API returned %d on attempt %d/%d — waiting %ds",
                        resp.status_code, attempt + 1, self._max_retries + 1, wait
                    )
                    time.sleep(wait)
                    last_error = RuntimeError(
                        f"HF API status {resp.status_code}: {resp.text[:200]}"
                    )

                elif resp.status_code == 401:
                    raise PermissionError(
                        "HF API returned 401 Unauthorized. "
                        "Check your EMBEDDING_API_KEY."
                    )

                elif resp.status_code == 404:
                    raise ValueError(
                        f"HF model '{self._model}' not found (404). "
                        "Check EMBEDDING_MODEL."
                    )

                else:
                    raise RuntimeError(
                        f"HF API returned {resp.status_code}: {resp.text[:300]}"
                    )

            except requests.Timeout:
                wait = 2 ** attempt + 1
                logger.warning(
                    "HF API timeout on attempt %d/%d — waiting %ds",
                    attempt + 1, self._max_retries + 1, wait
                )
                time.sleep(wait)
                last_error = TimeoutError(f"HF API timeout after {self._timeout}s")

            except (PermissionError, ValueError):
                raise  # not retryable

            except Exception as exc:
                wait = 2 ** attempt + 1
                logger.warning(
                    "HF API error on attempt %d/%d: %s — waiting %ds",
                    attempt + 1, self._max_retries + 1, exc, wait
                )
                time.sleep(wait)
                last_error = exc

        raise RuntimeError(
            f"HF embedding failed after {self._max_retries + 1} attempts. "
            f"Last error: {last_error}"
        )

    def _parse_response(self, data: object, expected_count: int) -> list[list[float]]:
        """
        Parse HF inference API response.
        The API may return a nested list (one embedding per input) or
        a flat list (single input). Normalise to list[list[float]].
        """
        if isinstance(data, list):
            if len(data) == 0:
                raise ValueError("HF API returned empty list.")
            # Single embedding (flat list of floats)
            if isinstance(data[0], (int, float)):
                if expected_count == 1:
                    return [data]
                else:
                    raise ValueError(
                        f"HF API returned single embedding for {expected_count} inputs."
                    )
            # List of embeddings
            if isinstance(data[0], list):
                return data  # type: ignore
        raise ValueError(f"Unexpected HF API response format: {type(data)}")


# ---------------------------------------------------------------------------
# Mock embedder (for offline tests)
# ---------------------------------------------------------------------------

class MockEmbedder(BaseEmbedder):
    """
    Deterministic mock embedder for offline unit tests.
    Generates fixed-dimension vectors from text hash.
    NOT a real embedding — only for testing infrastructure.
    """

    _DIM = 384

    @property
    def model_id(self) -> str:
        return "mock/deterministic-test-embedder"

    @property
    def dimension(self) -> int:
        return self._DIM

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._hash_vector(t) for t in texts]

    def _hash_vector(self, text: str) -> list[float]:
        """Deterministic pseudo-random vector from text SHA-256."""
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        # Extend to required dimension by repeating digest bytes
        raw = list(digest)
        while len(raw) < self._DIM:
            raw.extend(raw)
        raw = raw[: self._DIM]
        # Normalize to [-1, 1]
        return [(b / 127.5) - 1.0 for b in raw]


# ---------------------------------------------------------------------------
# Embedding cache
# ---------------------------------------------------------------------------

class EmbeddingCache:
    """
    Disk-based embedding cache.
    Cache key: sha256(model_id + ":" + text)
    Stored as individual .pkl files in cache_dir/
    """

    def __init__(self, cache_dir: Path, model_id: str) -> None:
        self._dir = cache_dir
        self._model_id = model_id
        self._dir.mkdir(parents=True, exist_ok=True)

    def _key(self, text: str) -> str:
        payload = f"{self._model_id}:{text}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(self, text: str) -> list[float] | None:
        path = self._dir / (self._key(text) + ".pkl")
        if path.exists():
            try:
                with open(path, "rb") as fh:
                    return pickle.load(fh)
            except Exception:
                path.unlink(missing_ok=True)  # corrupt cache
        return None

    def put(self, text: str, embedding: list[float]) -> None:
        path = self._dir / (self._key(text) + ".pkl")
        with open(path, "wb") as fh:
            pickle.dump(embedding, fh)
