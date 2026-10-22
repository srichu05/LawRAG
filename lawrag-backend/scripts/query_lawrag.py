#!/usr/bin/env python3
"""
query_lawrag.py — Phase 2 Agentic Legal Research CLI
=====================================================
Executes the full LangGraph Agentic RAG workflow:
  1. Analyzes question
  2. Retrieves evidence from BM25 and ChromaDB via RRF
  3. Assesses evidence sufficiency & conflicts
  4. Rewrites query if initial evidence is weak (max 1 retry)
  5. Generates grounded answer from retrieved Supreme Court judgments
  6. Validates citations against actual records (or honestly abstains)

Usage:
    python scripts/query_lawrag.py "What are the principles of natural justice?"
    python scripts/query_lawrag.py "What does the Supreme Court say about bail under section 302 IPC?"
    python scripts/query_lawrag.py "What are the current tax rates for cryptocurrency in India?" # abstention demo
    python scripts/query_lawrag.py -i # interactive mode
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Configure safe utf-8 console output for Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config
from app.agent.graph import run_lawrag

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")


def print_result(state: dict, as_json: bool = False) -> None:
    """Print the workflow output in human-readable or JSON format."""
    if as_json:
        print(json.dumps(state, indent=2, default=str))
        return

    print(f"\n{'='*70}")
    print(f"  LawRAG — Legal Research Report")
    print(f"{'='*70}")
    print(f"  Question          : {state.get('question')}")
    print(f"  Evidence Status   : {state.get('evidence_status', '').upper()}")
    
    meta = state.get("metadata", {})
    attempts = meta.get("retrieval_attempts", state.get("retry_count", 0) + 1)
    print(f"  Retrieval Attempts: {attempts}")

    rewrites = state.get("rewritten_queries", [])
    if rewrites:
        print(f"  Query Rewrites    : {', '.join(repr(r) for r in rewrites)}")

    warnings = state.get("warnings", [])
    if warnings:
        print("\n  Warnings / Disclosures:")
        for w in warnings:
            print(f"    - {w}")

    print(f"\n{'-'*70}")
    print("  ANSWER:")
    print(f"{'-'*70}")
    print(state.get("answer", "No answer generated."))

    citations = state.get("citations", [])
    print(f"\n{'-'*70}")
    print(f"  CITATIONS & SUPPORTING EVIDENCE ({len(citations)}):")
    print(f"{'-'*70}")
    if not citations:
        print("  No citations (no sufficient evidence verified in corpus).")
    else:
        for idx, cit in enumerate(citations, start=1):
            print(f"\n  [{idx}] Chunk ID: {cit.get('chunk_id')}")
            print(f"      Source File : {cit.get('source_file') or 'Unknown (missing metadata)'}")
            print(f"      Chunk Index : {cit.get('chunk_index')} | Total Pages: {cit.get('total_pages')}")
            print(f"      Excerpt     : \"{cit.get('excerpt')}\"")

    disclaimer = meta.get("disclaimer")
    if disclaimer:
        print(f"\n{'='*70}")
        print(f"  Notice: {disclaimer}")
    print(f"{'='*70}\n")


def interactive_mode():
    """Interactive loop for querying the legal research agent."""
    print("\nLawRAG Interactive Research Console (type 'exit' or 'quit' to quit)")
    print("-" * 65)
    while True:
        try:
            q = input("\nEnter your legal question: ").strip()
            if not q:
                continue
            if q.lower() in ("exit", "quit", "q"):
                print("Exiting LawRAG console.")
                break
            result = run_lawrag(q)
            print_result(result)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting LawRAG console.")
            break


def main():
    parser = argparse.ArgumentParser(description="LawRAG Phase 2 Agentic Legal Research CLI")
    parser.add_argument("question", nargs="?", help="Legal question to research")
    parser.add_argument("--provider", help="Override LLM_PROVIDER (e.g. 'mock', 'openai', 'groq')")
    parser.add_argument("--json", action="store_true", help="Output result as JSON")
    parser.add_argument("-i", "--interactive", action="store_true", help="Start interactive session")
    args = parser.parse_args()

    if args.provider:
        os.environ["LLM_PROVIDER"] = args.provider

    if args.interactive:
        interactive_mode()
    elif args.question:
        result = run_lawrag(args.question)
        print_result(result, as_json=args.json)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
