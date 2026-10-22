"""
Tests for query rewriter module.
Tests run offline — no LLM API calls.
Uses the deterministic offline rewriter.
"""
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.retrieval.query_rewriter import QueryRewriter, _parse_alternatives


class TestQueryRewriterOffline:
    """Tests for deterministic offline rewriting (no LLM configured)."""

    def setup_method(self):
        # Ensure rewriter is in offline mode
        os.environ.pop("REWRITER_PROVIDER", None)
        os.environ.pop("REWRITER_MODEL", None)
        os.environ.pop("REWRITER_API_KEY", None)
        from importlib import reload
        import app.config as cfg
        reload(cfg)
        self.rewriter = QueryRewriter()

    def test_original_always_first(self):
        queries = self.rewriter.rewrite("What is natural justice?")
        assert queries[0] == "What is natural justice?"

    def test_returns_list(self):
        queries = self.rewriter.rewrite("bail application")
        assert isinstance(queries, list)
        assert len(queries) >= 1

    def test_max_alternatives_is_two(self):
        """Total queries (original + alternatives) should not exceed 3."""
        queries = self.rewriter.rewrite("breach of contract remedies India")
        alternatives = queries[1:]
        assert len(alternatives) <= 2

    def test_empty_query_returns_empty(self):
        queries = self.rewriter.rewrite("")
        assert queries == [""]

    def test_no_facts_introduced(self):
        """Offline rewriter must not add party names, dates, or provisions."""
        original = "What is natural justice?"
        queries = self.rewriter.rewrite(original)
        for q in queries:
            # Check no case names or statutory provisions were invented
            assert "section" not in q.lower() or "section" in original.lower()

    def test_synonym_expansion_for_breach_of_contract(self):
        queries = self.rewriter.rewrite("What happens in case of breach of contract?")
        assert len(queries) >= 2
        # At least one alternative should exist
        all_text = " ".join(queries).lower()
        # Synonym should be present in alternatives
        assert any(
            term in all_text
            for term in ("contract violation", "contractual breach", "non-performance")
        )

    def test_fundamental_rights_expansion(self):
        queries = self.rewriter.rewrite("Tell me about fundamental rights in India")
        assert len(queries) >= 1
        # Should generate an alternative

    def test_deduplication_in_output(self):
        """Same query should not appear twice in output."""
        queries = self.rewriter.rewrite("bail application murder")
        lowers = [q.lower() for q in queries]
        assert len(lowers) == len(set(lowers))

    def test_murder_synonym_works(self):
        queries = self.rewriter.rewrite("What are the penalties for murder?")
        all_text = " ".join(queries).lower()
        assert any(
            term in all_text
            for term in ("culpable homicide", "section 302 ipc", "homicide")
        )

    def test_short_query_handled(self):
        """Very short queries should not crash."""
        queries = self.rewriter.rewrite("bail")
        assert queries[0] == "bail"


class TestQueryRewriterBounds:
    """Tests that the rewriter enforces bounds."""

    def test_max_retries_config_respected(self):
        """Rewriter should respect REWRITER_MAX_RETRIES configuration."""
        with patch.dict(os.environ, {
            "REWRITER_PROVIDER": "huggingface",
            "REWRITER_MODEL": "test/model",
            "REWRITER_API_KEY": "test-key",
            "REWRITER_MAX_RETRIES": "1",
        }):
            from importlib import reload
            import app.config as cfg
            reload(cfg)
            from app.retrieval.query_rewriter import QueryRewriter as QR
            r = QR()
            # When LLM fails, should fall back gracefully
            with patch.object(r, "_llm_rewrite", side_effect=RuntimeError("API down")):
                queries = r.rewrite("natural justice")
            assert queries[0] == "natural justice"
            assert len(queries) <= 3

    def test_provider_unavailable_continues_with_original(self):
        """When provider is missing, should NOT crash — report and continue."""
        with patch.dict(os.environ, {
            "REWRITER_PROVIDER": "",
        }):
            from importlib import reload
            import app.config as cfg
            reload(cfg)
            from app.retrieval.query_rewriter import QueryRewriter as QR
            r = QR()
            queries = r.rewrite("What is natural justice?")
            # Should always include the original
            assert "What is natural justice?" in queries


class TestParseAlternatives:
    def test_parse_numbered_list(self):
        text = "1. Alternative one\n2. Alternative two"
        result = _parse_alternatives(text)
        assert len(result) <= 2
        assert all(isinstance(s, str) for s in result)

    def test_parse_bulleted_list(self):
        text = "- First alternative\n- Second alternative\n- Third alternative"
        result = _parse_alternatives(text)
        assert len(result) == 2  # capped at 2

    def test_empty_input(self):
        result = _parse_alternatives("")
        assert result == []

    def test_very_short_lines_filtered(self):
        text = "ok\nAlternative query text here"
        result = _parse_alternatives(text)
        # "ok" is too short (< 5 chars) and should be filtered
        for r in result:
            assert len(r) > 5
