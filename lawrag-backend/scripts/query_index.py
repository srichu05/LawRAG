#!/usr/bin/env python3
"""
query_index.py — CLI for dense, BM25, and hybrid retrieval
============================================================
Query the LawRAG indexes interactively or with a single question.

Usage:
    python scripts/query_index.py "What are the principles of natural justice?"
    python scripts/query_index.py --method bm25 "section 302 IPC"
    python scripts/query_index.py --method hybrid --top-k 10 "bail application murder"
    python scripts/query_index.py --method compare "fundamental rights article 21"
    python scripts/query_index.py --rewrite "breach of contract remedies"
    python scripts/query_index.py --interactive
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s — %(message)s",
)


def main():
    parser = argparse.ArgumentParser(
        description="Query the LawRAG retrieval indexes"
    )
    parser.add_argument("query", nargs="?", help="Query string")
    parser.add_argument(
        "--method",
        choices=["dense", "bm25", "hybrid", "compare"],
        default="hybrid",
        help="Retrieval method (default: hybrid)",
    )
    parser.add_argument("--top-k", type=int, default=5, help="Number of results")
    parser.add_argument(
        "--provider",
        help="Override EMBEDDING_PROVIDER (e.g., 'mock')",
    )
    parser.add_argument(
        "--rewrite",
        action="store_true",
        help="Enable query rewriting",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Interactive query loop",
    )
    args = parser.parse_args()

    if args.provider:
        os.environ["EMBEDDING_PROVIDER"] = args.provider

    from app import config
    from app.retrieval.embeddings import get_embedder

    # Load embedder
    try:
        embedder = get_embedder()
    except Exception as exc:
        print(f"[ERROR] Embedder error: {exc}")
        sys.exit(1)

    # Load BM25 index (needed for hybrid and bm25 methods)
    bm25_index = None
    if args.method in ("bm25", "hybrid", "compare"):
        try:
            from app.retrieval.bm25 import load_bm25_index
            bm25_index = load_bm25_index()
        except FileNotFoundError:
            if args.method == "bm25":
                print(f"[ERROR] BM25 index not found. Run: python scripts/build_index.py")
                sys.exit(1)
            else:
                print("[WARN] BM25 index not found — hybrid will use dense only.")

    if args.interactive:
        _interactive_loop(embedder, bm25_index, args)
    elif args.query:
        _run_query(args.query, embedder, bm25_index, args)
    else:
        parser.print_help()
        sys.exit(1)


def _run_query(query: str, embedder, bm25_index, args):
    from app.retrieval.chroma_store import retrieve_dense
    from app.retrieval.bm25 import retrieve_bm25
    from app.retrieval.hybrid import retrieve_hybrid, compare_retrieval_methods
    from app.retrieval.query_rewriter import retrieve_with_rewriting

    method = args.method
    top_k = args.top_k

    try:
        if args.rewrite:
            output = retrieve_with_rewriting(query, embedder, bm25_index, top_k=top_k)
            results = output["results"]
            metadata = {
                "queries_used": output["queries_used"],
                "rewrites_used": output["rewrites_used"],
                "rewriting_changed_results": output["rewriting_changed_results"],
            }
        elif method == "dense":
            results = retrieve_dense(query, embedder, top_k=top_k)
            metadata = {"method": "dense"}
        elif method == "bm25":
            results = retrieve_bm25(query, top_k=top_k, index=bm25_index)
            metadata = {"method": "bm25"}
        elif method == "hybrid":
            results = retrieve_hybrid(query, embedder, bm25_index=bm25_index, top_k=top_k)
            metadata = {"method": "hybrid_rrf"}
        elif method == "compare":
            comparison = compare_retrieval_methods(query, embedder, bm25_index, top_k=top_k)
            if args.json:
                print(json.dumps(comparison, indent=2, default=str))
            else:
                _print_comparison(comparison)
            return

    except Exception as exc:
        print(f"[ERROR] Retrieval error: {exc}")
        sys.exit(1)

    if args.json:
        print(json.dumps({"query": query, "metadata": metadata, "results": results},
                          indent=2, default=str))
    else:
        _print_results(query, results, metadata)


def _print_results(query: str, results: list, metadata: dict):
    print(f"\n{'='*60}")
    print(f"  Query: {query!r}")
    print(f"  Method: {metadata.get('method', 'with-rewriting')}")
    if "queries_used" in metadata:
        print(f"  Queries used: {metadata['queries_used']}")
    print(f"  Results: {len(results)}")
    print(f"{'='*60}")

    if not results:
        print("  No results found.")
        return

    for r in results:
        print(f"\n  [{r['rank']}] chunk_id: {r['chunk_id']}")
        print(f"       source_file : {r.get('source_file') or 'N/A'}")
        print(f"       chunk_index : {r.get('chunk_index', 'N/A')}")
        print(f"       total_pages : {r.get('total_pages', 'N/A')}")
        if "distance" in r and r["distance"] is not None:
            print(f"       distance    : {r['distance']:.4f}")
        if "rrf_score" in r:
            print(f"       rrf_score   : {r['rrf_score']:.6f}")
            print(f"       dense_rank  : {r.get('dense_rank', 'N/A')}")
            print(f"       bm25_rank   : {r.get('bm25_rank', 'N/A')}")
        if "bm25_score" in r and "rrf_score" not in r:
            print(f"       bm25_score  : {r['bm25_score']:.4f}")
        text = r.get("text", "")
        print(f"       text        : {text[:200]!r}{'...' if len(text) > 200 else ''}")
    print()


def _print_comparison(comparison: dict):
    print(f"\n{'='*70}")
    print(f"  Comparison for: {comparison['query']!r}")
    print(f"{'='*70}")

    ov = comparison.get("overlap_analysis", {})
    print(f"\n  Overlap analysis:")
    print(f"    Dense-only results    : {ov.get('dense_only', '?')}")
    print(f"    BM25-only results     : {ov.get('bm25_only', '?')}")
    print(f"    In both retrievers    : {ov.get('in_both', '?')}")
    print(f"    Final hybrid results  : {ov.get('in_hybrid', '?')}")

    for method_key in ("dense", "bm25", "hybrid"):
        results = comparison.get(method_key, [])
        print(f"\n  [{method_key.upper()}] — {len(results)} results:")
        for r in results[:3]:
            text = r.get("text", "")
            print(f"    [{r.get('rank', '?')}] {r['chunk_id']} | "
                  f"src={r.get('source_file') or 'N/A'} | "
                  f"{text[:80]!r}{'...' if len(text) > 80 else ''}")
    print()


def _interactive_loop(embedder, bm25_index, args):
    print("\nLawRAG Interactive Query (type 'quit' to exit)")
    print(f"  Method: {args.method}  |  Top-k: {args.top_k}")
    print("-" * 40)
    while True:
        try:
            query = input("\nQuery> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break
        if query.lower() in ("quit", "exit", "q"):
            break
        if not query:
            continue
        _run_query(query, embedder, bm25_index, args)


if __name__ == "__main__":
    main()
