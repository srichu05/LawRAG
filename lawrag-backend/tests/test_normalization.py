"""
Tests for normalization module.
Tests run offline — no network or API calls.
"""
import json
import tempfile
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ingestion.normalize import normalize_records, load_normalized_records, _normalize_one


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_raw_jsonl(records: list[dict], tmp_path: Path) -> Path:
    """Write records to a temp JSONL file."""
    p = tmp_path / "raw.jsonl"
    with open(p, "w") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")
    return p


VALID_RECORD = {
    "id": 42,
    "text": "The court held that the right to equality is a fundamental right.",
    "metadata": {"chunk_index": 0, "source": "judgment_abc.pdf", "total_pages": 15},
}

BLANK_TEXT_RECORD = {
    "id": 99,
    "text": "   ",
    "metadata": {"chunk_index": 1, "source": "judgment_abc.pdf", "total_pages": 15},
}

NO_ID_RECORD = {
    "text": "Bail was denied based on the severity of the offence.",
    "metadata": {"chunk_index": 2, "source": "judgment_xyz.pdf", "total_pages": 10},
}

DUPLICATE_ID_RECORD = {
    "id": 42,
    "text": "A different text with the same id.",
    "metadata": {"chunk_index": 5, "source": "other.pdf", "total_pages": 5},
}


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class TestNormalizeOne:
    def test_valid_record(self):
        warnings = []
        result = _normalize_one(VALID_RECORD, 1, warnings)
        assert result["chunk_id"] == "42"
        assert result["source_id"] == "42"
        assert result["text"] == VALID_RECORD["text"]
        assert result["source_file"] == "judgment_abc.pdf"
        assert result["chunk_index"] == 0
        assert result["total_pages"] == 15
        assert "metadata" in result
        assert not warnings

    def test_missing_id_generates_hash(self):
        warnings = []
        result = _normalize_one(NO_ID_RECORD, 1, warnings)
        assert result["chunk_id"] is not None
        assert len(result["chunk_id"]) == 16  # sha256 hex prefix
        assert result["source_id"] is None
        assert any("generated chunk_id" in w for w in warnings)

    def test_blank_text_preserved(self):
        """Blank text should pass through normalize_one; skip happens at batch level."""
        warnings = []
        record = {"id": 1, "text": "  ", "metadata": {}}
        result = _normalize_one(record, 1, warnings)
        assert result["text"] == "  "  # text is NOT stripped

    def test_missing_metadata_fields_are_none(self):
        warnings = []
        record = {"id": 5, "text": "Some text.", "metadata": {}}
        result = _normalize_one(record, 1, warnings)
        assert result["chunk_index"] is None
        assert result["source_file"] is None
        assert result["total_pages"] is None

    def test_full_metadata_preserved(self):
        warnings = []
        result = _normalize_one(VALID_RECORD, 1, warnings)
        assert result["metadata"] == VALID_RECORD["metadata"]

    def test_non_dict_metadata_handled(self):
        warnings = []
        record = {"id": 10, "text": "Some text.", "metadata": "not_a_dict"}
        result = _normalize_one(record, 1, warnings)
        assert result["metadata"] == {}
        assert any("not a dict" in w for w in warnings)


class TestNormalizeRecords:
    def test_valid_records_normalized(self, tmp_path):
        raw = make_raw_jsonl([VALID_RECORD, NO_ID_RECORD], tmp_path)
        out = tmp_path / "norm.jsonl"
        reports = tmp_path / "reports"
        report = normalize_records(raw, out, reports)

        assert report["normalized_records"] == 2
        assert report["skipped_blank_text"] == 0
        assert out.exists()

        records = list(load_normalized_records(out))
        assert len(records) == 2

    def test_blank_text_records_skipped(self, tmp_path):
        raw = make_raw_jsonl([VALID_RECORD, BLANK_TEXT_RECORD], tmp_path)
        out = tmp_path / "norm.jsonl"
        reports = tmp_path / "reports"
        report = normalize_records(raw, out, reports)

        assert report["normalized_records"] == 1
        assert report["skipped_blank_text"] == 1

    def test_duplicate_ids_skipped(self, tmp_path):
        raw = make_raw_jsonl([VALID_RECORD, DUPLICATE_ID_RECORD], tmp_path)
        out = tmp_path / "norm.jsonl"
        reports = tmp_path / "reports"
        report = normalize_records(raw, out, reports)

        assert report["normalized_records"] == 1
        assert report["skipped_duplicate_id"] == 1

    def test_idempotent_when_rerun(self, tmp_path):
        """Running normalization twice on the same input should produce the same output."""
        raw = make_raw_jsonl([VALID_RECORD], tmp_path)
        out = tmp_path / "norm.jsonl"
        reports = tmp_path / "reports"

        report1 = normalize_records(raw, out, reports)
        out.unlink()
        report2 = normalize_records(raw, out, reports)

        assert report1["normalized_records"] == report2["normalized_records"]

    def test_json_parse_error_lines_skipped(self, tmp_path):
        p = tmp_path / "raw.jsonl"
        with open(p, "w") as fh:
            fh.write(json.dumps(VALID_RECORD) + "\n")
            fh.write("{this is not valid json}\n")
        out = tmp_path / "norm.jsonl"
        reports = tmp_path / "reports"
        report = normalize_records(raw_jsonl_path=p, output_path=out, reports_dir=reports)

        assert report["normalized_records"] == 1  # only valid record

    def test_report_saved_to_disk(self, tmp_path):
        raw = make_raw_jsonl([VALID_RECORD], tmp_path)
        out = tmp_path / "norm.jsonl"
        reports = tmp_path / "reports"
        normalize_records(raw, out, reports)
        assert (reports / "normalization_report.json").exists()

    def test_original_text_not_modified(self, tmp_path):
        """Normalization must not alter the original legal text."""
        text = "  Section 302 IPC — Punishment for murder.  "
        record = {"id": 7, "text": text, "metadata": {"source": "test.pdf", "chunk_index": 0, "total_pages": 1}}
        raw = make_raw_jsonl([record], tmp_path)
        out = tmp_path / "norm.jsonl"
        reports = tmp_path / "reports"
        normalize_records(raw, out, reports)

        records = list(load_normalized_records(out))
        assert records[0]["text"] == text  # EXACT original, including leading/trailing spaces


class TestLoadNormalizedRecords:
    def test_streams_records_lazily(self, tmp_path):
        raw = make_raw_jsonl([VALID_RECORD, NO_ID_RECORD], tmp_path)
        out = tmp_path / "norm.jsonl"
        reports = tmp_path / "reports"
        normalize_records(raw, out, reports)

        records = list(load_normalized_records(out))
        assert len(records) == 2
        for r in records:
            assert "chunk_id" in r
            assert "text" in r

    def test_file_not_found_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            list(load_normalized_records(tmp_path / "missing.jsonl"))
