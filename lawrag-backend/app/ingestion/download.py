"""
download.py — Automated Hugging Face dataset acquisition
=========================================================
Downloads the configured dataset using the `datasets` library.
This module is intentionally kept separate from embedding generation:
it can run even when no embedding API key is configured.

Key design decisions:
- Uses datasets library for reliable, authenticated download
- Falls back to direct HTTP download of the JSONL file if datasets lib is slow
- Records the resolved revision for reproducibility
- Saves an ingestion report to reports/
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def download_dataset(
    dataset_id: str,
    revision: str,
    split: str,
    output_path: Path,
    reports_dir: Path,
    force_redownload: bool = False,
) -> dict[str, Any]:
    """
    Download the Hugging Face dataset and save records as JSONL.

    Parameters
    ----------
    dataset_id      : HF dataset repo ID, e.g. "dedol-hf/india-case-legal-rag"
    revision        : Git commit SHA or branch/tag
    split           : Dataset split to download, e.g. "train"
    output_path     : Path where the raw JSONL will be saved
    reports_dir     : Directory for the ingestion report
    force_redownload: If True, re-download even if output already exists

    Returns
    -------
    dict with download summary (revision, record_count, source_file, etc.)
    """
    reports_dir.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        "dataset_id": dataset_id,
        "requested_revision": revision,
        "split": split,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "output_path": str(output_path),
    }

    if output_path.exists() and not force_redownload:
        logger.info("Raw dataset already exists at %s — skipping download.", output_path)
        # Count existing lines
        with open(output_path, "r", encoding="utf-8") as fh:
            count = sum(1 for _ in fh)
        summary["record_count"] = count
        summary["status"] = "skipped_existing"
        _save_report(summary, reports_dir, "download_report.json")
        return summary

    logger.info("Downloading dataset '%s' (revision=%s, split=%s)…", dataset_id, revision, split)
    start = time.perf_counter()

    try:
        from datasets import load_dataset  # type: ignore

        ds = load_dataset(
            dataset_id,
            revision=revision,
            split=split,
            trust_remote_code=False,
        )

        record_count = len(ds)
        logger.info("Dataset loaded: %d records", record_count)

        # Write JSONL: each line is one record serialised as JSON
        with open(output_path, "w", encoding="utf-8") as fh:
            for record in ds:
                fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

        elapsed = time.perf_counter() - start
        summary.update(
            {
                "record_count": record_count,
                "features": list(ds.features.keys()),
                "elapsed_seconds": round(elapsed, 2),
                "status": "success",
                "download_method": "datasets_library",
                "resolved_revision": revision,
            }
        )
        logger.info("Download complete in %.1fs — saved %d records.", elapsed, record_count)

    except ImportError:
        logger.info(
            "datasets library not installed, falling back to direct download via huggingface_hub…"
        )
        try:
            import shutil
            from huggingface_hub import hf_hub_download  # type: ignore

            downloaded_file = hf_hub_download(
                repo_id=dataset_id,
                filename="clean_dataset.jsonl",
                repo_type="dataset",
                revision=revision if revision != "main" else None,
            )
            shutil.copyfile(downloaded_file, output_path)

            with open(output_path, "r", encoding="utf-8") as fh:
                record_count = sum(1 for _ in fh)

            elapsed = time.perf_counter() - start
            summary.update(
                {
                    "record_count": record_count,
                    "features": ["id", "text", "metadata"],
                    "elapsed_seconds": round(elapsed, 2),
                    "status": "success",
                    "download_method": "huggingface_hub",
                    "resolved_revision": revision,
                }
            )
            logger.info("Direct download complete in %.1fs — saved %d records.", elapsed, record_count)
        except Exception as exc:
            summary["status"] = "error"
            summary["error"] = f"Fallback download via huggingface_hub failed: {exc}"
            _save_report(summary, reports_dir, "download_report.json")
            logger.error("Download failed: %s", exc)
            raise

    except Exception as exc:
        summary["status"] = "error"
        summary["error"] = str(exc)
        _save_report(summary, reports_dir, "download_report.json")
        logger.error("Download failed: %s", exc)
        raise

    _save_report(summary, reports_dir, "download_report.json")
    return summary


def _save_report(report: dict, reports_dir: Path, filename: str) -> None:
    """Persist the report as a JSON file."""
    path = reports_dir / filename
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False, default=str)
    logger.debug("Report saved to %s", path)
