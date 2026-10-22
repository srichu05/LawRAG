#!/usr/bin/env python3
"""
ingest_dataset.py — Download, validate, and normalize the dataset
=================================================================
Runs the complete data pipeline:
  1. Download dataset from Hugging Face
  2. Validate records
  3. Normalize into internal schema
  4. Save ingestion report

This script is intentionally kept separate from embedding/indexing.
It can run without an EMBEDDING_API_KEY configured.

Usage:
    python scripts/ingest_dataset.py
    python scripts/ingest_dataset.py --force-redownload
"""

import argparse
import json
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
logger = logging.getLogger("ingest_dataset")


def main():
    parser = argparse.ArgumentParser(
        description="Download, validate, and normalize the LawRAG dataset"
    )
    parser.add_argument(
        "--force-redownload",
        action="store_true",
        help="Re-download even if raw data already exists",
    )
    parser.add_argument(
        "--skip-normalize",
        action="store_true",
        help="Only download and validate, skip normalization",
    )
    args = parser.parse_args()

    from app import config
    from app.ingestion.download import download_dataset
    from app.ingestion.validate import validate_records
    from app.ingestion.normalize import normalize_records

    raw_path = config.DATA_DIR / "raw_dataset.jsonl"
    reports_dir = config.REPORTS_DIR

    print(f"\n{'='*60}")
    print(f"  LawRAG — Dataset Ingestion Pipeline")
    print(f"{'='*60}")
    print(f"  Dataset : {config.HF_DATASET_ID}")
    print(f"  Revision: {config.HF_DATASET_REVISION}")
    print(f"  Split   : {config.HF_DATASET_SPLIT}")
    print(f"  Output  : {raw_path}")
    print()

    # ── Step 1: Download ───────────────────────────────────────────────────
    print("STEP 1: Downloading dataset…")
    try:
        dl_report = download_dataset(
            dataset_id=config.HF_DATASET_ID,
            revision=config.HF_DATASET_REVISION,
            split=config.HF_DATASET_SPLIT,
            output_path=raw_path,
            reports_dir=reports_dir,
            force_redownload=args.force_redownload,
        )
        status = dl_report.get("status", "unknown")
        count = dl_report.get("record_count", "?")
        print(f"  [OK] Download complete: {count} records (status={status})")
        print(f"  [OK] Report: {reports_dir / 'download_report.json'}")
    except Exception as exc:
        print(f"  [ERROR] Download failed: {exc}")
        sys.exit(1)

    # ── Step 2: Validate ───────────────────────────────────────────────────
    print("\nSTEP 2: Validating records…")
    try:
        val_report = validate_records(
            raw_jsonl_path=raw_path,
            reports_dir=reports_dir,
        )
        print(f"  [OK] Total records  : {val_report['total_lines']}")
        print(f"  [OK] Valid records  : {val_report['valid_records']}")
        print(f"  [OK] Skipped        : {val_report['skipped_total']}")
        print(f"  [OK] Duplicate IDs  : {val_report['duplicate_id_count']}")
        print(f"  [OK] Duplicate texts: {val_report['duplicate_text_count']}")
        print(f"  [OK] Sources found  : {val_report['metadata_coverage']['unique_sources']}")
        print(f"  [OK] Report: {reports_dir / 'validation_report.json'}")
        if val_report.get("warnings"):
            print(f"  [WARN] Warnings: {len(val_report['warnings'])}")
    except Exception as exc:
        print(f"  [ERROR] Validation failed: {exc}")
        sys.exit(1)

    if args.skip_normalize:
        print("\n  --skip-normalize specified. Stopping after validation.")
        return

    # ── Step 3: Normalize ──────────────────────────────────────────────────
    print("\nSTEP 3: Normalizing records…")
    try:
        norm_report = normalize_records(
            raw_jsonl_path=raw_path,
            output_path=config.NORMALIZED_DATA_PATH,
            reports_dir=reports_dir,
        )
        print(f"  [OK] Normalized records : {norm_report['normalized_records']}")
        print(f"  [OK] Skipped blank text : {norm_report['skipped_blank_text']}")
        print(f"  [OK] Skipped duplicates : {norm_report['skipped_duplicate_id']}")
        print(f"  [OK] Output: {norm_report['output_path']}")
        print(f"  [OK] Report: {reports_dir / 'normalization_report.json'}")
    except Exception as exc:
        print(f"  [ERROR] Normalization failed: {exc}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  Ingestion pipeline complete.")
    print(f"  Next step: python scripts/build_index.py")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
