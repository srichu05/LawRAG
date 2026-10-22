"""
LawRAG Configuration
====================
All runtime settings are loaded from environment variables (or a .env file
when python-dotenv is installed).  No secret value is ever hard-coded here.

Usage
-----
    from app.config import settings
    print(settings.HF_DATASET_ID)
"""

from __future__ import annotations

import os
from pathlib import Path

# Load .env file automatically when python-dotenv is available.
try:
    from dotenv import load_dotenv

    _env_path = Path(__file__).resolve().parents[1] / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except ImportError:
    pass  # python-dotenv not installed; rely on shell env vars


def _optional(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------
HF_DATASET_ID: str = _optional("HF_DATASET_ID", "dedol-hf/india-case-legal-rag")
HF_DATASET_REVISION: str = _optional(
    "HF_DATASET_REVISION", "cdfb7afa492729eeb4ed39e42b5442ad4748ec71"
)
HF_DATASET_SPLIT: str = _optional("HF_DATASET_SPLIT", "train")

# ---------------------------------------------------------------------------
# Embedding provider
# ---------------------------------------------------------------------------
EMBEDDING_PROVIDER: str = _optional("EMBEDDING_PROVIDER", "huggingface")
EMBEDDING_MODEL: str = _optional(
    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
EMBEDDING_API_KEY: str = _optional("EMBEDDING_API_KEY", "")
EMBEDDING_BATCH_SIZE: int = int(_optional("EMBEDDING_BATCH_SIZE", "64"))
EMBEDDING_TIMEOUT: int = int(_optional("EMBEDDING_TIMEOUT", "60"))
EMBEDDING_MAX_RETRIES: int = int(_optional("EMBEDDING_MAX_RETRIES", "3"))
EMBEDDING_DIMENSION: int = int(_optional("EMBEDDING_DIMENSION", "384"))

# ---------------------------------------------------------------------------
# Query rewriting LLM (optional)
# ---------------------------------------------------------------------------
REWRITER_PROVIDER: str = _optional("REWRITER_PROVIDER", "")
REWRITER_MODEL: str = _optional("REWRITER_MODEL", "")
REWRITER_API_KEY: str = _optional("REWRITER_API_KEY", "")
REWRITER_MAX_RETRIES: int = int(_optional("REWRITER_MAX_RETRIES", "2"))

# ---------------------------------------------------------------------------
# ChromaDB
# ---------------------------------------------------------------------------
CHROMA_MODE: str = _optional("CHROMA_MODE", "local")  # "local" | "cloud"
CHROMA_PATH: str = _optional("CHROMA_PATH", "./data/chroma")
CHROMA_COLLECTION: str = _optional("CHROMA_COLLECTION", "lawrag_chunks")
CHROMA_HOST: str = _optional("CHROMA_HOST", "")
CHROMA_API_KEY: str = _optional("CHROMA_API_KEY", "")

# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------
TOP_K: int = int(_optional("TOP_K", "5"))
BM25_TOP_K: int = int(_optional("BM25_TOP_K", "10"))
RRF_K: int = int(_optional("RRF_K", "60"))  # RRF constant
MAX_RETRIEVAL_RETRIES: int = int(_optional("MAX_RETRIEVAL_RETRIES", "1"))

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR: Path = Path(__file__).resolve().parents[1]
DATA_DIR: Path = BASE_DIR / "data"
REPORTS_DIR: Path = BASE_DIR / "reports"
CACHE_DIR: Path = DATA_DIR / "embedding_cache"
BM25_INDEX_PATH: Path = DATA_DIR / "bm25_index.pkl"
NORMALIZED_DATA_PATH: Path = DATA_DIR / "normalized_records.jsonl"


# ---------------------------------------------------------------------------
# Answer Generation LLM (Phase 2)
# ---------------------------------------------------------------------------
LLM_PROVIDER: str = _optional("LLM_PROVIDER", "mock")  # "mock" | "openai" | "groq" | "huggingface"
LLM_MODEL: str = _optional("LLM_MODEL", "gpt-4o-mini")
LLM_API_KEY: str = _optional("LLM_API_KEY", "")
LLM_BASE_URL: str = _optional("LLM_BASE_URL", "")
LLM_TIMEOUT: int = int(_optional("LLM_TIMEOUT", "30"))
LLM_TEMPERATURE: float = float(_optional("LLM_TEMPERATURE", "0.0"))
LLM_MAX_TOKENS: int = int(_optional("LLM_MAX_TOKENS", "1024"))

# Evidence assessment thresholds
EVIDENCE_MIN_SCORE: float = float(_optional("EVIDENCE_MIN_SCORE", "0.01"))
EVIDENCE_CONFIDENCE_THRESHOLD: float = float(_optional("EVIDENCE_CONFIDENCE_THRESHOLD", "0.5"))

# ---------------------------------------------------------------------------
# Derived / convenience
# ---------------------------------------------------------------------------
def embedding_api_key_configured() -> bool:
    return bool(EMBEDDING_API_KEY)


def rewriter_configured() -> bool:
    return bool(REWRITER_PROVIDER and REWRITER_MODEL and REWRITER_API_KEY)


def llm_configured() -> bool:
    if LLM_PROVIDER.lower() == "mock":
        return True
    return bool(LLM_API_KEY)
