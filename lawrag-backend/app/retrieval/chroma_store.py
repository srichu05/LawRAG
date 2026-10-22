"""
chroma_store.py — Persistent ChromaDB indexing and dense retrieval
===================================================================
Manages the ChromaDB collection storing:
  - chunk_id as document ID
  - text as document content
  - embedding vector
  - scalar metadata (source_file, chunk_index, total_pages, source_id)

Design decisions:
  - Idempotent indexing: uses upsert semantics
  - Batched writes to manage memory
  - Detects incompatible embedding dimensions before writing
  - Records dataset revision and embedding model in collection metadata
  - Keeps indexing and query execution separate

Note: CHROMA_PATH is a local directory path. For production deployment,
configure a managed ChromaDB (Chroma Cloud) via CHROMA_HOST / CHROMA_API_KEY.
Local filesystem is NOT durable on Render free tier — Phase 3 concern.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from app import config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Collection management
# ---------------------------------------------------------------------------

def get_chroma_client():
    """Return a configured ChromaDB client (local or cloud)."""
    import chromadb  # type: ignore

    mode = config.CHROMA_MODE.lower()
    if mode == "local":
        path = str(Path(config.CHROMA_PATH).resolve())
        logger.debug("ChromaDB client: local PersistentClient at %s", path)
        return chromadb.PersistentClient(path=path)
    elif mode == "cloud":
        if not config.CHROMA_HOST:
            raise EnvironmentError(
                "CHROMA_MODE=cloud requires CHROMA_HOST to be set."
            )
        logger.debug("ChromaDB client: HttpClient at %s", config.CHROMA_HOST)
        return chromadb.HttpClient(
            host=config.CHROMA_HOST,
            headers={"X-Chroma-Token": config.CHROMA_API_KEY}
            if config.CHROMA_API_KEY
            else {},
        )
    else:
        raise ValueError(f"Unknown CHROMA_MODE='{mode}'. Use 'local' or 'cloud'.")


def get_or_create_collection(client, embedding_model_id: str, dimension: int):
    """
    Get an existing collection or create one with validated metadata.
    Raises if an existing collection was built with a different embedding model.
    """
    collection_name = config.CHROMA_COLLECTION

    existing_names = [c.name for c in client.list_collections()]

    if collection_name in existing_names:
        col = client.get_collection(collection_name)
        stored_model = col.metadata.get("embedding_model", "")
        stored_dim = col.metadata.get("embedding_dimension", -1)

        if stored_model and stored_model != embedding_model_id:
            raise ValueError(
                f"Existing collection '{collection_name}' was built with model "
                f"'{stored_model}', but current EMBEDDING_MODEL is '{embedding_model_id}'. "
                f"Delete the collection or change CHROMA_COLLECTION to use a new collection."
            )

        if stored_dim and stored_dim != dimension:
            raise ValueError(
                f"Existing collection has dimension {stored_dim}, "
                f"but current model produces dimension {dimension}. "
                f"Delete the collection or use a compatible model."
            )

        logger.info(
            "Using existing ChromaDB collection '%s' (model=%s, count=%d)",
            collection_name, stored_model or "unknown", col.count()
        )
        return col

    else:
        meta = {
            "embedding_model": embedding_model_id,
            "embedding_dimension": dimension,
            "dataset_id": config.HF_DATASET_ID,
            "dataset_revision": config.HF_DATASET_REVISION,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        col = client.create_collection(
            name=collection_name,
            metadata=meta,
        )
        logger.info(
            "Created ChromaDB collection '%s' (model=%s, dim=%d)",
            collection_name, embedding_model_id, dimension
        )
        return col


# ---------------------------------------------------------------------------
# Indexing
# ---------------------------------------------------------------------------

def index_records(
    normalized_records_path: Path,
    embedder,
    reports_dir: Path,
    batch_size: int = 64,
) -> dict[str, Any]:
    """
    Index normalized records into ChromaDB.

    Uses upsert semantics — safe to rerun without creating duplicates.
    Embeds documents in batches.
    Skips records with blank text.

    Returns indexing summary dict.
    """
    from app.ingestion.normalize import load_normalized_records

    client = get_chroma_client()
    collection = get_or_create_collection(
        client, embedder.model_id, embedder.dimension
    )

    total = indexed = skipped_blank = skipped_error = 0
    errors: list[str] = []

    # Buffer for batch upsert
    batch_ids: list[str] = []
    batch_texts: list[str] = []
    batch_metas: list[dict] = []

    def flush_batch() -> None:
        nonlocal indexed, skipped_error
        if not batch_ids:
            return
        try:
            embeddings = embedder.embed_texts(batch_texts)
            collection.upsert(
                ids=batch_ids,
                embeddings=embeddings,
                documents=batch_texts,
                metadatas=batch_metas,
            )
            indexed += len(batch_ids)
            logger.debug("Upserted batch of %d records (total=%d)", len(batch_ids), indexed)
        except Exception as exc:
            skipped_error += len(batch_ids)
            errors.append(f"Batch upsert error: {exc}")
            logger.error("Batch upsert failed: %s", exc)
        finally:
            batch_ids.clear()
            batch_texts.clear()
            batch_metas.clear()

    start = time.perf_counter()

    for record in load_normalized_records(normalized_records_path):
        total += 1
        text = record.get("text", "").strip()
        if not text:
            skipped_blank += 1
            continue

        chunk_id = record["chunk_id"]
        meta = _build_chroma_metadata(record)

        batch_ids.append(chunk_id)
        batch_texts.append(record["text"])  # preserve original (not stripped)
        batch_metas.append(meta)

        if len(batch_ids) >= batch_size:
            flush_batch()

    flush_batch()  # Remaining records

    elapsed = time.perf_counter() - start
    collection_count = collection.count()

    report = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "collection_name": config.CHROMA_COLLECTION,
        "embedding_model": embedder.model_id,
        "embedding_dimension": embedder.dimension,
        "dataset_revision": config.HF_DATASET_REVISION,
        "total_records_processed": total,
        "indexed": indexed,
        "skipped_blank": skipped_blank,
        "skipped_error": skipped_error,
        "collection_total_count": collection_count,
        "elapsed_seconds": round(elapsed, 2),
        "errors_sample": errors[:10],
    }

    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / "indexing_report.json"
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False, default=str)

    logger.info(
        "Indexing complete — total=%d indexed=%d skipped_blank=%d "
        "skipped_error=%d collection_count=%d elapsed=%.1fs",
        total, indexed, skipped_blank, skipped_error, collection_count, elapsed
    )
    return report


def _build_chroma_metadata(record: dict) -> dict:
    """
    Build ChromaDB-compatible metadata dict (scalar values only).
    ChromaDB requires: str, int, float, or bool — no None, no nested dicts.
    """
    meta: dict[str, Any] = {}

    def _str(v) -> str:
        return str(v) if v is not None else ""

    def _int(v) -> int:
        try:
            return int(v)
        except (TypeError, ValueError):
            return -1

    meta["source_id"] = _str(record.get("source_id"))
    meta["source_file"] = _str(record.get("source_file"))
    meta["chunk_index"] = _int(record.get("chunk_index"))
    meta["total_pages"] = _int(record.get("total_pages"))

    return meta


# ---------------------------------------------------------------------------
# Dense retrieval
# ---------------------------------------------------------------------------

def retrieve_dense(
    query: str,
    embedder,
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    """
    Dense semantic retrieval from ChromaDB.

    Parameters
    ----------
    query    : User query string
    embedder : Configured BaseEmbedder instance
    top_k    : Number of results (defaults to config.TOP_K)

    Returns
    -------
    list of result dicts with keys:
        chunk_id, text, source_file, source_id, chunk_index,
        total_pages, distance, rank
    """
    if top_k is None:
        top_k = config.TOP_K

    # ── Input validation ────────────────────────────────────────────────────
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    if not isinstance(top_k, int) or top_k < 1:
        raise ValueError(f"top_k must be a positive integer, got {top_k!r}")
    top_k = min(top_k, 100)  # hard cap

    client = get_chroma_client()
    collection = _get_existing_collection(client)

    if collection.count() == 0:
        logger.warning("ChromaDB collection '%s' is empty.", config.CHROMA_COLLECTION)
        return []

    # Embed only the query at retrieval time
    query_embedding = embedder.embed_query(query.strip())

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    return _format_results(results, "dense")


def _get_existing_collection(client):
    """Get collection or raise with a helpful message."""
    try:
        return client.get_collection(config.CHROMA_COLLECTION)
    except Exception:
        raise RuntimeError(
            f"ChromaDB collection '{config.CHROMA_COLLECTION}' does not exist. "
            f"Run the indexing script first: python scripts/build_index.py"
        )


def _format_results(chroma_results: dict, retrieval_method: str) -> list[dict[str, Any]]:
    """Convert ChromaDB query results into the standard result schema."""
    ids = chroma_results.get("ids", [[]])[0]
    docs = chroma_results.get("documents", [[]])[0]
    metas = chroma_results.get("metadatas", [[]])[0]
    distances = chroma_results.get("distances", [[]])[0]

    output = []
    for rank, (cid, doc, meta, dist) in enumerate(
        zip(ids, docs, metas, distances), start=1
    ):
        output.append({
            "chunk_id": cid,
            "text": doc,
            "source_file": meta.get("source_file") or None,
            "source_id": meta.get("source_id") or None,
            "chunk_index": meta.get("chunk_index", -1),
            "total_pages": meta.get("total_pages", -1),
            "distance": float(dist),
            "retrieval_method": retrieval_method,
            "rank": rank,
        })

    return output
