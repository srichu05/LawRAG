# LawRAG Evaluation Plan

**Purpose:** Turn the 50-point judging rubric into a concrete test and evidence plan.  
**Important:** Target scores are goals, not guaranteed results. Report only measured outcomes.

## 1. Rubric mapping

| Judging criterion | Points | Evidence required |
|---|---:|---|
| Problem relevance and clarity | 10 | Named user, concrete research task, corpus justification, concise demo story |
| Retrieval quality | 10 | Relevant passages in top-k, sensible chunking/indexing, hybrid retrieval, query rewriting results |
| Answer grounding | 15 | Every substantive claim supported, valid citations, surprise question and unanswerable question handled correctly |
| Evaluation and failure analysis | 5 | At least five test questions, metrics, two failure cases with root causes and fixes |
| Demo and usability | 5 | Smooth three-minute demo, readable interface, clear loading/error/found-not-found states |
| Creativity and upgrades | 5 | Working hybrid retrieval, query rewriting, found/not-found indicator, useful evidence interface |

## 2. Product scenario

LawRAG helps students and researchers explore a bounded corpus of Indian Supreme Court judgment chunks. It retrieves passages and provides a source-grounded research summary. It is not a substitute for legal counsel and does not claim comprehensive or current coverage of Indian law.

## 3. Test set design

Create a versioned evaluation file, such as `tests/evaluation_questions.jsonl`. Each item should include:
- stable test ID;
- question;
- expected answerability (`answerable`, `unanswerable`, or `ambiguous`);
- expected source/chunk identifiers or a human-reviewed relevance note;
- expected key facts, where appropriate;
- question type;
- reviewer notes.

Include at least:
1. Two direct questions answerable from known passages.
2. One paraphrased version of a supported question.
3. One question that requires exact keyword/legal terminology.
4. One multi-part question with multiple evidence requirements.
5. One question unrelated to the corpus.
6. One question that sounds plausible but is not supported by the retrieved corpus.
7. One question likely to retrieve conflicting or ambiguous passages, if such a case exists in the dataset.

The judge's surprise question must not be copied from the evaluation set. For the live demo, prepare a question that can be checked against the corpus but keep the ability to answer a genuinely unseen question.

## 4. Retrieval metrics

Measure:
- **Recall@k:** proportion of reviewed relevant chunks found within top-k.
- **MRR@k:** rank of the first relevant chunk.
- **Precision@k:** proportion of retrieved chunks reviewed as relevant.
- **Source traceability:** proportion of retrieved results with valid source identifiers.
- **Query rewrite effect:** whether the retry improves recall or relevance compared with the initial query.

Use human-reviewed relevance labels for the small test set. State the number of questions and relevant passages used. Do not report metrics from an unreviewed or empty test set.

## 5. Answer-grounding metrics

Review:
- **Citation validity:** each citation maps to an actual retrieved record.
- **Claim support:** each substantive corpus-specific claim is supported by its cited evidence.
- **Citation coverage:** proportion of substantive claims with appropriate citations.
- **Abstention correctness:** unsupported questions are declined rather than answered speculatively.
- **Conflict handling:** materially different evidence is surfaced instead of concealed.
- **No fabricated metadata:** no invented case names, formal citations, dates, page numbers, or URLs.

A syntactically valid citation is not necessarily a supporting citation. Review semantic support as well as ID validity.

## 6. Required failure analysis

Document at least two real failures after running tests. For each:
1. Show the input question.
2. Show the retrieved passages or explain that none were relevant.
3. Identify the root cause (e.g., vocabulary mismatch, poor chunk boundary, missing metadata, weak embedding match, insufficient corpus coverage, or unsupported generation).
4. Apply a targeted fix.
5. Re-run the same test.
6. Report before/after results honestly.

Do not manufacture failures or claim an improvement that was not measured. If a failure cannot be fixed in the available time, document the limitation and mitigation.

## 7. Acceptance gates

### Phase 1: ingestion and retrieval
- Dataset revision, schema, counts, and license findings recorded.
- Indexing is repeatable and does not silently duplicate records.
- Every returned chunk has traceable source metadata where the source provides it.
- Retrieval test set runs and results are recorded.
- Dense retrieval works; BM25/hybrid retrieval and query rewriting are implemented and evaluated before declaring retrieval-quality work complete.

### Phase 2: agentic RAG
- LangGraph has explicit states and conditional edges.
- Retry count is bounded.
- Answerable question returns supported evidence.
- Unsupported question returns an explicit insufficient-evidence response.
- Citations map to retrieved records and support their associated claims.
- Conflict and provider-error paths are tested.

### Phase 3: UI and deployment
- Health and query endpoints pass smoke tests.
- Deployed UI can submit a question and display the answer and sources.
- Loading, failure, empty-evidence, and found/not-found states are clear.
- The app survives normal redeploy/restart without silently losing its only vector index.
- Three-minute demo is rehearsed and timed.

## 8. Live surprise-question protocol

During the demo:
1. Ask a question that is not in the test set.
2. Observe whether retrieval returns relevant evidence.
3. Open and inspect the source.
4. Check whether the answer accurately represents the passage.
5. If the corpus does not support the question, verify that the system abstains.
6. Include the result in grounding evaluation.

Do not select a surprise question solely because it is easy. A robust system should handle both supported and unsupported unseen questions.

## 9. Results template

Record actual results in a table:

| Test ID | Answerability | Relevant result in top-k? | Citation valid? | Claim supported? | Abstention correct? | Notes |
|---|---|---|---|---|---|---|

Summary:
- Test-set version:
- Dataset revision:
- Embedding model:
- Retrieval configuration:
- Number of questions run:
- Recall@k / MRR@k (if relevance labels support calculation):
- Citation validity:
- Unsupported-question abstention:
- Two failure analyses:
- Known limitations:

Only populate scores after running the tests and reviewing evidence.
