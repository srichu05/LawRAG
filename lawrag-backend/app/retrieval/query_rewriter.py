"""
query_rewriter.py — Bounded query rewriting for retrieval improvement
======================================================================
Generates alternative search queries to improve recall for differently
phrased legal questions.

Design decisions:
  - At most 1-2 alternative queries (never unlimited)
  - Never introduces facts, parties, dates, or provisions not in the original
  - Preserves the original query — results are merged and deduplicated
  - Uses configured LLM provider only if REWRITER_PROVIDER is set
  - Falls back to deterministic offline rewrites (expansion/normalization)
  - Records whether rewriting changed the results
  - Does NOT simulate a live LLM call if provider is unavailable

Providers:
  - "openai"       : OpenAI chat completions (REWRITER_API_KEY required)
  - "huggingface"  : HF Inference API text generation (REWRITER_API_KEY required)
  - "offline"      : Deterministic rule-based expansion (no API needed)
  - ""  (empty)    : Disabled — returns original query only
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any

from app import config

logger = logging.getLogger(__name__)

# Offline legal-domain expansion rules
# Maps common terms to synonyms — add more as needed
_LEGAL_SYNONYMS: dict[str, list[str]] = {
    "breach of contract": ["contract violation", "contractual breach", "non-performance"],
    "fundamental rights": ["constitutional rights", "basic rights", "article 21"],
    "writ petition": ["habeas corpus", "mandamus", "certiorari"],
    "negligence": ["duty of care", "tortious liability", "carelessness"],
    "bail": ["anticipatory bail", "regular bail", "bail application"],
    "murder": ["culpable homicide", "section 302 ipc", "homicide"],
    "supreme court": ["apex court", "honourable court"],
    "appeal": ["civil appeal", "criminal appeal", "special leave petition", "slp"],
    "property": ["immovable property", "real estate", "land dispute"],
    "divorce": ["matrimonial dispute", "dissolution of marriage", "section 13 hma"],
}


class QueryRewriter:
    """
    Bounded query rewriter.
    Generates at most config.REWRITER_MAX_RETRIES alternative queries.
    """

    def __init__(self) -> None:
        self._provider = config.REWRITER_PROVIDER.lower() if config.REWRITER_PROVIDER else ""
        self._enabled = config.rewriter_configured()
        if not self._enabled:
            logger.info(
                "Query rewriting is disabled. "
                "Set REWRITER_PROVIDER, REWRITER_MODEL, and REWRITER_API_KEY to enable. "
                "Using offline deterministic fallback."
            )

    def rewrite(self, query: str) -> list[str]:
        """
        Generate alternative queries for the given query.

        Returns
        -------
        list of query strings: [original_query] + alternative queries
        The original is always first in the list.
        Maximum total: 1 (original) + 2 (alternatives) = 3
        """
        if not query or not query.strip():
            return [query]

        original = query.strip()
        alternatives: list[str] = []

        if self._enabled and self._provider in ("openai", "huggingface"):
            try:
                alternatives = self._llm_rewrite(original)
            except Exception as exc:
                logger.warning(
                    "LLM query rewriting failed: %s. "
                    "Falling back to offline rewriting.", exc
                )
                alternatives = self._offline_rewrite(original)
        else:
            alternatives = self._offline_rewrite(original)

        # Deduplicate and cap at 2 alternatives
        seen = {original.lower()}
        filtered = []
        for alt in alternatives:
            alt = alt.strip()
            if alt.lower() not in seen and alt:
                seen.add(alt.lower())
                filtered.append(alt)
                if len(filtered) >= 2:
                    break

        result = [original] + filtered
        logger.debug(
            "Query rewriting: original=%r alternatives=%r", original, filtered
        )
        return result

    def _offline_rewrite(self, query: str) -> list[str]:
        """
        Deterministic, rule-based offline query rewriting.
        Expands legal synonyms to improve recall without LLM.
        """
        alternatives: list[str] = []
        query_lower = query.lower()

        for term, synonyms in _LEGAL_SYNONYMS.items():
            if term in query_lower:
                for syn in synonyms[:1]:  # at most 1 synonym expansion
                    alt = re.sub(re.escape(term), syn, query_lower, flags=re.IGNORECASE)
                    if alt.lower() != query.lower():
                        alternatives.append(alt)
                break  # one expansion is enough

        # Fallback: return the query stripped of question marks / interrogatives
        if not alternatives:
            simplified = re.sub(
                r"^(what|when|where|who|how|why|does|is|are|can|could|should|do)\s+",
                "",
                query.lower(),
            ).strip()
            if simplified and simplified.lower() != query.lower():
                alternatives.append(simplified)

        return alternatives[:2]

    def _llm_rewrite(self, query: str) -> list[str]:
        """
        Use a configured LLM to generate alternative queries.
        Strictly bounded: at most 2 alternatives, no invented facts.
        """
        max_attempts = config.REWRITER_MAX_RETRIES

        prompt = (
            "You are a legal search assistant helping improve retrieval from an "
            "Indian Supreme Court judgment database.\n\n"
            "Rewrite the following legal question to improve search results. "
            "Generate exactly 1 or 2 alternative search queries. "
            "Rules:\n"
            "- Do NOT add legal facts, parties, dates, or provisions not in the original.\n"
            "- Keep the same legal issue.\n"
            "- Output ONLY the alternative queries, one per line, no numbering, no extra text.\n\n"
            f"Original question: {query}\n\n"
            "Alternative queries:"
        )

        if self._provider == "openai":
            return self._openai_rewrite(prompt, max_attempts)
        elif self._provider == "huggingface":
            return self._hf_rewrite(prompt, max_attempts)
        else:
            raise ValueError(f"Unsupported rewriter provider: {self._provider}")

    def _openai_rewrite(self, prompt: str, max_attempts: int) -> list[str]:
        try:
            import openai  # type: ignore
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

        client = openai.OpenAI(api_key=config.REWRITER_API_KEY)

        for attempt in range(max_attempts + 1):
            try:
                response = client.chat.completions.create(
                    model=config.REWRITER_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200,
                    temperature=0.3,
                )
                text = response.choices[0].message.content or ""
                return _parse_alternatives(text)
            except Exception as exc:
                if attempt < max_attempts:
                    time.sleep(2 ** attempt)
                else:
                    raise RuntimeError(f"OpenAI rewrite failed: {exc}") from exc

        return []

    def _hf_rewrite(self, prompt: str, max_attempts: int) -> list[str]:
        import requests

        url = f"https://api-inference.huggingface.co/models/{config.REWRITER_MODEL}"
        headers = {
            "Authorization": f"Bearer {config.REWRITER_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "inputs": prompt,
            "parameters": {"max_new_tokens": 100, "temperature": 0.3},
            "options": {"wait_for_model": True},
        }

        for attempt in range(max_attempts + 1):
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list) and data:
                        text = data[0].get("generated_text", "")
                        # Remove the prompt from the output if echoed
                        if prompt in text:
                            text = text.split("Alternative queries:")[-1]
                        return _parse_alternatives(text)
                elif resp.status_code in (429, 503):
                    time.sleep(2 ** attempt + 1)
                else:
                    raise RuntimeError(f"HF API {resp.status_code}: {resp.text[:200]}")
            except Exception as exc:
                if attempt < max_attempts:
                    time.sleep(2 ** attempt)
                else:
                    raise RuntimeError(f"HF rewrite failed: {exc}") from exc

        return []


def _parse_alternatives(text: str) -> list[str]:
    """Parse LLM output into a list of alternative query strings."""
    lines = [
        re.sub(r"^\s*[\d\.\-\*]+\s*", "", line).strip()
        for line in text.strip().splitlines()
        if line.strip() and len(line.strip()) > 5
    ]
    return lines[:2]


# ---------------------------------------------------------------------------
# Retrieval with rewriting
# ---------------------------------------------------------------------------

def retrieve_with_rewriting(
    query: str,
    embedder,
    bm25_index=None,
    top_k: int | None = None,
    rewriter: QueryRewriter | None = None,
) -> dict[str, Any]:
    """
    Run hybrid retrieval with optional query rewriting.
    Merges results from original and rewritten queries, deduplicates by chunk_id.

    Returns
    -------
    dict with keys:
      - results     : final merged result list (sorted by best rank)
      - queries_used: list of queries that were run
      - rewrites_used: number of alternative queries
      - rewriting_changed_results: bool
    """
    from app.retrieval.hybrid import retrieve_hybrid

    if top_k is None:
        top_k = config.TOP_K
    if rewriter is None:
        rewriter = QueryRewriter()

    queries = rewriter.rewrite(query)
    queries_used = queries[:3]  # hard cap: original + max 2 alternatives

    all_results: list[dict] = []
    seen_ids: set[str] = set()

    for q in queries_used:
        try:
            results = retrieve_hybrid(
                q, embedder, bm25_index=bm25_index, top_k=top_k * 2
            )
            for r in results:
                cid = r["chunk_id"]
                if cid not in seen_ids:
                    seen_ids.add(cid)
                    # Tag which query found this result
                    r["source_query"] = q
                    all_results.append(r)
        except Exception as exc:
            logger.error("Retrieval for query %r failed: %s", q, exc)

    # Sort by rrf_score if available, else by rank
    all_results.sort(
        key=lambda r: r.get("rrf_score", 0.0),
        reverse=True,
    )

    original_ids = {
        r["chunk_id"]
        for r in retrieve_hybrid(query, embedder, bm25_index=bm25_index, top_k=top_k)
    } if len(queries_used) > 1 else set()

    final = all_results[:top_k]
    rewriting_changed = (
        len(queries_used) > 1
        and any(r["chunk_id"] not in original_ids for r in final)
    ) if original_ids else False

    return {
        "results": final,
        "queries_used": queries_used,
        "rewrites_used": len(queries_used) - 1,
        "rewriting_changed_results": rewriting_changed,
    }
