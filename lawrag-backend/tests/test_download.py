"""
test_download.py — Unit tests for dataset acquisition
======================================================
Tests verify:
  - Existing raw file skips download (idempotency)
  - Success reports are written to disk
  - Fallback mechanism when datasets library is missing
  - Error handling when network fails
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.ingestion.download import download_dataset


SAMPLE_DATA = [
    {"id": 1, "text": "Judgment 1", "metadata": {"source": "doc1.pdf", "chunk_index": 0, "total_pages": 1}},
    {"id": 2, "text": "Judgment 2", "metadata": {"source": "doc2.pdf", "chunk_index": 0, "total_pages": 2}},
]


def test_skip_existing_file(tmp_path):
    output_path = tmp_path / "raw.jsonl"
    reports_dir = tmp_path / "reports"
    output_path.write_text("{\"id\": 1}\n{\"id\": 2}\n", encoding="utf-8")

    summary = download_dataset(
        dataset_id="test/repo",
        revision="main",
        split="train",
        output_path=output_path,
        reports_dir=reports_dir,
        force_redownload=False,
    )

    assert summary["status"] == "skipped_existing"
    assert summary["record_count"] == 2
    assert (reports_dir / "download_report.json").exists()


def test_force_redownload_with_huggingface_hub(tmp_path):
    output_path = tmp_path / "raw.jsonl"
    reports_dir = tmp_path / "reports"
    source_file = tmp_path / "source.jsonl"
    with open(source_file, "w", encoding="utf-8") as fh:
        for item in SAMPLE_DATA:
            fh.write(json.dumps(item) + "\n")

    # Simulate datasets missing to trigger huggingface_hub fallback
    with patch.dict("sys.modules", {"datasets": None}):
        with patch("huggingface_hub.hf_hub_download", return_value=str(source_file)) as mock_hub:
            summary = download_dataset(
                dataset_id="dedol-hf/india-case-legal-rag",
                revision="cdfb7afa492729eeb4ed39e42b5442ad4748ec71",
                split="train",
                output_path=output_path,
                reports_dir=reports_dir,
                force_redownload=True,
            )
            assert summary["status"] == "success"
            assert summary["record_count"] == 2
            assert summary["download_method"] == "huggingface_hub"
            assert output_path.exists()
            assert (reports_dir / "download_report.json").exists()


def test_download_failure_records_error_report(tmp_path):
    output_path = tmp_path / "raw.jsonl"
    reports_dir = tmp_path / "reports"

    with patch.dict("sys.modules", {"datasets": None}):
        with patch("huggingface_hub.hf_hub_download", side_effect=RuntimeError("Network connection reset")):
            with pytest.raises(RuntimeError, match="Network connection reset"):
                download_dataset(
                    dataset_id="test/repo",
                    revision="main",
                    split="train",
                    output_path=output_path,
                    reports_dir=reports_dir,
                    force_redownload=True,
                )

            report_file = reports_dir / "download_report.json"
            assert report_file.exists()
            with open(report_file, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                assert data["status"] == "error"
                assert "Network connection reset" in data["error"]
