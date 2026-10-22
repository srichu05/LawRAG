# LawRAG — Phase 1: Dataset Ingestion and Retrieval Foundation

**LawRAG** is an agentic Retrieval-Augmented Generation (RAG) system for Indian Supreme Court legal research. This README covers **Phase 1** — the complete data and retrieval foundation.

> **Disclaimer:** LawRAG is an informational research aid only. It is not a lawyer, does not provide binding legal advice, and does not claim comprehensive or current coverage of Indian law.

---

## Dataset Facts (Verified)

| Property | Value |
|---|---|
| Repository | `dedol-hf/india-case-legal-rag` |
| Revision (SHA) | `cdfb7afa492729eeb4ed39e42b5442ad4748ec71` |
| License | MIT (permissive — unrestricted use, modification, distribution) |
| Format | Parquet + JSONL |
| Split | `train` only |
| Record count | **9,375** records |
| Schema fields | `id` (int64), `text` (large_string), `metadata.chunk_index`, `metadata.source`, `metadata.total_pages` |
| Dataset size | ~4.5 MB uncompressed, ~2.4 MB compressed |
| Content | Pre-chunked Indian Supreme Court judgments |

---

## Project Structure

```
lawrag-backend/
├── app/
│   ├── config.py              # All settings from environment variables
│   ├── agent/                 # Phase 2 LangGraph Agentic RAG
│   │   ├── state.py           # TypedDict graph state (question, citations, etc.)
│   │   ├── llm.py             # LLM provider integration (Mock, Groq, OpenAI, HF)
│   │   ├── nodes.py           # 8 inspectable workflow nodes
│   │   └── graph.py           # StateGraph orchestration & conditional routing
│   ├── ingestion/
│   │   ├── download.py        # HuggingFace dataset download
│   │   ├── validate.py        # Schema inspection and data validation
│   │   └── normalize.py       # Record normalization + provenance
│   └── retrieval/
│       ├── embeddings.py      # HuggingFace Inference API + mock
│       ├── chroma_store.py    # ChromaDB indexing + dense retrieval
│       ├── bm25.py            # BM25 lexical retrieval
│       ├── hybrid.py          # Hybrid RRF fusion
│       └── query_rewriter.py  # Bounded query rewriting
├── scripts/
│   ├── query_lawrag.py        # Phase 2 Agentic RAG CLI research tool
│   ├── inspect_dataset.py     # Inspect HF dataset metadata
│   ├── ingest_dataset.py      # Download + validate + normalize
│   ├── build_index.py         # Build ChromaDB + BM25 indexes
│   ├── query_index.py         # Query CLI (dense/BM25/hybrid)
│   └── evaluate_retrieval.py  # Retrieval evaluation suite
├── tests/
│   ├── conftest.py
│   ├── evaluation_questions.jsonl  # 10-question eval set with ground truth labels
│   ├── test_agent.py          # Phase 2 LangGraph workflow tests (22 tests)
│   ├── test_download.py       # Dataset acquisition & fallback tests
│   ├── test_normalization.py  # Normalization & schema preservation tests
│   ├── test_validation.py     # Schema validation & error reporting tests
│   ├── test_embeddings.py     # Embedding provider & cache tests
│   ├── test_bm25.py           # BM25 lexical retrieval tests
│   ├── test_hybrid.py         # Reciprocal Rank Fusion & comparison tests
│   ├── test_chroma_store.py   # Vector store & integration tests
│   └── test_retrieval.py      # Query rewriting tests
├── data/                      # Generated; excluded from git
├── reports/                   # Generated reports; excluded from git
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Quick Setup

### 1. Install dependencies
```bash
cd lawrag-backend
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env — at minimum, set EMBEDDING_API_KEY to a HuggingFace token
# Get your token at: https://huggingface.co/settings/tokens
```

### 3. Inspect the dataset (no credentials needed)
```bash
python scripts/inspect_dataset.py
```

### 4. Download and ingest the dataset
```bash
python scripts/ingest_dataset.py
```
Produces:
- `data/raw_dataset.jsonl` — raw download
- `data/normalized_records.jsonl` — normalized internal schema
- `reports/download_report.json`
- `reports/validation_report.json`
- `reports/normalization_report.json`

### 5. Build the indexes
```bash
# With real HuggingFace embedding API key (set in .env):
python scripts/build_index.py

# Offline testing with mock embedder:
python scripts/build_index.py --provider mock
```
Produces:
- `data/chroma/` — ChromaDB persistent collection
- `data/bm25_index.pkl` — BM25 lexical index
- `reports/indexing_report.json`

### 6. Query the indexes

```bash
# Hybrid retrieval (recommended):
python scripts/query_index.py "What are the principles of natural justice?"

# Dense semantic only:
python scripts/query_index.py --method dense "right to life article 21"

# BM25 lexical only (great for legal terms):
python scripts/query_index.py --method bm25 "section 302 IPC bail"

# Compare all three methods:
python scripts/query_index.py --method compare "breach of contract"

# With query rewriting:
python scripts/query_index.py --rewrite "What happens when contracts are violated?"

# JSON output:
python scripts/query_index.py --json "fundamental rights" | python -m json.tool

# Interactive mode:
python scripts/query_index.py --interactive
```

### 7. Run the evaluation suite
```bash
# All methods (requires indexes to be built):
python scripts/evaluate_retrieval.py

# With mock embedder:
python scripts/evaluate_retrieval.py --provider mock
```
Produces: `reports/evaluation_report.json`

---

## Running Tests

```bash
# All offline unit tests (no credentials needed):
python -m pytest tests/ -v -m "not integration"

# Including integration tests (requires chromadb + no real API):
python -m pytest tests/ -v

# With coverage:
python -m pytest tests/ -v --cov=app --cov-report=term-missing -m "not integration"

# Specific test file:
python -m pytest tests/test_bm25.py -v
python -m pytest tests/test_hybrid.py -v
```

### Test categories
| Marker | Description |
|---|---|
| (default) | Offline unit tests — no network, no credentials |
| `integration` | Require chromadb installed; use mock embedder |

---

## Embedding Configuration

### Model verified
- **Provider:** HuggingFace Inference API
- **Model:** `sentence-transformers/all-MiniLM-L6-v2`
- **Dimension:** 384
- **Input limit:** 512 tokens
- **API support:** Feature-extraction confirmed ✓

### Without API key
Set `EMBEDDING_PROVIDER=mock` in `.env` to use the deterministic mock embedder for index building and retrieval testing (offline, no API needed).

---

## Retrieval Architecture

### Dense retrieval
- Query is embedded at retrieval time using the same model as document indexing
- ChromaDB cosine distance search returns top-k candidates
- Results include distance, source file, chunk index, and total pages

### BM25 lexical retrieval
- Important for exact legal terminology, case names, statute references
- Tokenizer: lowercase + whitespace/punctuation split, min token length 2
- Index persisted as pickle for fast loading
- Returns ranked results with BM25 scores

### Hybrid (Reciprocal Rank Fusion)
- Runs both dense and BM25 retrievers
- Fuses using RRF: `score(d) = Σ 1/(k + rank_r(d))` where k=60 (configurable)
- Deduplicates by chunk_id
- Records provenance: which retriever found each result
- Configurable k parameter via `RRF_K` environment variable

### Query rewriting
- Generates up to 2 alternative queries
- **Offline mode:** Synonym expansion for common legal terms
- **LLM mode:** Configurable OpenAI or HuggingFace text generation
- Never introduces facts not in the original query
- Merges and deduplicates results from all queries

---

## Evaluation Questions

| ID | Question | Type | Answerability |
|---|---|---|---|
| Q01 | Principles of natural justice? | Direct | Answerable |
| Q02 | Bail in murder cases (section 302 IPC)? | Exact term | Answerable |
| Q03 | Fundamental rights violations under Article 21? | Paraphrased | Answerable |
| Q04 | right to life personal liberty protection | Keyword/exact | Answerable |
| Q05 | Breach of contract and remedies? | Multi-part | Answerable |
| Q06 | Writ petition filing procedure? | Ambiguous | Ambiguous |
| Q07 | Women's property rights after marriage? | Direct | Answerable |
| Q08 | Cryptocurrency tax rates in India? | Out of corpus | Unanswerable |
| Q09 | Cricket match fixing penalties (IPL)? | Out of corpus | Unanswerable |
| Q10 | Culpable homicide amounting to murder? | Synonym test | Answerable |

> **Note:** `relevant_chunk_ids` are to be populated manually after indexing and inspecting results.

---

## Security and Provenance

- All API keys are stored in `.env` only — never in source code
- Retrieved chunks are treated as untrusted input
- Source metadata preserved without fabrication
- Missing metadata is recorded as `None`, not invented
- Every retrieved result is traceable to `source_file` and `source_id`
- Duplicate chunk IDs are reported, not silently overwritten
- ChromaDB dimension/model mismatch detected and reported

---

## Known Limitations (Phase 1)

1. **Corpus boundary:** The dataset contains a bounded set of judgments. Many legal questions may not be answerable from this corpus — this is expected.
2. **HuggingFace rate limits:** Anonymous inference API requests are heavily rate-limited. A HuggingFace token is strongly recommended.
3. **Relevance labels:** The evaluation set currently uses empty `relevant_chunk_ids`. These must be manually reviewed and filled after indexing to compute Recall@k, MRR@k, and Precision@k accurately.
4. **ChromaDB locality:** The local ChromaDB path is not persistent on cloud hosting (e.g., Render free tier). Phase 3 will configure Chroma Cloud.
5. **Query rewriting (offline mode):** The offline synonym expansion covers common legal terms but is not comprehensive. LLM-based rewriting is significantly better but requires an API key.

---

## Phase 2 — Agentic RAG Workflow (LangGraph)

Phase 2 implements the autonomous, bounded legal research workflow orchestrating retrieval, evidence assessment, query rewriting, grounded generation, citation validation, and honest abstention.

### Graph Architecture

```
[analyze_query]
       │
       ▼
[retrieve_evidence] ◄────┐
       │                 │
       ▼                 │
[assess_evidence]        │
       │                 │
       ├─ (weak & retries < 1) ──► [rewrite_query]
       │
       ├─ (sufficient) ────────► [generate_answer] ──► [validate_citations] ──┐
       │                                                                      │
       └─ (insufficient / retry exhausted) ──► [abstain] ─────────────────────┴─► [finalize] ──► END
```

### The 8 Workflow Nodes

1. **`analyze_query`**: Normalizes question whitespace, initializes state, and validates query presence.
2. **`retrieve_evidence`**: Executes the Phase 1 hybrid retrieval pipeline (`retrieve_hybrid`) combining BM25 and dense embeddings with Reciprocal Rank Fusion. Merges and deduplicates across retries.
3. **`assess_evidence`**: Conservative evidence assessment checking topic keyword coverage, relevance RRF score, source metadata completeness, and conflicting judicial authority (e.g. dissent, overruling).
4. **`rewrite_query`**: Bounded query rewriting using `QueryRewriter`. Generates legal synonym expansions without hallucinating new facts. Strictly bounded to at most ONE retry (`retry_count < 1`).
5. **`generate_answer`**: Generates a concise explanation strictly grounded in the retrieved Supreme Court passages. Enforces prompt injection safety by treating judgment text as untrusted context.
6. **`validate_citations`**: Verifies that every returned citation references a real retrieved chunk (`chunk_id`, `source_file`, `chunk_index`, `total_pages`, excerpt). Never invents metadata.
7. **`abstain`**: Returns an explicit, honest abstention statement when the corpus lacks evidence. Sets citations to `[]` and discloses corpus limitations.
8. **`finalize`**: Compiles the final structured result with audit metadata, search queries used, and legal disclaimers.

### Running Phase 2 Research CLI

```bash
# 1. Ask a supported legal question
python scripts/query_lawrag.py "What are the principles of natural justice in Indian Supreme Court judgments?"

# 2. Ask an unsupported / out-of-corpus question (demonstrating honest abstention)
python scripts/query_lawrag.py "What are the current tax rates for cryptocurrency trading in India?"

# 3. Output structured JSON (suitable for API/frontend integration)
python scripts/query_lawrag.py "What does the Supreme Court say about breach of contract?" --json

# 4. Interactive research loop
python scripts/query_lawrag.py -i
```

### Running All Tests (131 Tests)

```bash
# Run all tests (Phase 1 + Phase 2)
python -m pytest tests -v

# Run Phase 2 LangGraph tests specifically
python -m pytest tests/test_agent.py -v
```

---

## Phase 2 Acceptance Gates — Status

| Gate | Status |
|---|---|
| Explicit LangGraph StateGraph with typed state | ✓ Implemented (`LawRAGState`) |
| 8 inspectable workflow nodes | ✓ Implemented & Verified |
| Conditional transitions (sufficient / weak / insufficient) | ✓ Verified |
| Bounded retries (at most 1 retry; loop prevention) | ✓ Verified |
| Supported questions receive grounded answers | ✓ Verified (tested with natural justice, breach of contract) |
| Unsupported questions trigger honest abstention | ✓ Verified (tested with cryptocurrency, IPL cricket) |
| Citations resolve strictly to real retrieved chunks | ✓ Verified (100% chunk_id and source_file traceability) |
| Missing metadata disclosures | ✓ Implemented (warnings added) |
| Conflicting evidence detection | ✓ Implemented (flags dissent & overruling) |
| Provider failure handling | ✓ Verified (graceful error handling, no crashes) |
| Full test suite passes | ✓ 131 passing tests (0 failures, 0 skipped) |
| No credentials committed | ✓ All secrets in .env |

---

---

## Phase 3 — FastAPI Backend & Frontend Integration

Phase 3 exposes the Agentic RAG workflow over a high-performance FastAPI server integrated with the React/Vite frontend (`lawrag-frontend`).

### API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` or `/api/v1/health` | `GET` | Operational health check (returns LLM provider, BM25 index readiness, and chunk count). |
| `/api/v1/research` or `/api/query` | `POST` | Executes full Agentic RAG pipeline. Accepts `{"query": "...", "category": "..."}` and returns grounded answer, citations, statutes, and audit traces. |
| `/docs` | `GET` | Interactive Swagger UI API documentation. |

### Running the Full System Locally

```bash
# Terminal 1: Start FastAPI Backend (Port 8000)
cd lawrag-backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2: Start React Frontend (Port 5173)
cd lawrag-frontend
npm run dev -- --port 5173
```

Open `http://localhost:5173` in your browser. The top status bar will show a green dot with `Backend: FastAPI Backend Live`.


