"""
Tests for validation module.
Tests run offline — no network or API calls.
"""
import json
from pathlib import Path

import pytest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ingestion.validate import validate_records


def make_raw_jsonl(records: list, tmp_path: Path) -> Path:
    p = tmp_path / "raw.jsonl"
    with open(p, "w") as fh:
        for r in records:
            if isinstance(r, str):
                fh.write(r + "\n")
            else:
                fh.write(json.dumps(r) + "\n")
    return p


GOOD = {
    "id": 1,
    "text": "The Supreme Court held that fundamental rights are non-derogable.",
    "metadata": {"chunk_index": 0, "source": "case_001.pdf", "total_pages": 10},
}

BLANK_TEXT = {
    "id": 2,
    "text": "",
    "metadata": {"chunk_index": 1, "source": "case_001.pdf", "total_pages": 10},
}

MISSING_ID = {
    "text": "Bail was denied given the gravity of the offence.",
    "metadata": {"chunk_index": 0, "source": "case_002.pdf", "total_pages": 5},
}

DUPLICATE_ID_2 = {
    "id": 1,
    "text": "Another passage with the same id=1.",
    "metadata": {"chunk_index": 99, "source": "other.pdf", "total_pages": 3},
}

DUPLICATE_TEXT_RECORD = {
    "id": 3,
    "text": GOOD["text"],  # Same text as GOOD
    "metadata": {"chunk_index": 2, "source": "case_003.pdf", "total_pages": 7},
}

NO_SOURCE = {
    "id": 4,
    "text": "Some legal text without a source.",
    "metadata": {"chunk_index": 0, "total_pages": 5},  # missing source
}


class TestValidateRecords:
    def test_valid_record_counted(self, tmp_path):
        raw = make_raw_jsonl([GOOD], tmp_path)
        report = validate_records(raw, tmp_path / "reports")
        assert report["valid_records"] == 1
        assert report["total_lines"] == 1

    def test_blank_text_flagged(self, tmp_path):
        raw = make_raw_jsonl([GOOD, BLANK_TEXT], tmp_path)
        report = validate_records(raw, tmp_path / "reports")
        assert report["skipped_blank_text"] >= 1

    def test_json_error_counted(self, tmp_path):
        raw = make_raw_jsonl([GOOD, "{bad json"], tmp_path)
        report = validate_records(raw, tmp_path / "reports")
        assert report["skipped_json_error"] == 1

    def test_duplicate_id_detected(self, tmp_path):
        raw = make_raw_jsonl([GOOD, DUPLICATE_ID_2], tmp_path)
        report = validate_records(raw, tmp_path / "reports")
        assert report["duplicate_id_count"] == 1

    def test_duplicate_text_detected(self, tmp_path):
        raw = make_raw_jsonl([GOOD, DUPLICATE_TEXT_RECORD], tmp_path)
        report = validate_records(raw, tmp_path / "reports")
        assert report["duplicate_text_count"] == 1

    def test_missing_source_counted(self, tmp_path):
        """Records without source metadata should reduce meta_has_source count."""
        raw = make_raw_jsonl([GOOD, NO_SOURCE], tmp_path)
        report = validate_records(raw, tmp_path / "reports")
        cov = report["metadata_coverage"]
        assert cov["source_present"] == 1  # only GOOD has source

    def test_missing_id_noted(self, tmp_path):
        raw = make_raw_jsonl([MISSING_ID], tmp_path)
        report = validate_records(raw, tmp_path / "reports")
        assert report["skipped_missing_id"] >= 1

    def test_report_saved(self, tmp_path):
        raw = make_raw_jsonl([GOOD], tmp_path)
        reports = tmp_path / "reports"
        validate_records(raw, reports)
        assert (reports / "validation_report.json").exists()

    def test_file_not_found_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            validate_records(tmp_path / "missing.jsonl", tmp_path)

    def test_metadata_coverage_statistics(self, tmp_path):
        raw = make_raw_jsonl([GOOD], tmp_path)
        report = validate_records(raw, tmp_path / "reports")
        cov = report["metadata_coverage"]
        assert cov["chunk_index_present"] == 1
        assert cov["total_pages_present"] == 1
        assert cov["unique_sources"] == 1

    def test_empty_file(self, tmp_path):
        p = tmp_path / "empty.jsonl"
        p.write_text("")
        report = validate_records(p, tmp_path / "reports")
        assert report["valid_records"] == 0
        assert report["total_lines"] == 0
