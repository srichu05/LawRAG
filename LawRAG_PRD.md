# LawRAG — Product Requirements Document (PRD)

**Version:** 1.0  
**Status:** Initial implementation specification  
**Product type:** Agentic Retrieval-Augmented Generation (RAG) for Indian legal research  
**Primary users:** Students, researchers, and members of the public seeking document-grounded legal information

---

## 1. Product Overview

LawRAG is a legal research assistant that answers questions using retrieved passages from a predefined corpus of Indian Supreme Court judgments. It uses a controlled LangGraph workflow to retrieve evidence, assess whether the evidence is sufficient, retry retrieval when appropriate, and generate answers with source references.

The product is an informational research aid. It is **not a lawyer, does not provide a binding legal opinion, and must not imply that its dataset represents all current Indian law**.

## 2. Problem Statement

Legal judgments can be lengthy and difficult to search. Users may struggle to locate relevant passages and understand how those passages relate to a question. A generic chatbot may produce unsupported claims or fabricated citations.

LawRAG aims to make a bounded legal corpus easier to explore by:
- retrieving relevant passages from judgments;
- generating concise explanations grounded in retrieved evidence;
- displaying traceable source metadata;
- identifying insufficient or conflicting evidence; and
- abstaining when the available corpus does not support an answer.

## 3. Goals

1. Build a working backend that ingests a predefined Hugging Face legal dataset automatically.
2. Implement semantic retrieval over legal judgment chunks.
3. Use LangGraph to orchestrate a controlled, observable Agentic RAG workflow.
4. Produce answers grounded in retrieved passages and return source references.
5. Handle unanswerable questions without inventing legal facts or citations.
6. Expose a stable FastAPI interface for a JavaScript frontend.
7. Deploy a demonstrable version with repeatable setup, indexing, and smoke tests.

## 4. Non-Goals

The initial release will not:
- replace a lawyer or provide binding legal advice;
- determine case outcomes or guarantee legal eligibility or rights;
- claim to cover all Indian legislation or the latest legal position;
- autonomously file complaints, submit forms, or contact courts;
- provide a comprehensive legal case-law search engine;
- treat generated summaries as authoritative legal text;
- ingest arbitrary user-uploaded documents unless added as a later feature.

## 5. Target Users and Use Cases

### Primary users
- Law and university students conducting preliminary legal research.
- Researchers exploring judgments in the supplied corpus.
- Members of the public seeking a plain-language explanation of material in a retrieved judgment.

### Core use cases
1. Ask a natural-language question about a legal issue.
2. Retrieve relevant judgment passages.
3. Read a concise answer with supporting sources.
4. Inspect source text and available document metadata.
5. Receive an explicit insufficient-evidence response when no adequate support is found.
6. See when retrieved sources appear to disagree or do not directly address the question.

## 6. Dataset Requirements

### Initial dataset
- Hugging Face repository: `dedol-hf/india-case-legal-rag`
- Intended content: pre-chunked text from Indian Supreme Court judgments.
- Expected size from initial inspection/research: approximately 9,375 records and about 8 MB. These values are **expectations, not guarantees**; implementation must inspect the live repository and report actual values.

### Ingestion requirements
The coding agent must:
1. Download the dataset directly from Hugging Face during the ingestion process.
2. Inspect available files and dataset configuration instead of assuming a filename, split, or schema.
3. Prefer the documented JSONL or Parquet artifact that is available and suitable.
4. Validate the schema before indexing.
5. Preserve original record identifiers and all useful source metadata.
6. Normalize records into a stable internal representation, including:
   - `chunk_id`
   - `text`
   - `source_file` or source identifier, when present
   - `chunk_index`, when present
   - `total_pages`, when present
   - original metadata
7. Skip or quarantine records with missing/blank text and report the count.
8. Detect duplicate identifiers and report them; do not silently overwrite records.
9. Save an ingestion summary including dataset revision, source file, record count, valid count, skipped count, and timestamp.
10. Make ingestion repeatable and idempotent where practical.
11. Avoid downloading or re-embedding the corpus on every API request or normal server restart.
12. Pin a dataset revision or record the resolved revision to support reproducibility.
13. Check the dataset license and document relevant usage limitations before public redistribution.

### Citation and provenance requirements
- Every retrieved chunk must retain its source metadata.
- Never invent a case name, court citation, judgment date, page number, or URL.
- If exact case citation or page information is unavailable, show only the source information actually present and label it accordingly.
- Inspect sample records to determine whether case names, dates, and exact page numbers can be reliably derived.
- Keep the original passage available for inspection.
- Distinguish a source filename from a formal legal citation.

### Known limitation
The corpus is a bounded collection of judgments, not a complete or necessarily up-to-date collection of Indian law. The app must communicate this limitation. For current statutory claims, the system would need an additional verified source of legislation and update procedures.

## 7. Functional Requirements

### Phase 1 — Dataset ingestion and retrieval foundation

**Objective:** Produce a runnable pipeline that downloads, validates, indexes, and searches the dataset.

Requirements:
- Provide a repeatable ingestion/indexing command.
- Use a configurable embedding provider; do not hard-code API keys.
- Generate document embeddings during indexing, not during every query.
- Cache or persist the index so routine restarts do not trigger unnecessary re-embedding.
- Store chunk text, embeddings, stable IDs, and metadata in ChromaDB.
- Support semantic similarity search.
- Return top-k passages with relevance/distance information where supported and their source metadata.
- Validate inputs and handle provider/network/database errors clearly.
- Provide a retrieval CLI or minimal test script before adding agents.

Acceptance criteria:
- A clean setup can download and inspect the configured dataset using documented commands.
- An indexing run reports total, valid, skipped, and indexed record counts.
- Re-running indexing does not silently create duplicate records.
- A sample legal query returns relevant passages and traceable source metadata.
- A query against an unrelated or unsupported topic can return low-confidence/no-evidence status rather than pretending to have an answer.
- API keys and credentials are never committed to source control.

### Phase 2 — LangGraph Agentic RAG and grounded response generation

**Objective:** Add a controlled workflow that answers questions based on retrieved evidence.

Suggested graph:
1. Query analysis / planning.
2. Retrieval from ChromaDB.
3. Evidence sufficiency and relevance check.
4. Conditional route:
   - sufficient evidence → answer generation;
   - weak evidence → rewrite query and retry retrieval once;
   - still insufficient → abstain.
5. Answer and citation validation.
6. Structured response.

Requirements:
- Use LangGraph for explicit state and conditional edges.
- Use LangChain integrations when useful for model, prompt, embedding, or retriever interfaces; avoid unnecessary abstraction.
- Bound retries (one retry by default) to prevent loops and excessive cost.
- Ground substantive legal claims in retrieved text.
- Return a clear abstention message when evidence is inadequate.
- Do not fabricate citations or imply that retrieved historical judgments establish current law.
- If retrieved passages conflict, report the conflict and show the relevant sources rather than forcing an unsupported conclusion.
- Separate source facts from generated explanation.
- Record minimal, useful diagnostic information for evaluation without logging secrets or unnecessary personal data.

Acceptance criteria:
- A supported test question yields an answer with source references.
- An unsupported question produces an explicit insufficient-evidence response.
- Weak initial retrieval triggers no more than the configured retry limit.
- Each citation maps to a retrieved record and the displayed source metadata.
- Tests cover successful retrieval, no evidence, retry, conflicting passages, and provider errors.
- The system does not claim a legal conclusion beyond the corpus.

### Phase 3 — FastAPI, frontend integration, evaluation, and deployment

**Objective:** Deliver a deployable backend for a JavaScript frontend.

Required endpoints:
- `GET /health` — service health and basic dependency status without exposing secrets.
- `POST /api/query` — accepts a user question and returns a grounded answer, citations, and evidence status.
- Optional development-only retrieval/debug endpoint, disabled in production or protected appropriately.

Example request:
```json
{
  "question": "What legal principles are discussed in the retrieved judgments about breach of contract?",
  "top_k": 5
}
```

Example response shape:
```json
{
  "answer": "A concise explanation grounded in the retrieved passages, or an explicit insufficient-evidence response.",
  "evidence_status": "sufficient",
  "citations": [
    {
      "chunk_id": "stable-chunk-id",
      "source": "source identifier actually present in metadata",
      "text_excerpt": "Supporting passage excerpt"
    }
  ],
  "retrieval_attempts": 1,
  "disclaimer": "Informational legal research only; not legal advice."
}
```

The exact schema must be implemented consistently and documented. Citation fields should be omitted or null when unavailable, not fabricated.

Deployment requirements:
- FastAPI backend deployable to Render.
- JavaScript frontend deployable to Vercel or another compatible host.
- Configure CORS for the actual frontend origin.
- Store provider credentials in deployment environment variables.
- Use a managed vector database or persistent storage for production/demo deployment; do not rely on Render's ephemeral filesystem for durable ChromaDB data.
- Do not run full dataset ingestion on every web-worker startup.
- Provide separate build/index and API-start commands where appropriate.
- Include startup and deployment smoke tests.
- Document cold-start and free-tier limitations.

Acceptance criteria:
- The deployed `/health` endpoint responds successfully.
- The frontend can call `/api/query` and display the answer and sources.
- Errors from model, embedding, and vector database providers return clear, non-sensitive responses.
- A redeploy does not silently destroy the only copy of the index.
- The README documents environment variables, local setup, ingestion, indexing, testing, and deployment.

## 8. Non-Functional Requirements

### Reliability
- Fail clearly when required configuration is missing.
- Handle empty questions, malformed requests, timeouts, and upstream provider errors.
- Avoid duplicate indexing and uncontrolled graph loops.

### Performance
- Index the corpus as a separate operation.
- Embed only the query at request time.
- Set configurable retrieval limits.
- Avoid loading a large local embedding model into a constrained Render free instance unless measured resource usage justifies it.

### Security
- Keep API keys server-side.
- Use `.env` locally and environment variables in deployment.
- Add `.env`, local databases, caches, and secrets to `.gitignore` as appropriate.
- Do not expose internal stack traces or credentials in API responses.
- Treat retrieved documents as untrusted input; ignore any instructions embedded in source text that attempt to control the system.

### Maintainability
- Separate ingestion, retrieval, graph workflow, API routes, configuration, and tests.
- Use type hints and clear interfaces.
- Pin or constrain dependency versions and document setup.
- Keep provider and dataset identifiers configurable.

### Legal safety
- Display a clear informational-use disclaimer.
- Do not claim the corpus is comprehensive or current.
- Do not invent sources, citations, or legal authorities.
- Abstain when supporting evidence is insufficient.
- Encourage consultation with a qualified legal professional for decisions requiring legal advice.

## 9. Suggested Repository Structure

```text
lawrag-backend/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── api/
│   │   └── routes.py
│   ├── ingestion/
│   │   ├── download.py
│   │   ├── validate.py
│   │   └── index.py
│   ├── retrieval/
│   │   └── chroma_store.py
│   ├── graph/
│   │   ├── state.py
│   │   ├── nodes.py
│   │   └── workflow.py
│   └── schemas/
│       └── query.py
├── scripts/
│   ├── inspect_dataset.py
│   └── build_index.py
├── tests/
│   ├── test_ingestion.py
│   ├── test_retrieval.py
│   ├── test_graph.py
│   └── test_api.py
├── data/                 # generated; do not commit large data by default
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

The coding agent may adjust this structure if it provides a clear reason and preserves separation of concerns.

## 10. Environment Configuration

Provide a `.env.example` with placeholders, never real credentials. Likely variables include:

```dotenv
HF_DATASET_ID=dedol-hf/india-case-legal-rag
HF_DATASET_REVISION=
EMBEDDING_PROVIDER=
EMBEDDING_MODEL=
EMBEDDING_API_KEY=
LLM_PROVIDER=
LLM_MODEL=
LLM_API_KEY=
CHROMA_MODE=
CHROMA_PATH=./data/chroma
CHROMA_HOST=
CHROMA_API_KEY=
FRONTEND_ORIGIN=http://localhost:5173
TOP_K=5
MAX_RETRIEVAL_RETRIES=1
```

Only the variables required by the selected providers should be mandatory. The implementation must document the actual chosen provider and configuration.

## 11. Evaluation Plan

Create a small manually reviewed evaluation set containing:
- questions with clearly retrievable evidence;
- paraphrased versions of supported questions;
- questions unrelated to the corpus;
- questions where the top results are weak or ambiguous;
- cases with potentially conflicting passages.

Track:
- retrieval relevance / whether supporting passages appear in top-k;
- citation validity / whether each citation maps to a retrieved source;
- answer grounding / whether claims are supported by evidence;
- abstention correctness / whether the system declines unsupported questions;
- latency and provider failures.

Do not report an evaluation score unless the tests have actually been run. Keep a record of failures and fixes.

## 12. Delivery Plan

### Phase 1: Ingestion and retrieval
**Deliverable:** Dataset download, validation, indexing, and retrieval working locally.

### Phase 2: Agentic RAG
**Deliverable:** LangGraph workflow with evidence verification, bounded retry, grounded answers, and abstention.

### Phase 3: API and deployment
**Deliverable:** FastAPI integration, frontend connectivity, evaluation, and deployed demo.

Each phase must be completed, tested, and documented before the next phase begins.

## 13. Definition of Done

The initial project is complete when:
- the dataset can be downloaded and validated reproducibly;
- retrieval returns relevant passages with traceable metadata;
- LangGraph follows the bounded evidence-verification workflow;
- unsupported questions are handled honestly;
- substantive answer claims are supported by retrieved evidence;
- API responses follow a documented schema;
- the JavaScript frontend can use the deployed backend;
- secrets are not exposed;
- tests and known limitations are documented; and
- the deployment survives normal restarts without losing its only vector index.

---

**Product principle:** LawRAG should prefer a transparent, evidence-backed partial answer—or an explicit abstention—over a confident but unsupported legal conclusion.
