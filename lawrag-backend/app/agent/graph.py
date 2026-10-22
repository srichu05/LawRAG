"""
graph.py — LangGraph orchestration workflow for LawRAG
======================================================
Compiles the 8-node state graph with conditional edges, bounded retries,
grounded generation, citation validation, and honest abstention.
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, StateGraph

from app import config
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

logger = logging.getLogger(__name__)


def route_evidence(state: LawRAGState) -> str:
    """
    Conditional routing edge from assess_evidence.
    Permits at most MAX_RETRIEVAL_RETRIES query rewrites (default 1).
    """
    status = state.get("evidence_status", "")
    retries = state.get("retry_count", 0)

    if status == "sufficient":
        return "generate_answer"
    elif status == "weak" and retries < config.MAX_RETRIEVAL_RETRIES:
        return "rewrite_query"
    else:
        return "abstain"


def build_lawrag_graph(
    embedder=None,
    bm25_index=None,
    llm=None,
    rewriter=None,
):
    """
    Construct and compile the LawRAG LangGraph StateGraph.
    Allows injecting dependencies (embedder, bm25_index, llm, rewriter)
    for reproducible offline unit testing.
    """
    workflow = StateGraph(LawRAGState)

    # Wrap nodes with injected dependencies if supplied
    def _retrieve_node(state: LawRAGState) -> dict[str, Any]:
        return retrieve_evidence(state, embedder=embedder, bm25_index=bm25_index)

    def _rewrite_node(state: LawRAGState) -> dict[str, Any]:
        return rewrite_query(state, rewriter=rewriter)

    def _generate_node(state: LawRAGState) -> dict[str, Any]:
        return generate_answer(state, llm=llm)

    # Register nodes
    workflow.add_node("analyze_query", analyze_query)
    workflow.add_node("retrieve_evidence", _retrieve_node)
    workflow.add_node("assess_evidence", assess_evidence)
    workflow.add_node("rewrite_query", _rewrite_node)
    workflow.add_node("generate_answer", _generate_node)
    workflow.add_node("validate_citations", validate_citations)
    workflow.add_node("abstain", abstain)
    workflow.add_node("finalize", finalize)

    # Register edges
    workflow.set_entry_point("analyze_query")
    workflow.add_edge("analyze_query", "retrieve_evidence")
    workflow.add_edge("retrieve_evidence", "assess_evidence")

    # Conditional branching after evidence assessment
    workflow.add_conditional_edges(
        "assess_evidence",
        route_evidence,
        {
            "generate_answer": "generate_answer",
            "rewrite_query": "rewrite_query",
            "abstain": "abstain",
        },
    )

    # Loop back from rewrite to retrieval (strictly bounded by retry_count < 1)
    workflow.add_edge("rewrite_query", "retrieve_evidence")

    # Linear branches leading to finalization
    workflow.add_edge("generate_answer", "validate_citations")
    workflow.add_edge("validate_citations", "finalize")
    workflow.add_edge("abstain", "finalize")
    workflow.add_edge("finalize", END)

    return workflow.compile()


def run_lawrag(
    question: str,
    embedder=None,
    bm25_index=None,
    llm=None,
    rewriter=None,
) -> LawRAGState:
    """
    Main entry point to execute the complete Agentic RAG workflow.

    Parameters
    ----------
    question   : User's legal question
    embedder   : Optional custom or mock embedder
    bm25_index : Optional pre-loaded BM25 index
    llm        : Optional custom or mock LLM client
    rewriter   : Optional custom query rewriter

    Returns
    -------
    Final LawRAGState dictionary containing answer, citations, evidence_status, etc.
    """
    graph = build_lawrag_graph(
        embedder=embedder,
        bm25_index=bm25_index,
        llm=llm,
        rewriter=rewriter,
    )

    initial_state: LawRAGState = {
        "question": question,
        "retrieved_chunks": [],
        "evidence_status": "evaluating",
        "retry_count": 0,
        "answer": "",
        "citations": [],
        "warnings": [],
        "search_query": question,
        "rewritten_queries": [],
        "conflicts_detected": False,
        "metadata": {},
    }

    final_state = graph.invoke(initial_state)
    return final_state
