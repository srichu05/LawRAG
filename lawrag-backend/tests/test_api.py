"""
test_api.py — Unit tests for LawRAG FastAPI endpoints
======================================================
Tests /api/v1/health, /api/v1/research, request validation,
grounded generation responses, citations, and insufficient evidence handling.
"""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check_endpoints(client):
    """Verify both /health and /api/v1/health return 200 with operational metadata."""
    for path in ["/health", "/api/v1/health"]:
        resp = client.get(path)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "llm_provider" in data
        assert "embedding_provider" in data
        assert "bm25_index_ready" in data


def test_root_endpoint(client):
    """Verify root endpoint returns API information."""
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert "service" in data
    assert "endpoints" in data


def test_research_empty_query_rejected(client):
    """Verify empty or missing query returns HTTP 400."""
    resp = client.post("/api/v1/research", json={"query": "   "})
    assert resp.status_code == 400
    assert "Research query cannot be empty" in resp.json()["detail"]

    resp2 = client.post("/api/v1/research", json={})
    assert resp2.status_code == 400


def test_research_supported_query_grounded_response(client):
    """Verify supported legal question produces grounded answer and formatted citations."""
    mock_state = {
        "question": "What constitutes retrenchment?",
        "evidence_status": "sufficient",
        "retry_count": 0,
        "answer": "Retrenchment under Section 25F requires one month notice and compensation [Chunk c1].",
        "retrieved_chunks": [
            {
                "chunk_id": "c1",
                "source_file": "1976_1_SCC_822.json",
                "source_id": "1976_SCC_822",
                "chunk_index": 0,
                "total_pages": 4,
                "text": "Under the Industrial Disputes Act, 1947 Section 25F mandatory retrenchment notice...",
            }
        ],
        "citations": [
            {
                "chunk_id": "c1",
                "source_file": "1976_1_SCC_822.json",
                "source_id": "1976_SCC_822",
                "chunk_index": 0,
                "total_pages": 4,
                "excerpt": "Under the Industrial Disputes Act, 1947 Section 25F mandatory retrenchment notice...",
            }
        ],
        "warnings": [],
        "conflicts_detected": False,
        "metadata": {"evidence_status": "sufficient"},
    }

    with patch("app.main.run_lawrag", return_value=mock_state):
        resp = client.post(
            "/api/v1/research",
            json={"query": "What constitutes retrenchment?", "category": "Employment and Labour Law"},
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["isInsufficientEvidence"] is False
        assert "Industrial Disputes Act" in str(data["statutes"]) or len(data["statutes"]) >= 0
        assert len(data["citations"]) == 1
        assert data["citations"][0]["id"] == "cite-c1"
        assert "Supreme Court of India" in data["citations"][0]["caseName"]
        assert "agentTraces" in data
        assert "planner" in data["agentTraces"]
        assert "retriever" in data["agentTraces"]
        assert "verifier" in data["agentTraces"]
        assert "synthesizer" in data["agentTraces"]
        assert "FastAPI" in data["backendSource"] or "LawRAG" in data["backendSource"]


def test_research_unsupported_query_abstains(client):
    """Verify unsupported query returns explicit insufficient evidence response."""
    mock_state = {
        "question": "Martian cryptocurrency penal code",
        "evidence_status": "insufficient",
        "retry_count": 1,
        "answer": "There is insufficient evidence in the retrieved Indian Supreme Court judgments...",
        "retrieved_chunks": [],
        "citations": [],
        "warnings": ["Workflow abstained due to insufficient evidence in the corpus."],
        "conflicts_detected": False,
        "metadata": {"evidence_status": "insufficient"},
    }

    with patch("app.main.run_lawrag", return_value=mock_state):
        resp = client.post(
            "/api/v1/research",
            json={"query": "Martian cryptocurrency penal code"},
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["isInsufficientEvidence"] is True
        assert len(data["citations"]) == 0
        assert len(data["reasons"]) > 0
        assert len(data["recommendations"]) > 0
        assert "insufficient" in data["summary"].lower()
