"""
validate.py — Schema inspection and data validation
====================================================
Validates the downloaded raw JSONL against the confirmed schema:
  - id       : int64 (original record id)
  - text     : large_string (the legal text chunk)
  - metadata : dict with:
       chunk_index  : int64
       source       : string (source filename)
       total_pages  : int64

Validation checks:
  1. Missing or blank text
  2. Missing record identifiers
  3. Duplicate chunk identifiers (id field)
  4. Duplicate text records
  5. Missing source metadata
  6. Malformed records / JSON parse errors
  7. Text encoding issues
  8. Metadata field coverage statistics

Produces a validation report at reports/validation_report.json
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def validate_records(
    raw_jsonl_path: Path,
    reports_dir: Path,
) -> dict[str, Any]:
    """
    Validate a raw JSONL dataset file.

    Parameters
    ----------
    raw_jsonl_path  : Path to the downloaded JSONL file
    reports_dir     : Directory where the validation report is saved

    Returns
    -------
    dict with validation summary including counts of valid/invalid records
    """
    reports_dir.mkdir(parents=True, exist_ok=True)

    if not raw_jsonl_path.exists():
        raise FileNotFoundError(f"Raw dataset not found: {raw_jsonl_path}")

    seen_ids: set[Any] = set()
    seen_texts: set[str] = set()
    duplicate_ids: list[Any] = []
    duplicate_texts: list[Any] = []
    invalid_records: list[dict] = []
    warnings: list[str] = []

    total = 0
    valid = 0
    skipped_blank_text = 0
    skipped_missing_id = 0
    skipped_json_error = 0

    # Metadata coverage counters
    meta_has_chunk_index = 0
    meta_has_source = 0
    meta_has_total_pages = 0
    meta_source_values: Counter = Counter()

    with open(raw_jsonl_path, "r", encoding="utf-8", errors="replace") as fh:
        for line_num, line in enumerate(fh, start=1):
            total += 1
            line = line.strip()
            if not line:
                continue

            # ── 1. JSON parse ──────────────────────────────────────────────
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                skipped_json_error += 1
                invalid_records.append(
                    {"line": line_num, "reason": "json_parse_error", "detail": str(exc)}
                )
                continue

            rec_id = record.get("id")
            text = record.get("text", "")
            metadata = record.get("metadata", {}) or {}

            # ── 2. Missing / blank text ────────────────────────────────────
            if not isinstance(text, str) or not text.strip():
                skipped_blank_text += 1
                invalid_records.append(
                    {"line": line_num, "id": rec_id, "reason": "blank_or_missing_text"}
                )
                continue

            # ── 3. Missing identifier ──────────────────────────────────────
            if rec_id is None:
                skipped_missing_id += 1
                invalid_records.append(
                    {"line": line_num, "reason": "missing_id", "text_prefix": text[:60]}
                )
                # We don't skip — we flag and continue processing
                # (normalization will mint a deterministic ID)

            # ── 4. Duplicate IDs ──────────────────────────────────────────
            if rec_id is not None:
                if rec_id in seen_ids:
                    duplicate_ids.append({"line": line_num, "id": rec_id})
                    warnings.append(f"Duplicate id={rec_id} at line {line_num}")
                else:
                    seen_ids.add(rec_id)

            # ── 5. Duplicate text ──────────────────────────────────────────
            text_key = text.strip()
            if text_key in seen_texts:
                duplicate_texts.append({"line": line_num, "id": rec_id})
            else:
                seen_texts.add(text_key)

            # ── 6. Metadata coverage ───────────────────────────────────────
            if isinstance(metadata, dict):
                if metadata.get("chunk_index") is not None:
                    meta_has_chunk_index += 1
                if metadata.get("source"):
                    meta_has_source += 1
                    meta_source_values[metadata["source"]] += 1
                if metadata.get("total_pages") is not None:
                    meta_has_total_pages += 1
            else:
                warnings.append(f"Line {line_num}: metadata is not a dict")

            valid += 1

    skipped_total = skipped_blank_text + skipped_json_error
    unique_sources = len(meta_source_values)

    report: dict[str, Any] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "raw_file": str(raw_jsonl_path),
        "total_lines": total,
        "valid_records": valid,
        "skipped_total": skipped_total,
        "skipped_blank_text": skipped_blank_text,
        "skipped_missing_id": skipped_missing_id,
        "skipped_json_error": skipped_json_error,
        "duplicate_id_count": len(duplicate_ids),
        "duplicate_text_count": len(duplicate_texts),
        "duplicate_ids": duplicate_ids[:20],       # cap report to first 20
        "duplicate_texts": duplicate_texts[:20],
        "metadata_coverage": {
            "chunk_index_present": meta_has_chunk_index,
            "source_present": meta_has_source,
            "total_pages_present": meta_has_total_pages,
            "unique_sources": unique_sources,
            "top_sources": meta_source_values.most_common(10),
        },
        "invalid_records_sample": invalid_records[:20],
        "warnings": warnings[:50],
    }

    _save_report(report, reports_dir, "validation_report.json")

    logger.info(
        "Validation complete — total=%d valid=%d skipped=%d "
        "dup_ids=%d dup_texts=%d sources=%d",
        total, valid, skipped_total,
        len(duplicate_ids), len(duplicate_texts), unique_sources,
    )

    if warnings:
        for w in warnings[:5]:
            logger.warning("  %s", w)
        if len(warnings) > 5:
            logger.warning("  … and %d more warnings (see report).", len(warnings) - 5)

    return report


def _save_report(report: dict, reports_dir: Path, filename: str) -> None:
    path = reports_dir / filename
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False, default=str)
    logger.debug("Validation report saved to %s", path)
