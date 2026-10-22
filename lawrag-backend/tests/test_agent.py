"""
test_agent.py — Phase 2 LangGraph Agentic RAG Test Suite
=========================================================
Tests cover:
  1. Supported question -> grounded answer and valid citations
  2. Unsupported question -> bounded retry -> explicit honest abstention
  3. Weak initial retrieval -> exactly one retry at most (bounded loops)
  4. Citation validation -> citations point strictly to real retrieved chunks
  5. Missing or invalid source metadata -> disclosure warning
  6. Conflicting evidence detection -> conflict flag & warning
  7. LLM provider failure -> graceful fallback without crash
  8. Empty retrieval results -> immediate abstention
"""

from unittest.mock import MagicMock, patch

import pytest

from app.agent.graph import build_lawrag_graph, route_evidence, run_lawrag
from app.agent.llm import BaseLLMClient, MockLLM, OpenAICompatibleLLM, get_llm_client
from app.agent.nodes import (
    abstain,
    analyze_query,
    assess_evidence,
    finalize,
    generate_answer,
    retrieve_evidence,
    rewrite_query,
    validate_citations,
)
from app.agent.state import LawRAGState

# Sample records for mock retrieval
SAMPLE_CHUNKS = [
    {
        "chunk_id": "3490",
        "text": "right in Part III at all. As to the meaning of the word 'law' it was argued that it meant principles of natural justice. It meant 'jus', i.e., law in the abstract sense of natural justice.",
        "source_file": "6482417cc33c75ac1d880121.pdf",
        "source_id": "3490",
        "chunk_index": 116,
        "total_pages": 153,
        "rrf_score": 0.032,
        "rank": 1,
    },
    {
        "chunk_id": "4465",
        "text": "rules of procedure which are sanctioned or well established by principles of natural justice accepted in all climes and countries and at all times.",
        "source_file": "6482417cc33c75ac1d880121.pdf",
        "source_id": "4465",
        "chunk_index": 1091,
        "total_pages": 153,
        "rrf_score": 0.028,
        "rank": 2,
    },
]

CONFLICTING_CHUNKS = [
    {
        "chunk_id": "101",
        "text": "The majority held that the detention was lawful under the statute.",
        "source_file": "case_maj.pdf",
        "source_id": "101",
        "chunk_index": 1,
        "total_pages": 10,
        "rrf_score": 0.03,
        "rank": 1,
    },
    {
        "chunk_id": "102",
        "text": "In a dissenting opinion, it was held that the procedure was unconstitutional and contrary to natural justice, and the previous ruling was overruled.",
        "source_file": "case_diss.pdf",
        "source_id": "102",
        "chunk_index": 2,
        "total_pages": 10,
        "rrf_score": 0.025,
        "rank": 2,
    },
]


# =============================================================================
# 1. Individual Node Unit Tests
# =============================================================================

class TestAnalyzeQueryNode:
    def test_cleans_whitespace(self):
        state: LawRAGState = {"question": "   What is   natural   justice?   "}
        output = analyze_query(state)
        assert output["question"] == "What is natural justice?"
        assert output["search_query"] == "What is natural justice?"
        assert output["retry_count"] == 0

    def test_empty_query_flagged(self):
        state: LawRAGState = {"question": "   "}
        output = analyze_query(state)
        assert output["question"] == ""
        assert any("Empty query" in w for w in output["warnings"])


class TestAssessEvidenceNode:
    def test_empty_chunks_is_insufficient(self):
        state: LawRAGState = {
            "question": "What is natural justice?",
            "retrieved_chunks": [],
            "retry_count": 0,
            "warnings": [],
        }
        res = assess_evidence(state)
        assert res["evidence_status"] == "insufficient"
        assert any("No chunks were retrieved" in w for w in res["warnings"])

    def test_supported_query_is_sufficient(self):
        state: LawRAGState = {
            "question": "What are the principles of natural justice?",
            "retrieved_chunks": SAMPLE_CHUNKS,
            "retry_count": 0,
            "warnings": [],
        }
        res = assess_evidence(state)
        assert res["evidence_status"] == "sufficient"

    def test_unsupported_query_with_retry_available_is_weak(self):
        state: LawRAGState = {
            "question": "What are the current tax rates for cryptocurrency in India?",
            "retrieved_chunks": SAMPLE_CHUNKS,  # natural justice chunks, not crypto
            "retry_count": 0,
            "warnings": [],
        }
        res = assess_evidence(state)
        assert res["evidence_status"] == "weak"
        assert any("cryptocurrency" in w for w in res["warnings"])

    def test_unsupported_query_after_retry_is_insufficient(self):
        state: LawRAGState = {
            "question": "What are the current tax rates for cryptocurrency in India?",
            "retrieved_chunks": SAMPLE_CHUNKS,
            "retry_count": 1,  # retry already used
            "warnings": [],
        }
        res = assess_evidence(state)
        assert res["evidence_status"] == "insufficient"

    def test_detects_conflicting_evidence(self):
        state: LawRAGState = {
            "question": "Is preventive detention lawful?",
            "retrieved_chunks": CONFLICTING_CHUNKS,
            "retry_count": 0,
            "warnings": [],
        }
        res = assess_evidence(state)
        assert res["conflicts_detected"] is True
        assert any("conflicting" in w.lower() or "dissent" in w.lower() for w in res["warnings"])

    def test_discloses_missing_source_metadata(self):
        chunk_no_meta = [dict(SAMPLE_CHUNKS[0], source_file=None)]
        state: LawRAGState = {
            "question": "What is natural justice?",
            "retrieved_chunks": chunk_no_meta,
            "retry_count": 0,
            "warnings": [],
        }
        res = assess_evidence(state)
        assert any("missing or incomplete" in w for w in res["warnings"])


class TestRewriteQueryNode:
    def test_increments_retry_count_and_updates_search_query(self):
        state: LawRAGState = {
            "question": "breach of contract damages",
            "retry_count": 0,
            "rewritten_queries": [],
            "warnings": [],
        }
        mock_rewriter = MagicMock()
        mock_rewriter.rewrite.return_value = ["breach of contract damages", "contract violation compensation"]

        output = rewrite_query(state, rewriter=mock_rewriter)
        assert output["retry_count"] == 1
        assert output["search_query"] == "contract violation compensation"
        assert "contract violation compensation" in output["rewritten_queries"]
        assert any("retried with query" in w for w in output["warnings"])


class TestValidateCitationsNode:
    def test_citations_match_retrieved_chunks(self):
        state: LawRAGState = {
            "retrieved_chunks": SAMPLE_CHUNKS,
            "warnings": [],
        }
        output = validate_citations(state)
        citations = output["citations"]
        assert len(citations) == 2
        assert citations[0]["chunk_id"] == "3490"
        assert citations[0]["source_file"] == "6482417cc33c75ac1d880121.pdf"
        assert citations[0]["chunk_index"] == 116
        assert citations[0]["total_pages"] == 153
        assert len(citations[0]["excerpt"]) > 0

    def test_flags_missing_source_file_in_citations(self):
        chunk_missing_src = [dict(SAMPLE_CHUNKS[0], chunk_id="999", source_file=None)]
        state: LawRAGState = {
            "retrieved_chunks": chunk_missing_src,
            "warnings": [],
        }
        output = validate_citations(state)
        assert output["citations"][0]["chunk_id"] == "999"
        assert output["citations"][0]["source_file"] is None
        assert any("[Chunk 999] has no source_file metadata" in w for w in output["warnings"])


class TestAbstainNode:
    def test_abstention_output_structure(self):
        state: LawRAGState = {
            "question": "What is the penalty for cricket match fixing in IPL?",
            "warnings": [],
        }
        output = abstain(state)
        assert "insufficient evidence" in output["answer"].lower()
        assert output["citations"] == []
        assert output["evidence_status"] == "insufficient"
        assert any("abstained" in w.lower() for w in output["warnings"])


class TestGenerateAnswerNode:
    def test_grounded_answer_generation_with_mock_llm(self):
        state: LawRAGState = {
            "question": "What are the principles of natural justice?",
            "retrieved_chunks": SAMPLE_CHUNKS,
            "warnings": [],
        }
        mock_llm = MockLLM()
        output = generate_answer(state, llm=mock_llm)
        assert len(output["answer"]) > 20
        assert "natural justice" in output["answer"].lower()

    def test_llm_failure_does_not_crash_workflow(self):
        state: LawRAGState = {
            "question": "What are the principles of natural justice?",
            "retrieved_chunks": SAMPLE_CHUNKS,
            "warnings": [],
        }
        failing_llm = MagicMock()
        failing_llm.generate.side_effect = ConnectionError("Remote LLM endpoint timed out")

        output = generate_answer(state, llm=failing_llm)
        assert "An error occurred" in output["answer"]
        assert any("LLM generation failed" in w for w in output["warnings"])


# =============================================================================
# 2. Workflow Routing & State Transition Tests
# =============================================================================

class TestWorkflowRouting:
    def test_route_sufficient_to_generate(self):
        state: LawRAGState = {"evidence_status": "sufficient", "retry_count": 0}
        assert route_evidence(state) == "generate_answer"

    def test_route_weak_with_retry_available_to_rewrite(self):
        state: LawRAGState = {"evidence_status": "weak", "retry_count": 0}
        assert route_evidence(state) == "rewrite_query"

    def test_route_weak_with_retry_exhausted_to_abstain(self):
        state: LawRAGState = {"evidence_status": "weak", "retry_count": 1}
        assert route_evidence(state) == "abstain"

    def test_route_insufficient_to_abstain(self):
        state: LawRAGState = {"evidence_status": "insufficient", "retry_count": 0}
        assert route_evidence(state) == "abstain"


# =============================================================================
# 3. End-to-End Workflow Integration Tests
# =============================================================================

class TestLawRAGWorkflowEndToEnd:
    def test_supported_question_grounded_answer_and_valid_citations(self):
        """Supported question receives sufficient evidence status, grounded answer, and citations."""
        mock_embedder = MagicMock()
        mock_bm25 = MagicMock()
        mock_bm25.retrieve.return_value = SAMPLE_CHUNKS
        mock_llm = MockLLM()

        with patch("app.agent.nodes.retrieve_hybrid", return_value=SAMPLE_CHUNKS):
            result = run_lawrag(
                question="What are the principles of natural justice?",
                embedder=mock_embedder,
                bm25_index=mock_bm25,
                llm=mock_llm,
            )

        assert result["evidence_status"] == "sufficient"
        assert len(result["answer"]) > 0
        assert "insufficient evidence" not in result["answer"].lower()
        assert len(result["citations"]) == len(SAMPLE_CHUNKS)
        # Citations must match chunk IDs from retrieval
        citation_ids = [c["chunk_id"] for c in result["citations"]]
        assert "3490" in citation_ids
        assert "4465" in citation_ids
        assert result["metadata"]["retrieval_attempts"] == 1

    def test_unsupported_question_triggers_retry_then_abstention(self):
        """Unsupported question (e.g. cryptocurrency) must retry once then honestly abstain."""
        mock_embedder = MagicMock()
        mock_bm25 = MagicMock()
        # Returns chunks that do not mention cryptocurrency
        mock_bm25.retrieve.return_value = SAMPLE_CHUNKS
        mock_llm = MockLLM()
        mock_rewriter = MagicMock()
        mock_rewriter.rewrite.return_value = [
            "What are tax rates for cryptocurrency in India?",
            "cryptocurrency digital assets taxation regulations",
        ]

        with patch("app.agent.nodes.retrieve_hybrid", return_value=SAMPLE_CHUNKS):
            result = run_lawrag(
                question="What are tax rates for cryptocurrency in India?",
                embedder=mock_embedder,
                bm25_index=mock_bm25,
                llm=mock_llm,
                rewriter=mock_rewriter,
            )

        # Must abstain after exhausting 1 retry
        assert result["evidence_status"] == "insufficient"
        assert "insufficient evidence" in result["answer"].lower()
        assert result["citations"] == []
        assert result["retry_count"] == 1
        assert result["metadata"]["retrieval_attempts"] == 2
        assert any("abstained" in w.lower() for w in result["warnings"])

    def test_empty_retrieval_results_immediately_abstains(self):
        """When nothing is retrieved, workflow abstains honestly without generating hallucinations."""
        mock_embedder = MagicMock()
        mock_bm25 = MagicMock()
        mock_bm25.retrieve.return_value = []

        with patch("app.agent.nodes.retrieve_hybrid", return_value=[]):
            result = run_lawrag(
                question="Completely unknown query",
                embedder=mock_embedder,
                bm25_index=mock_bm25,
                llm=MockLLM(),
            )

        assert result["evidence_status"] == "insufficient"
        assert "insufficient evidence" in result["answer"].lower()
        assert result["citations"] == []
        assert result["retrieved_chunks"] == []

    def test_bounded_retries_prevent_infinite_loops(self):
        """Verify that workflow never retries more than once even if evidence remains weak."""
        weak_chunk = [{
            "chunk_id": "1",
            "text": "general text without specific subject",
            "source_file": "doc.pdf",
            "source_id": "1",
            "chunk_index": 0,
            "total_pages": 1,
            "rrf_score": 0.005,  # below minimum score
            "rank": 1,
        }]

        mock_rewriter = MagicMock()
        mock_rewriter.rewrite.return_value = ["original query", "alternative query 1"]

        with patch("app.agent.nodes.retrieve_hybrid", return_value=weak_chunk):
            result = run_lawrag(
                question="Specific obscure legal provision XYZ",
                embedder=MagicMock(),
                bm25_index=MagicMock(),
                llm=MockLLM(),
                rewriter=mock_rewriter,
            )

        # Retry count must be exactly 1, not 2 or 3
        assert result["retry_count"] == 1
        assert result["evidence_status"] == "insufficient"
        assert "insufficient evidence" in result["answer"].lower()
