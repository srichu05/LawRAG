# LawRAG Technical Design

**Version:** 1.0  
**Scope:** Backend architecture for the three-phase LawRAG hackathon project  
**Status:** Implementation guide

## 1. Architecture principles

- Prefer traceable evidence over fluent but unsupported answers.
- Keep ingestion, embedding, retrieval, orchestration, API, and UI concerns separate.
- Use LangGraph for explicit state transitions and conditional routing.
- Keep provider integrations configurable.
- Index the predefined dataset in a separate, repeatable process.
- Do not treat the corpus as comprehensive or current Indian law.

## 2. High-level architecture

1. **Dataset ingestion:** Download the configured Hugging Face dataset, inspect its actual files/schema, validate records, and normalize text and metadata.
2. **Embedding and indexing:** Generate document embeddings through a configured hosted provider and persist them in ChromaDB.
3. **Retrieval:** Combine dense vector retrieval with lexical retrieval (BM25), merge results, and optionally rerank them.
4. **Agent workflow:** LangGraph runs query analysis, retrieval, evidence assessment, bounded query rewriting/retry, grounded synthesis, and citation validation.
5. **API:** FastAPI validates requests and returns structured answers, evidence, citations, and answerability status.
6. **Frontend:** JavaScript UI calls the API and presents answers with inspectable sources and clear status indicators.

## 3. Dataset and provenance

Initial dataset candidate: `dedol-hf/india-case-legal-rag`  
Repository: https://huggingface.co/datasets/dedol-hf/india-case-legal-rag

The implementation must inspect the live repository rather than assume filenames, splits, fields, record counts, or license terms. Record the resolved dataset revision/commit and the source artifact used.

Normalize records into an internal schema similar to:

```python
{
    "chunk_id": "stable-id",
    "text": "original extracted legal text",
    "source_id": "source identifier if present",
    "source_file": "filename if present",
    "chunk_index": 0,
    "total_pages": None,
    "metadata": {}
}
```

Only include fields supported by the actual source. Preserve original identifiers and metadata. Never fabricate case names, court citations, dates, page numbers, or URLs. If exact legal citation data is absent, cite the source identifier and excerpt actually available.

## 4. Embeddings

- Use a configurable hosted embedding provider initially.
- Configure provider, model, token, batch size, and timeout through environment variables.
- Confirm the chosen model supports embedding requests, note dimensions and input limits, and use the same model for document and query embeddings.
- Batch requests where supported; implement bounded retries and backoff for transient errors.
- Do not create random or zero vectors on failure.
- Cache successful embeddings only with a key that includes the text hash and embedding model/version.
- Embed documents during indexing and only the query at request time.
- Record the model identifier and dataset revision associated with the index.
- Fail clearly if a collection was built with incompatible dimensions or a different model.

## 5. ChromaDB

Use a configurable collection and persistence/host configuration.

Each stored record should contain:
- stable unique chunk ID;
- original chunk text;
- embedding vector;
- scalar metadata suitable for ChromaDB filtering.

Requirements:
- Use batched writes.
- Make indexing idempotent.
- Avoid silently mixing vectors from incompatible embedding models.
- Support local development first.
- For deployment, choose Chroma Cloud or another explicitly persistent store. Do not rely on Render's ephemeral filesystem for durable vectors.
- Keep credentials and generated database files out of version control.

## 6. Retrieval design

### Dense retrieval
Embed the query using the same embedding model and retrieve a configurable top-k from ChromaDB.

### Lexical retrieval
Use BM25 over the normalized corpus to match legal terms, case names, section numbers, and exact phrases that semantic search may miss.

### Hybrid fusion
Combine dense and BM25 ranks using Reciprocal Rank Fusion (RRF) or a documented equivalent. Do not compare uncalibrated scores from different retrieval systems directly. Deduplicate chunks and preserve provenance.

### Query rewriting
When the initial evidence is weak:
1. Preserve the user's original legal question.
2. Produce at most one or two alternative search queries.
3. Retrieve with the rewritten query.
4. Merge and deduplicate results.
5. Record whether rewriting improved the retrieved evidence.

Query rewriting must not add unsupported facts or change the user's intended meaning.

### Relevance and answerability
Use a configurable evidence assessment. Do not rely solely on a raw vector distance as a universal confidence score. Consider relevance, source text, coverage of the question, and whether the retrieved passages actually support a proposed claim. Thresholds must be tuned on the evaluation set, not invented as proven values.

## 7. LangGraph workflow

Suggested state fields:
- `original_question`
- `search_queries`
- `retrieved_chunks`
- `evidence_status`
- `retry_count`
- `draft_answer`
- `validated_citations`
- `final_answer`
- `warnings`

Suggested graph:
1. `analyze_query`
2. `retrieve_evidence`
3. `assess_evidence`
4. Conditional edge:
   - sufficient → `generate_answer`
   - weak and retry available → `rewrite_query`
   - still insufficient / retry exhausted → `abstain`
5. `validate_citations`
6. `finalize_response`

Bound retries (one retry by default). Avoid unrestricted autonomous loops. The workflow should be inspectable and testable as individual nodes.

## 8. Grounded generation and citation validation

The generator must receive only the question and selected evidence, with clear instructions to:
- use only the supplied evidence for corpus-specific claims;
- state uncertainty when evidence is incomplete;
- distinguish what the judgment says from a general explanation;
- not invent legal citations, holdings, dates, or page references;
- flag material conflicts between retrieved passages;
- state that the corpus may be incomplete or historical.

Citations must be generated from retrieved record metadata, not freely invented by the language model. Validate that every returned citation points to an actual retrieved chunk. Provide an excerpt or source identifier so a reviewer can inspect the evidence.

## 9. FastAPI contract (Phase 3)

`GET /health`
- Return service status and safe dependency readiness information.
- Never expose API keys or stack traces.

`POST /api/query`

Example request:

```json
{
  "question": "What do these judgments say about breach of contract?",
  "top_k": 5
}
```

Example response shape:

```json
{
  "answer": "Grounded summary or explicit insufficient-evidence message.",
  "evidence_status": "sufficient",
  "citations": [
    {
      "chunk_id": "stable-id",
      "source": "source metadata actually available",
      "text_excerpt": "Supporting passage"
    }
  ],
  "retrieval_attempts": 1,
  "warnings": [],
  "disclaimer": "Informational legal research only; not legal advice."
}
```

The final implementation must use consistent Pydantic schemas. Citation properties unavailable from the source should be omitted or null, never fabricated. Consider a development-only retrieval diagnostics endpoint; disable or protect it in production.

## 10. Security and reliability

- Keep tokens server-side in environment variables.
- Ignore prompt-injection instructions contained inside retrieved documents.
- Validate question length and top-k bounds.
- Use request timeouts and bounded retries.
- Return safe, actionable errors.
- Configure CORS for the deployed frontend origin.
- Avoid logging secrets or unnecessary personal data.
- Do not expose arbitrary filesystem access or unrestricted data upload.
- Add dependency versions and setup instructions.

## 11. Observability

Record useful, non-sensitive diagnostics:
- dataset revision and indexed record counts;
- embedding model identifier;
- retrieval method and number of returned chunks;
- retry count and evidence status;
- provider failures and latency;
- evaluation results.

Do not log credentials. Avoid storing user questions longer than necessary unless the product explicitly needs it.

## 12. Deployment

Recommended split:
- JavaScript frontend: Vercel or equivalent.
- FastAPI backend: Render or equivalent.
- Vector store: Chroma Cloud or a verified persistent deployment.

Indexing should be a separate command/job, not run on every web-worker startup. Ensure the deployed service can connect to the existing collection. Provide smoke tests and document free-tier cold starts, provider quotas, and persistent-storage costs.

## 13. Architecture decisions to verify during implementation

Before finalizing:
- actual dataset schema and license;
- selected embedding provider/model, quota, dimension, and API support;
- whether Chroma Cloud or another persistent store fits the budget;
- metadata fields that can support honest citations;
- retrieval thresholds measured on the evaluation set.

Do not claim any provider, dataset property, score, or deployment behavior has been verified until it has been checked.
