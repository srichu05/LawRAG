"""
normalize.py — Record normalization and provenance preservation
================================================================
Transforms raw JSONL records from the dataset into a stable internal
representation while preserving all original metadata.

Internal schema (confirmed against actual dataset schema):
  {
      "chunk_id"    : str   — stable unique ID (original id cast to str)
      "text"        : str   — original legal text, unchanged
      "source_id"   : str   — original id as string (if present)
      "source_file" : str   — metadata.source (filename/path from dataset)
      "chunk_index" : int   — metadata.chunk_index
      "total_pages" : int|None — metadata.total_pages
      "metadata"    : dict  — full original metadata dict for traceability
  }

Design decisions:
  - Original text is NEVER modified (no stripping of legal wording)
  - IDs are deterministic: str(original_id) when available,
    sha256(text[:200]) when id is missing
  - Duplicates by chunk_id are reported, not silently merged
  - Missing metadata fields are set to None, not invented
  - Output saved as JSONL for easy streaming during indexing
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public normalizer
# ---------------------------------------------------------------------------

def normalize_records(
    raw_jsonl_path: Path,
    output_path: Path,
    reports_dir: Path,
    skip_blank_text: bool = True,
) -> dict[str, Any]:
    """
    Normalize raw JSONL records into the internal schema.

    Parameters
    ----------
    raw_jsonl_path  : Path to raw downloaded JSONL
    output_path     : Where to write normalized JSONL
    reports_dir     : Directory for normalization report
    skip_blank_text : Whether to skip records with no text (recommended: True)

    Returns
    -------
    dict normalization summary
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    total = valid = skipped_blank = skipped_dup = 0
    dup_ids: list[dict] = []
    seen_chunk_ids: set[str] = set()
    warnings: list[str] = []

    with open(raw_jsonl_path, "r", encoding="utf-8", errors="replace") as src_fh, \
         open(output_path, "w", encoding="utf-8") as out_fh:

        for line_num, line in enumerate(src_fh, start=1):
            total += 1
            line = line.strip()
            if not line:
                continue

            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                warnings.append(f"Line {line_num}: JSON parse error — skipping")
                continue

            normalized = _normalize_one(raw, line_num, warnings)

            text = normalized["text"]
            if skip_blank_text and not text.strip():
                skipped_blank += 1
                continue

            chunk_id = normalized["chunk_id"]
            if chunk_id in seen_chunk_ids:
                skipped_dup += 1
                dup_ids.append({"line": line_num, "chunk_id": chunk_id})
                warnings.append(
                    f"Line {line_num}: duplicate chunk_id='{chunk_id}' — skipping"
                )
                continue

            seen_chunk_ids.add(chunk_id)
            out_fh.write(json.dumps(normalized, ensure_ascii=False, default=str) + "\n")
            valid += 1

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "input_path": str(raw_jsonl_path),
        "output_path": str(output_path),
        "total_raw_lines": total,
        "normalized_records": valid,
        "skipped_blank_text": skipped_blank,
        "skipped_duplicate_id": skipped_dup,
        "duplicate_ids_sample": dup_ids[:20],
        "warnings": warnings[:50],
    }

    _save_report(report, reports_dir, "normalization_report.json")

    logger.info(
        "Normalization complete — raw=%d normalized=%d skipped_blank=%d skipped_dup=%d",
        total, valid, skipped_blank, skipped_dup,
    )
    return report


def _normalize_one(raw: dict, line_num: int, warnings: list[str]) -> dict[str, Any]:
    """Normalize a single raw record into the internal schema."""

    # ── Original ID ────────────────────────────────────────────────────────
    original_id = raw.get("id")
    source_id: str | None = str(original_id) if original_id is not None else None

    # ── Text ───────────────────────────────────────────────────────────────
    text: str = raw.get("text", "") or ""

    # ── Metadata ───────────────────────────────────────────────────────────
    raw_meta = raw.get("metadata", {}) or {}
    if not isinstance(raw_meta, dict):
        warnings.append(f"Line {line_num}: metadata is not a dict; treating as empty")
        raw_meta = {}

    chunk_index: int | None = _safe_int(raw_meta.get("chunk_index"))
    source_file: str | None = raw_meta.get("source") or None
    total_pages: int | None = _safe_int(raw_meta.get("total_pages"))

    # ── Stable chunk_id ────────────────────────────────────────────────────
    # Prefer original id; fall back to deterministic hash of text prefix
    if source_id is not None:
        chunk_id = source_id
    else:
        # Deterministic fallback: hash of first 512 chars
        chunk_id = hashlib.sha256(text[:512].encode("utf-8")).hexdigest()[:16]
        warnings.append(
            f"Line {line_num}: no original id; generated chunk_id='{chunk_id}'"
        )

    return {
        "chunk_id": chunk_id,
        "text": text,
        "source_id": source_id,
        "source_file": source_file,
        "chunk_index": chunk_index,
        "total_pages": total_pages,
        "metadata": raw_meta,  # full original metadata preserved
    }


def load_normalized_records(path: Path) -> Iterator[dict]:
    """Stream normalized records from JSONL file."""
    if not path.exists():
        raise FileNotFoundError(f"Normalized records not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def _safe_int(value: Any) -> int | None:
    """Convert value to int or return None."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _save_report(report: dict, reports_dir: Path, filename: str) -> None:
    path = reports_dir / filename
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False, default=str)
