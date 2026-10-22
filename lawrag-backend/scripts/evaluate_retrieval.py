#!/usr/bin/env python3
"""
evaluate_retrieval.py — Retrieval evaluation suite
====================================================
Runs the evaluation question set against all three retrieval methods
and produces a structured evaluation report.

Evaluation set: tests/evaluation_questions.jsonl
Metrics: Recall@k, MRR@k, Precision@k, source traceability
Methods: dense, bm25, hybrid, hybrid+rewrite

Usage:
    python scripts/evaluate_retrieval.py
    python scripts/evaluate_retrieval.py --provider mock --method all
    python scripts/evaluate_retrieval.py --top-k 10
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("evaluate_retrieval")

EVAL_SET_PATH = Path(__file__).resolve().parents[1] / "tests" / "evaluation_questions.jsonl"


def main():
    parser = argparse.ArgumentParser(description="Evaluate LawRAG retrieval quality")
    parser.add_argument(
        "--eval-set",
        default=str(EVAL_SET_PATH),
        help="Path to evaluation JSONL file",
    )
    parser.add_argument(
        "--method",
        choices=["dense", "bm25", "hybrid", "rewrite", "all"],
        default="all",
        help="Retrieval method to evaluate",
    )
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--provider", help="Override EMBEDDING_PROVIDER")
    parser.add_argument("--output", help="Path for evaluation report JSON")
    args = parser.parse_args()

    if args.provider:
        os.environ["EMBEDDING_PROVIDER"] = args.provider

    from app import config
    from app.retrieval.embeddings import get_embedder

    eval_path = Path(args.eval_set)
    if not eval_path.exists():
        print(f"[ERROR] Evaluation set not found: {eval_path}")
        sys.exit(1)

    # Load eval questions
    questions = []
    with open(eval_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                try:
                    questions.append(json.loads(line))
                except json.JSONDecodeError as e:
                    logger.warning("Skipping malformed line: %s", e)

    if not questions:
        print("[ERROR] No evaluation questions found.")
        sys.exit(1)

    print(f"\n{'='*65}")
    print(f"  LawRAG — Retrieval Evaluation")
    print(f"{'='*65}")
    print(f"  Questions   : {len(questions)}")
    print(f"  Top-k       : {args.top_k}")
    print(f"  Method(s)   : {args.method}")
    print(f"  Eval set    : {eval_path.name}")
    print()

    # Load embedder
    try:
        embedder = get_embedder()
    except Exception as exc:
        print(f"[ERROR] Embedder error: {exc}")
        sys.exit(1)

    # Load BM25 index
    bm25_index = None
    try:
        from app.retrieval.bm25 import load_bm25_index
        bm25_index = load_bm25_index()
    except Exception as exc:
        if args.method in ("bm25", "all"):
            print(f"[WARN] BM25 index unavailable: {exc}")

    methods_to_run = (
        ["dense", "bm25", "hybrid", "rewrite"]
        if args.method == "all"
        else [args.method]
    )

    all_results: dict = {}
    for method in methods_to_run:
        print(f"  Running method: {method}…")
        method_results = _evaluate_method(
            questions, method, embedder, bm25_index, args.top_k
        )
        all_results[method] = method_results
        _print_method_summary(method, method_results)

    # ── Produce report ─────────────────────────────────────────────────────
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "eval_set": str(eval_path),
        "num_questions": len(questions),
        "top_k": args.top_k,
        "embedding_model": embedder.model_id,
        "dataset_revision": config.HF_DATASET_REVISION,
        "results_by_method": all_results,
    }

    output_path = args.output or str(config.REPORTS_DIR / "evaluation_report.json")
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False, default=str)

    print(f"\n  [OK] Evaluation report saved: {output_path}")
    print(f"{'='*65}\n")


def _evaluate_method(
    questions: list, method: str, embedder, bm25_index, top_k: int
) -> dict:
    """Run one retrieval method over all questions and compute metrics."""
    from app.retrieval.chroma_store import retrieve_dense
    from app.retrieval.bm25 import retrieve_bm25
    from app.retrieval.hybrid import retrieve_hybrid
    from app.retrieval.query_rewriter import retrieve_with_rewriting

    per_question = []
    recall_values = []
    mrr_values = []
    precision_values = []
    source_traceable = 0

    for q in questions:
        qid = q.get("test_id", "?")
        question = q.get("question", "")
        expected = q.get("relevant_chunk_ids", [])  # may be empty if unknown
        answerability = q.get("expected_answerability", "unknown")

        # Run retrieval
        try:
            if method == "dense":
                results = retrieve_dense(question, embedder, top_k=top_k)
            elif method == "bm25":
                if bm25_index is None:
                    results = []
                else:
                    results = retrieve_bm25(question, top_k=top_k, index=bm25_index)
            elif method == "hybrid":
                results = retrieve_hybrid(question, embedder, bm25_index=bm25_index, top_k=top_k)
            elif method == "rewrite":
                out = retrieve_with_rewriting(question, embedder, bm25_index, top_k=top_k)
                results = out["results"]
            else:
                results = []
            error = None
        except Exception as exc:
            results = []
            error = str(exc)
            logger.warning("Method %s failed for Q%s: %s", method, qid, exc)

        retrieved_ids = [r["chunk_id"] for r in results]

        # Source traceability
        traceable = sum(
            1 for r in results
            if r.get("source_file") or r.get("source_id")
        )
        if results:
            source_traceable += traceable

        # Compute metrics (only when we have relevance labels)
        recall = None
        mrr = None
        precision = None

        if expected:
            # Recall@k: fraction of expected chunks found in top-k
            found = sum(1 for eid in expected if eid in retrieved_ids)
            recall = found / len(expected) if expected else 0.0
            recall_values.append(recall)

            # MRR@k: 1/rank of first relevant result
            mrr = 0.0
            for rank, cid in enumerate(retrieved_ids, start=1):
                if cid in expected:
                    mrr = 1.0 / rank
                    break
            mrr_values.append(mrr)

            # Precision@k
            relevant_retrieved = sum(1 for cid in retrieved_ids if cid in expected)
            precision = relevant_retrieved / len(retrieved_ids) if retrieved_ids else 0.0
            precision_values.append(precision)

        per_question.append({
            "test_id": qid,
            "question": question,
            "expected_answerability": answerability,
            "retrieved_count": len(results),
            "relevant_expected": expected,
            "retrieved_ids": retrieved_ids[:top_k],
            "recall_at_k": recall,
            "mrr_at_k": mrr,
            "precision_at_k": precision,
            "source_traceable_count": traceable,
            "top_result": results[0] if results else None,
            "error": error,
        })

    def _avg(lst):
        return round(sum(lst) / len(lst), 4) if lst else None

    return {
        "per_question": per_question,
        "aggregate": {
            "recall_at_k": _avg(recall_values),
            "mrr_at_k": _avg(mrr_values),
            "precision_at_k": _avg(precision_values),
            "questions_with_labels": len(recall_values),
            "questions_without_labels": len(questions) - len(recall_values),
            "source_traceable_count": source_traceable,
        },
    }


def _print_method_summary(method: str, results: dict):
    agg = results.get("aggregate", {})
    print(f"\n  [{method.upper()}]")
    print(f"    Questions with labels : {agg.get('questions_with_labels', '?')}")
    print(f"    Recall@k              : {agg.get('recall_at_k', 'N/A')}")
    print(f"    MRR@k                 : {agg.get('mrr_at_k', 'N/A')}")
    print(f"    Precision@k           : {agg.get('precision_at_k', 'N/A')}")
    print(f"    Source traceable hits : {agg.get('source_traceable_count', '?')}")
    print()


if __name__ == "__main__":
    main()
