# LawRAG Implementation Plan

**Execution model:** Build one phase at a time. Do not proceed until the current phase's acceptance gate is met or blockers are explicitly documented.

## Working rules for the coding agent

1. Read `LawRAG_PRD.md`, `TECHNICAL_DESIGN.md`, and `EVALUATION_PLAN.md` before changing code.
2. Inspect the existing repository before creating or overwriting files.
3. Inspect actual dataset/provider schemas and documentation; never assume fields or APIs.
4. Implement real functionality, not placeholders or mocked success paths.
5. Run tests and commands, fix failures, and report actual output.
6. Never fabricate legal citations, dataset facts, metrics, or test results.
7. Keep credentials in environment variables; never print or commit secrets.
8. Make changes incrementally and keep the project runnable.
9. Record files changed, commands run, results, limitations, and next steps at the end of each phase.
10. Do not implement later phases prematurely.

## Phase 1 — Dataset ingestion, indexing, and retrieval

### Work
- Inspect the repository and the Hugging Face dataset `dedol-hf/india-case-legal-rag`.
- Confirm the actual file format, schema, dataset revision, record count, and license.
- Download the dataset automatically and validate records.
- Normalize text and metadata without inventing missing information.
- Implement a configurable hosted embedding provider.
- Batch and cache document embeddings; support retry/resume where practical.
- Store vectors, text, and metadata in ChromaDB with stable IDs and idempotent indexing.
- Implement dense retrieval and BM25 lexical retrieval.
- Add rank fusion (e.g. Reciprocal Rank Fusion) with deduplication and preserved provenance.
- Implement query rewriting as a bounded retrieval improvement step, then measure whether it helps.
- Provide command-line tools for inspection, ingestion/indexing, and querying.
- Build tests and a small human-reviewed retrieval evaluation set.

### Acceptance gate
- Ingestion report contains real counts and revision.
- Indexing is repeatable.
- Dense and hybrid retrieval work.
- Query results include source metadata.
- Evaluation results are recorded without invented metrics.
- Unit tests and a small integration test pass, or blockers are reported precisely.

## Phase 2 — LangGraph Agentic RAG

### Work
- Define typed graph state.
- Implement query analysis, retrieval, evidence assessment, bounded query rewrite/retry, grounded synthesis, citation validation, and finalization.
- Route to answer generation only when evidence is sufficient.
- Route to abstention when evidence remains insufficient.
- Surface conflicting or ambiguous passages where found.
- Keep citations derived from retrieved records rather than free-form model output.
- Add tests for supported, unsupported, paraphrased, conflicting, and provider-error cases.
- Track retrieval attempts and evidence status in the result.

### Acceptance gate
- The graph has explicit, inspectable nodes and conditional transitions.
- Retries are bounded.
- Supported questions receive evidence-backed answers.
- Unsupported questions trigger an honest abstention.
- Citation IDs resolve to real retrieved chunks.
- Tests and evaluation results are documented.

## Phase 3 — FastAPI, frontend integration, and deployment

### Work
- Implement `GET /health` and `POST /api/query` with Pydantic request/response models.
- Add validation, safe errors, CORS, timeouts, and environment-based configuration.
- Integrate with the JavaScript frontend.
- Present answerability status, citations, source excerpts, loading states, and errors clearly.
- Configure deployment on Render and Vercel (or chosen equivalents).
- Use Chroma Cloud or another verified persistent vector store for deployed data.
- Keep indexing separate from web-worker startup.
- Run smoke tests against the deployed service.
- Rehearse a three-minute demo with a supported question and an unseen/unanswerable question.

### Acceptance gate
- Deployed health endpoint works.
- Deployed frontend can submit a query and render its answer and citations.
- Restart/redeploy does not silently destroy the only index.
- Secrets are not exposed.
- Smoke-test results and known free-tier limitations are documented.

## Final rubric review

Before declaring completion, map actual evidence to all six criteria:
- Problem relevance and clarity (10)
- Retrieval quality (10)
- Answer grounding (15)
- Evaluation and failure analysis (5)
- Demo and usability (5)
- Creativity and upgrades (5)

The total is 50 points. These are rubric targets, not guaranteed scores. Report any criterion that remains partially implemented.

## Final report format

At the end of each phase, provide:
- Summary of implemented functionality.
- Files created/modified.
- Commands executed.
- Tests executed and actual results.
- Dataset/provider/index details where relevant.
- Rubric criteria addressed.
- Known issues and limitations.
- Exact command(s) to run the current phase.
- Confirmation that the acceptance gate passed, or a precise list of blockers.
