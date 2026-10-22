#!/usr/bin/env python3
"""
build_index.py — Build ChromaDB vector index and BM25 index
============================================================
Reads normalized records, generates embeddings, and populates:
  1. ChromaDB (dense semantic index)
  2. BM25 lexical index (persisted as pickle)

Requirements:
  - EMBEDDING_API_KEY must be set (or EMBEDDING_PROVIDER=mock for testing)
  - Normalized records must exist (run ingest_dataset.py first)

Usage:
    python scripts/build_index.py
    python scripts/build_index.py --provider mock        # offline test
    python scripts/build_index.py --batch-size 32
"""

import argparse
import logging
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("build_index")


def main():
    parser = argparse.ArgumentParser(
        description="Build ChromaDB and BM25 indexes for LawRAG"
    )
    parser.add_argument(
        "--provider",
        help="Override EMBEDDING_PROVIDER (e.g., 'mock' for offline test)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Embedding batch size (overrides config)",
    )
    parser.add_argument(
        "--skip-chroma",
        action="store_true",
        help="Skip ChromaDB indexing (only build BM25)",
    )
    parser.add_argument(
        "--skip-bm25",
        action="store_true",
        help="Skip BM25 indexing (only build ChromaDB)",
    )
    args = parser.parse_args()

    import os
    if args.provider:
        os.environ["EMBEDDING_PROVIDER"] = args.provider

    from app import config
    from app.retrieval.embeddings import get_embedder
    from app.retrieval.bm25 import build_bm25_index
    from app.retrieval.chroma_store import index_records

    normalized_path = config.NORMALIZED_DATA_PATH
    if not normalized_path.exists():
        print(f"\n  [ERROR] Normalized records not found: {normalized_path}")
        print(f"  Run first: python scripts/ingest_dataset.py")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  LawRAG — Index Builder")
    print(f"{'='*60}")
    print(f"  Normalized data : {normalized_path}")
    print(f"  Embedding model : {config.EMBEDDING_MODEL}")
    print(f"  ChromaDB path   : {config.CHROMA_PATH}")
    print(f"  BM25 index path : {config.BM25_INDEX_PATH}")
    print()

    # ── Embedder ───────────────────────────────────────────────────────────
    try:
        embedder = get_embedder()
        print(f"  Embedder: {embedder.__class__.__name__} (model={embedder.model_id})")
    except Exception as exc:
        print(f"  [ERROR] Failed to initialize embedder: {exc}")
        sys.exit(1)

    # ── Build BM25 index ───────────────────────────────────────────────────
    if not args.skip_bm25:
        print(f"\nSTEP 1: Building BM25 index…")
        try:
            bm25_idx = build_bm25_index(normalized_path)
            print(f"  [OK] BM25 index built: {bm25_idx.doc_count} documents")
            print(f"  [OK] Saved to: {config.BM25_INDEX_PATH}")
        except Exception as exc:
            print(f"  [ERROR] BM25 index failed: {exc}")
            logger.exception("BM25 build error")
    else:
        print("\nSTEP 1: BM25 — skipped (--skip-bm25)")

    # ── Build ChromaDB index ───────────────────────────────────────────────
    if not args.skip_chroma:
        print(f"\nSTEP 2: Building ChromaDB index…")
        if not config.embedding_api_key_configured() and config.EMBEDDING_PROVIDER != "mock":
            print(
                "  [WARN] WARNING: EMBEDDING_API_KEY is not set. "
                "Dense indexing may fail or be rate-limited.\n"
                "  Use --provider mock to test without a real API key."
            )

        batch_size = args.batch_size or config.EMBEDDING_BATCH_SIZE
        try:
            report = index_records(
                normalized_records_path=normalized_path,
                embedder=embedder,
                reports_dir=config.REPORTS_DIR,
                batch_size=batch_size,
            )
            print(f"  [OK] Total processed  : {report['total_records_processed']}")
            print(f"  [OK] Indexed          : {report['indexed']}")
            print(f"  [OK] Skipped blank    : {report['skipped_blank']}")
            print(f"  [OK] Errors           : {report['skipped_error']}")
            print(f"  [OK] Collection count : {report['collection_total_count']}")
            print(f"  [OK] Elapsed          : {report['elapsed_seconds']}s")
            print(f"  [OK] Report: {config.REPORTS_DIR / 'indexing_report.json'}")
        except Exception as exc:
            print(f"  [ERROR] ChromaDB indexing failed: {exc}")
            logger.exception("ChromaDB indexing error")
            sys.exit(1)
    else:
        print("\nSTEP 2: ChromaDB — skipped (--skip-chroma)")

    print(f"\n{'='*60}")
    print(f"  Indexing complete.")
    print(f"  Next step: python scripts/query_index.py \"your legal question\"")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
