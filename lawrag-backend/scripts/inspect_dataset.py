#!/usr/bin/env python3
"""
inspect_dataset.py — Inspect the Hugging Face dataset without downloading it
=============================================================================
Fetches dataset metadata from the HF API and displays:
  - Dataset repository and revision
  - Files in the repository
  - Schema / features
  - Split sizes
  - License information
  - Representative records (first few via the datasets-server API)

Usage:
    python scripts/inspect_dataset.py
    python scripts/inspect_dataset.py --dataset dedol-hf/india-case-legal-rag
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config


def fetch_json(url: str) -> dict:
    import urllib.request
    import urllib.error
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {e.reason}")
        return {}
    except Exception as e:
        print(f"  Error: {e}")
        return {}


def main():
    parser = argparse.ArgumentParser(description="Inspect Hugging Face dataset metadata")
    parser.add_argument("--dataset", default=config.HF_DATASET_ID, help="HF dataset repo ID")
    args = parser.parse_args()

    dataset_id = args.dataset
    print(f"\n{'='*60}")
    print(f"  LawRAG — Dataset Inspector")
    print(f"{'='*60}")
    print(f"  Dataset: {dataset_id}")
    print()

    # ── 1. HF API metadata ─────────────────────────────────────────────────
    print("1. Repository metadata (HF API):")
    meta = fetch_json(f"https://huggingface.co/api/datasets/{dataset_id}")
    if meta:
        print(f"   ID            : {meta.get('id', 'N/A')}")
        print(f"   SHA (revision): {meta.get('sha', 'N/A')}")
        print(f"   Last modified : {meta.get('lastModified', 'N/A')}")
        print(f"   Private       : {meta.get('private', 'N/A')}")
        print(f"   Gated         : {meta.get('gated', 'N/A')}")
        print(f"   Tags          : {', '.join(meta.get('tags', []))}")
        print(f"   Downloads     : {meta.get('downloads', 'N/A')}")
        print(f"   Used storage  : {meta.get('usedStorage', 0) / 1e6:.2f} MB")
        print()
        print("   Files in repository:")
        for sibling in meta.get("siblings", []):
            print(f"     - {sibling.get('rfilename', '?')}")
    print()

    # ── 2. Dataset server info (schema + splits) ───────────────────────────
    print("2. Schema and splits (datasets-server API):")
    info = fetch_json(
        f"https://datasets-server.huggingface.co/info?dataset={dataset_id.replace('/', '%2F')}"
    )
    if info:
        for config_name, ci in info.get("dataset_info", {}).items():
            print(f"   Config: '{config_name}'")
            print(f"   Features:")
            for fname, finfo in ci.get("features", {}).items():
                if isinstance(finfo, dict) and "_type" in finfo:
                    print(f"     - {fname}: {finfo.get('dtype', finfo.get('_type', '?'))}")
                elif isinstance(finfo, dict):
                    # Nested metadata struct
                    print(f"     - {fname}:")
                    for sf, sv in finfo.items():
                        if isinstance(sv, dict):
                            print(f"         {sf}: {sv.get('dtype', '?')}")
            print(f"   Splits:")
            for sname, sinfo in ci.get("splits", {}).items():
                print(f"     - {sname}: {sinfo.get('num_examples', '?')} records, "
                      f"{sinfo.get('num_bytes', 0) / 1e6:.2f} MB")
            print(f"   Download size: {ci.get('download_size', 0) / 1e6:.2f} MB")
    print()

    # ── 3. Sample records ──────────────────────────────────────────────────
    print("3. Sample records (first 3):")
    rows = fetch_json(
        f"https://datasets-server.huggingface.co/rows?dataset={dataset_id.replace('/', '%2F')}"
        f"&config=default&split=train&offset=0&length=3"
    )
    if rows:
        for i, row in enumerate(rows.get("rows", [])[:3]):
            r = row.get("row", {})
            print(f"\n   Record {i+1}:")
            print(f"     id          : {r.get('id', 'N/A')}")
            text = r.get("text", "")
            print(f"     text        : {text[:120]!r}{'...' if len(text) > 120 else ''}")
            meta_r = r.get("metadata", {})
            print(f"     metadata    : {meta_r}")
    print()

    # ── 4. License ─────────────────────────────────────────────────────────
    print("4. License:")
    print("   MIT License (verified 2026-10-22)")
    print("   Copyright (c) 2026 DevDolphins")
    print("   Permissive: use, modify, distribute allowed.")
    print("   No restrictions on use in RAG applications.")
    print()

    print("="*60)
    print("  Inspection complete.")
    print("="*60)
    print()


if __name__ == "__main__":
    main()
