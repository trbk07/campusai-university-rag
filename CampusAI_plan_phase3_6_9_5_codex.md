# CampusAI — Phase 3→6 Hardening Plan (9.5/10 Gate)
> Codex-optimized execution spec.  
> Repo: `trbk07/campusai-university-rag`  
> Audit baseline: `main@cacb451f3018a739cf92ee1ba1855392d5456e1b`  
> Goal: Phase 3, 4, 5, 6 each independently reach **>= 9.5/10** before Phase 7 work starts.

---

## 0. How to use this file

This file is the **source of truth for Phase 3→6 hardening**. It is intentionally structured for low-context coding agents.

Rules:

1. Do **not** read the whole repository.
2. Do **not** read all of this file when executing one task.
3. Select exactly one task ID (`P3-A`, `P4-C`, etc.).
4. Read only that task's `READ SET`.
5. Modify only the `CHANGE SET` unless a dependency forces a small adjacent change.
6. Run the task's `TEST SET`.
7. Do not mark a task complete unless its `EXIT GATE` passes.
8. After every task, update only its checkbox/status and append one short evidence line.
9. Never tune using test/holdout. Dev/calibration only.
10. Never hand-edit a report to change FAIL→PASS. Reports are generated artifacts.

### Agent response contract

For each Codex task, return only:

```text
TASK: <id>
CHANGED:
- <file>: <what changed>

TESTS:
- <command>: PASS/FAIL

METRICS:
- <only metrics affected by this task>

OPEN:
- <remaining blocker, or NONE>
```

No repo-wide summary unless explicitly requested.

---

# 1. Current audited baseline

## Phase 3 — Dense retrieval
Current strengths:
- `DenseIndex` has checksum, schema, corpus/model mismatch checks.
- Restart/corruption persistence tests exist.
- SentenceTransformer runtime is lazy and process-wide.
- Multilingual model evidence exists.

Current blockers to 9.5:
- Dense vectors are persisted as JSON `list[list[float]]`.
- Dense search is Python-loop `O(N×D)`, not vectorized.
- Runtime model cache key omits model revision.
- `model_revision="1"` is not a pinned upstream model revision/commit.
- Older canonical Phase 3 acceptance uses only 2 docs / 5 chunks and remains `conditional`.
- Corpus publication can expose partial BM25/dense state during interrupted rebuild.

## Phase 4 — Basic RAG
Current strengths:
- Deterministic contract suite exists.
- Context budget, cache, citation resolution, abstention path are tested.
- `basic_rag_report.json`: 30 records, 22 answerable, 8 negative, contract PASS.

Current blockers to 9.5:
- `FixtureLLM` consumes gold answer/evidence; this proves contract correctness, not real model quality.
- Routing semantics are split between `rag/service.py` and `retrieval/routing.py`.
- Production query path contains `Topic:`-specific normalization.
- Timing in Basic RAG report is not cleanly separated by route/retrieval/context/LLM/validation.

## Phase 5 — Grounding / citation / abstention
Current strengths:
- `EvidenceRegistry`, strict schema, claim alignment, numeric/code/year/polarity checks.
- >=50 adversarial test cases.
- Strong frozen thresholds already defined in `configs/phase5_release.json`.
- Release package validator exists.

Current blockers to 9.5:
- `evaluation/results/grounding_release_report.json` is empty.
- Human annotation signoff is not independently completed.
- LLM still supplies citation metadata that the system then validates; provenance should be system-owned.
- Quote support should be deterministic/extractive where possible.
- Claim alignment logic is becoming too monolithic.

## Phase 6 — Hybrid / RRF
Current strengths:
- 400 records / 13 documents.
- Dev/test/holdout separation; no split leakage.
- BGE-M3 real model.
- Test answerable Recall@5 ≈ 0.9829.
- Holdout answerable Recall@5 ≈ 0.9573.
- Negative FPR = 0 for primary auto route.
- Provenance loss/filter leakage = 0.
- Paired bootstrap CI shows hybrid > BM25/dense.
- Warm p95 ≈ 247.8 ms in performance report.

Current blockers to 9.5:
- Benchmark questions are partly keyword/template-like; natural user-query validity is under-proven.
- `hybrid.py` hardcodes future year rule (`>2030`).
- Runtime parses internal-ish source hints from query text.
- Auto router uses crude `len(tokens) <= 3 → BM25`.
- Acceptance confidence uses hardcoded `.55 lexical + .35 dense + .10 agreement`.
- Filtered/page-constrained search may expand to all items.
- Query cache key should include index/calibration generation.
- `phase6_grounding_regression.json` is empty.
- Peak RSS is ~2.16 GB; free-tier headroom is narrow.

---

# 2. Global 9.5 release rules

A phase is **not 9.5** unless all apply:

- Code correctness: no known P0/P1 bug in phase path.
- Reproducibility: clean commit + dependency lock + config/model/corpus/benchmark hashes.
- Data integrity: dev/test/holdout rules documented and enforced.
- Evaluation: generated from runtime; no hand-edited pass flags.
- Failure analysis: failed queries are exported and categorized.
- Regression: prior phase metrics do not regress outside declared tolerance.
- Security/provenance: fail-closed where evidence/index identity is uncertain.
- Docs: exact commands to regenerate evidence.
- Tests: focused suite + full suite pass.
- Release manifest points to the code/evidence actually being claimed.

Do **not** start Phase 7 until P3, P4, P5, P6 final gates all pass.

---

# 3. Execution order

```text
P3-A → P3-B → P3-C → P3-D → P3-E
  ↓
P4-A → P4-B → P4-C → P4-D
  ↓
P5-A → P5-B → P5-C → P5-D → P5-E
  ↓
P6-A → P6-B → P6-C → P6-D → P6-E
  ↓
FINAL-RECERTIFY
```

Why this order:
- P3 changes index identity/storage used downstream.
- P4 unifies query planning before P6 cleanup.
- P5 makes grounding provenance system-owned.
- P6 then optimizes retrieval/routing against the final contracts.

---

# 4. Phase 3 — Embedding & vector search → 9.5

## P3-A — Pin model identity end-to-end
**Priority:** P0  
**Status:** [ ]

### READ SET
```text
src/campusai/retrieval/model_runtime.py
src/campusai/retrieval/dense_index.py
tests/test_retrieval_persistence.py
configs/default.yaml
```

### CHANGE SET
- Add immutable encoder identity:
  - `model_name`
  - `model_revision` = real pinned revision/commit when configured
  - `device`
  - `dtype`
  - `backend`
  - `normalize_embeddings`
  - optional query/document prompt identity
- Extend `RuntimeKey` to include revision + dtype/backend.
- `get_encoder()` must load the requested revision, not only model name.
- Dense manifest must persist the complete embedding recipe.
- Loading an index with a different active recipe must fail closed.

### TEST SET
```text
pytest -q tests/test_retrieval_persistence.py
pytest -q tests/test_retrieval.py tests/test_retrieval_benchmark.py
```

Add tests:
- same name + different revision => different runtime entries;
- index revision A + runtime revision B => reject;
- dimension/normalization mismatch => reject;
- manifest round-trip preserves recipe.

### EXIT GATE
```text
✓ runtime cache cannot alias different model revisions
✓ exact model recipe is persisted
✓ mismatch fails closed
✓ focused tests pass
```

---

## P3-B — Replace JSON vectors with ndarray storage
**Priority:** P0  
**Status:** [ ]

### READ SET
```text
src/campusai/retrieval/dense_index.py
src/campusai/retrieval/index_builder.py
tests/test_retrieval_persistence.py
evaluation/run_retrieval_eval.py
```

### TARGET FORMAT
```text
<doc_id>/
  dense_manifest.json
  dense_items.jsonl
  dense_vectors.npy
```

Use:
```text
float32
shape = (n_chunks, dimension)
normalized rows
scores = matrix @ query_vector
```

Do not add FAISS yet unless matrix benchmark proves necessary.

### CHANGE SET
- Store vectors as contiguous `numpy.float32`.
- Vectorize cosine search using normalized inner product.
- Keep deterministic tie-break on `chunk_id`.
- Validate:
  - shape;
  - dtype;
  - item count;
  - dimension;
  - checksum;
  - corpus fingerprint.
- Backward compatibility:
  - either one explicit migration tool;
  - or fail with actionable `IndexVersionMismatchError`.
  - no silent old/new mixing.

### TEST SET
```text
pytest -q tests/test_retrieval_persistence.py tests/test_retrieval.py
```

Benchmark old vs new on same corpus:
```text
load_ms
search p50/p95/p99
RSS
disk bytes
top-k identity
```

### EXIT GATE
```text
✓ top-k results match reference implementation
✓ no Python vector loop in production dense search
✓ vector file is float32 ndarray
✓ corrupted/truncated vector file fails closed
✓ latency/RAM/disk comparison artifact generated
```

---

## P3-C — Transactional index publication
**Priority:** P0  
**Status:** [ ]

### READ SET
```text
src/campusai/retrieval/index_builder.py
src/campusai/retrieval/dense_index.py
src/campusai/retrieval/bm25_index.py
tests/test_retrieval_persistence.py
```

### CHANGE SET
Build outside the live path:

```text
.tmp/index-build-<uuid>/
  bm25...
  dense...
  manifest...
```

Then:
1. fsync;
2. validate all artifacts;
3. atomically publish snapshot;
4. update corpus manifest last;
5. increment `index_generation`.

Concurrency:
- lock per document/corpus build;
- concurrent same-doc build cannot expose mixed generations.

### TEST SET
Add fault-injection tests:
```text
fail after BM25 write
fail during dense vectors write
fail before manifest publish
two concurrent builders
restart after interrupted build
```

### EXIT GATE
```text
✓ old index remains queryable after failed rebuild
✓ no partial live snapshot
✓ corpus manifest references only complete snapshots
✓ generation is monotonic/auditable
```

---

## P3-D — Strengthen corpus/index fingerprint
**Priority:** P1  
**Status:** [ ]

### READ SET
```text
src/campusai/retrieval/dense_index.py
src/campusai/retrieval/index_builder.py
src/campusai/retrieval/contracts.py
```

### FINGERPRINT MUST COVER
```text
chunk_id
doc_id
content
page/page_range
content_type
table_id
heading_path
source_hash
parser_version
chunker_version
retrieval-relevant metadata
embedding recipe hash
```

### EXIT GATE
Changing any retrieval/provenance-relevant field changes the fingerprint and invalidates stale index/cache.

---

## P3-E — Re-certify dense retrieval on real corpus
**Priority:** P0 gate  
**Status:** [ ]

### READ SET
```text
evaluation/run_retrieval_eval.py
evaluation/run_retrieval_benchmark.py
evaluation/metrics.py
data/benchmark/phase6_retrieval_*.jsonl
```

### DATA
Use the Phase 6 real university corpus, not the old 2-doc/5-chunk acceptance corpus.

Add a small **human-natural dense challenge set**; do not generate by copying gold chunk keywords.

### REPORT
```text
Recall@1/3/5/10
MRR
nDCG@5
p50/p95/p99
cold model load
query encode latency
vector search latency
peak RSS
index bytes/chunk
```

Segments:
```text
vi / en / vi-en
exact_code
fact
table
prerequisite
comparison
multi_document
clean_text / OCR-degraded
```

Also run model Pareto comparison:
```text
BAAI/bge-m3
vs one lighter multilingual candidate
(optional) optimized/quantized candidate
```

### PHASE 3 FINAL GATE
```text
✓ >=8 real documents
✓ real pinned multilingual model
✓ real-corpus Recall@5 >= 0.90
✓ persistence/restart/corruption/concurrency pass
✓ transactional publication
✓ vectorized storage/search
✓ model identity fail-closed
✓ production model chosen by quality/latency/RAM Pareto evidence
✓ release manifest generated on clean commit
```

---

# 5. Phase 4 — Basic RAG → 9.5

## P4-A — Split contract evaluation from provider quality
**Priority:** P0  
**Status:** [ ]

### READ SET
```text
evaluation/run_basic_rag.py
evaluation/results/basic_rag_report.json
tests/test_basic_rag.py
src/campusai/rag/grounding.py
```

### CHANGE SET
Keep `FixtureLLM`, but explicitly call its report:
```text
Phase 4 Contract Acceptance
```

It may prove:
```text
schema
cache
context budget
citation coordinates
abstention path
determinism
```

It must **not** be used to claim real LLM answer quality.

Add:
```text
evaluation/run_basic_rag_provider.py
```

Real provider never receives:
```text
gold_answer
gold_evidence
gold_claims
```

### EXIT GATE
Two independent reports:
```text
basic_rag_contract_report.json
basic_rag_provider_report.json
```

---

## P4-B — Real-provider benchmark
**Priority:** P0  
**Status:** [ ]

### DATA
80–120 reviewed QA minimum:
```text
~50 fact
~15 table/simple lookup
~15 bilingual/mixed
~20 unanswerable/ambiguous
```

Use real corpus.

### METRICS
```text
answer correctness
citation precision/recall
abstention precision/recall
schema-valid rate
fabrication rate
p50/p95 total
```

Manual or deterministic gold review is authoritative; LLM judge may be supplementary only.

### EXIT GATE
```text
answerable correctness >= .90
citation resolution = 1.00
citation precision >= .98
negative abstention >= .95
fabrication rate = 0 on release set
schema invalid = 0
```

---

## P4-C — One query planner, no duplicated routing
**Priority:** P0  
**Status:** [ ]

### READ SET
```text
src/campusai/rag/service.py
src/campusai/retrieval/routing.py
src/campusai/retrieval/hybrid.py
tests/test_basic_rag.py
tests/test_phase6_retrieval.py
```

### CHANGE SET
Create one canonical plan object, e.g.:

```text
QueryPlan
- route
- doc_ids
- filters
- top_k
- rerank
- language
- page_constraints
- year_constraints
```

One `QueryPlanner.plan()` owns routing semantics.

Remove production-specific `Topic:` parsing from `rag/service.py`.
If benchmark adapters need `Topic:`, keep it under `evaluation/`.

### EXIT GATE
```text
✓ RAG service and retriever consume same QueryPlan
✓ no second independent routing policy
✓ no benchmark protocol marker in production query normalization
✓ old routing regression tests adapted and passing
```

---

## P4-D — Cache + tracing completeness
**Priority:** P1  
**Status:** [ ]

### READ SET
```text
src/campusai/rag/cache.py
src/campusai/rag/service.py
src/campusai/observability.py
```

### CACHE KEY MUST INCLUDE
```text
normalized question
language
doc_ids / filters / top_k
query plan hash
corpus fingerprint
index generation
embedding recipe hash
reranker identity
retrieval config hash
calibration hash
LLM model identity
prompt hash
schema/policy versions
context budget
```

### TRACE STAGES
```text
plan_ms
retrieval_ms
context_build_ms
llm_ms
validation_ms
grounding_ms
total_ms
cache_hit
```

### PHASE 4 FINAL GATE
```text
✓ deterministic contract suite PASS
✓ real-provider suite PASS
✓ one query planner
✓ complete cache invalidation fingerprint
✓ stage-level tracing
✓ release manifest generated on clean commit
```

---

# 6. Phase 5 — Citation / grounding / abstention → 9.5

## P5-A — System-owned deterministic citations
**Priority:** P0  
**Status:** [ ]

### READ SET
```text
src/campusai/rag/grounding.py
src/campusai/rag/evidence.py
src/campusai/rag/schemas.py
src/campusai/rag/claims.py
tests/test_grounding.py
tests/test_phase5_adversarial.py
```

### TARGET CONTRACT
LLM returns only semantic references:

```json
{
  "answer": "...",
  "claims": [
    {
      "claim_id": "c1",
      "text": "...",
      "citation_ids": ["chunk-id"]
    }
  ],
  "abstained": false
}
```

LLM does **not** own:
```text
page
page_range
source_name
source_hash
table_id
quote
```

System resolves `citation_ids` through `EvidenceRegistry` and constructs public citations deterministically.

### EXIT GATE
```text
✓ impossible for model to invent page/source metadata
✓ unknown citation ID => fail closed
✓ all public citation metadata is registry-derived
✓ adversarial suite updated and passing
```

---

## P5-B — Extractive support spans
**Priority:** P1  
**Status:** [ ]

### TARGET
For text evidence, derive quote/span from evidence:
```text
start_offset
end_offset
quote
```

For table evidence:
```text
table_id
row_id / row index
column IDs when available
```

Do not trust model-written quote as provenance.

### EXIT GATE
```text
✓ public quote is reproducible from stored evidence
✓ changed source text invalidates stale span
✓ Unicode/whitespace normalization cannot change numeric/code identity
```

---

## P5-C — Refactor claim validation by claim type
**Priority:** P1  
**Status:** [ ]

### READ SET
```text
src/campusai/rag/claims.py
src/campusai/rag/policies.py
src/campusai/rag/decision.py
```

### TARGET TYPES
```text
FACT
NUMERIC
COURSE_RELATION
TEMPORAL
TABLE_VALUE
COMPARISON
```

Split validators, e.g.:
```text
LexicalClaimValidator
NumericClaimValidator
CodeClaimValidator
TemporalClaimValidator
```

Keep orchestration small. Avoid adding domain-specific one-off conditions to one giant `align_claims()`.

### PROPERTY TESTS
Generate mutations:
```text
3 → 4 credits
2025 → 2026
MATH101 → MATH102
must → must not
at least → at most
30% → 20%
semester 1 → semester 2
```

Property:
```text
grounded exact fact + material mutation
=> status cannot remain supported
```

---

## P5-D — Complete independent human review + calibration
**Priority:** P0 gate  
**Status:** [ ]

### READ SET
```text
data/benchmark/grounding_reviewed.jsonl
scripts/annotation_signoff.py
evaluation/calibrate_confidence.py
evaluation/grounding_metrics.py
configs/phase5_release.json
```

### RULES
- Primary review: 100%.
- Independent reviewer/signoff: follow the release validator exactly.
- Creator and independent reviewer identities must not overlap where validator forbids it.
- Resolve disagreements before freeze.
- Freeze benchmark before final test/holdout.
- Fit calibration on dev only.

### REQUIRED OUTPUTS
```text
annotation_signoff.json
calibration_report.json
grounding_release_report.json
```

Calibration:
```text
ECE
Brier
coverage-risk curve
risk@80
risk@90
```

---

## P5-E — Generate real Phase 5 release package
**Priority:** P0 gate  
**Status:** [ ]

### READ SET
```text
evaluation/phase5_package.py
evaluation/validate_release.py
configs/phase5_release.json
docs/grounding_release_gates.md
```

### FROZEN QUALITY GATES
Keep existing strong thresholds:

```text
citation precision       >= .99
citation recall          >= .98
citation completeness    >= .98
citation coord validity  = 1.00

grounded claim precision >= .99
grounded claim recall    >= .95

abstention precision     >= .99
abstention recall        >= .98
reason accuracy          >= .95

holdout ECE              <= .05
holdout Brier            <= .08
risk@80 coverage         <= .01
risk@90 coverage         <= .02

unsupported leakage      = 0
contradicted leakage     = 0
schema invalid rate      = 0
```

Also bootstrap CI for major precision/recall metrics.

### PHASE 5 FINAL GATE
```text
✓ grounding_release_report.json non-empty and generated
✓ independent human signoff valid
✓ all frozen thresholds pass
✓ deterministic system-owned citations
✓ adversarial/property tests pass
✓ release package validator PASS
✓ release manifest generated on clean commit
```

---

# 7. Phase 6 — Hybrid / RRF → 9.5

## P6-A — Add human-natural challenge set
**Priority:** P0  
**Status:** [ ]

### KEEP
The existing 400-query dataset remains the deterministic **regression benchmark**.

### ADD
100–150 human-written queries that are written **without copying gold chunk keywords**.

Coverage:
```text
natural Vietnamese
English
vi-en code-switch
typos / no accents
short but meaningful questions
ambiguous references
exact course code
tables
prerequisites
multi-document
negative/out-of-corpus
```

Examples:
```text
Môn Machine Learning cần học môn gì trước?
CTĐT CNTT năm 2024 có bao nhiêu tín chỉ?
Nếu bị khiển trách trong kỳ thi thì bị trừ bao nhiêu điểm?
prerequisite của AIT3003 là môn nào?
mon nay tien quyet la gi
trường có bắt buộc sinh viên dùng MacBook không?
```

### REPORT SEPARATELY
Never merge generated and human sets into one headline metric.

```text
regression_generated/*
human_natural/*
```

---

## P6-B — Remove brittle query hacks
**Priority:** P0  
**Status:** [ ]

### READ SET
```text
src/campusai/retrieval/routing.py
src/campusai/retrieval/hybrid.py
tests/test_phase6_retrieval.py
```

### REMOVE / REPLACE
1. No hardcoded:
```text
year > 2030 => invalid
```

Use selected corpus metadata, or defer full temporal validity to Phase 9.

2. Do not parse internal source hashes/IDs from ordinary user query as ranking controls.
Use explicit:
```text
doc_ids
filters
QueryPlan constraints
```

3. Remove:
```text
len(tokens) <= 3 => BM25
```

Preferred simple policy:
```text
exact code => exact route
explicit filters => filtered hybrid
otherwise => hybrid
```

If cost-aware routing is retained, tune on dev only and freeze before test/holdout.

### EXIT GATE
```text
✓ no calendar magic constant
✓ no internal-ID control hidden in user text
✓ short natural semantic questions are not forced to BM25 by token count
```

---

## P6-C — Replace hardcoded acceptance score with calibrated confidence model
**Priority:** P0  
**Status:** [ ]

### CURRENT TO REMOVE
```text
0.55 * lexical
+ 0.35 * dense
+ 0.10 * agreement
```

### TARGET
Create explicit `RetrievalConfidenceModel`.

Possible features:
```text
BM25 normalized score/rank
dense cosine/rank
retriever agreement
top1-top2 margin
query length/features
exact-code flag
filter match
```

Use a small interpretable model:
```text
logistic regression
or monotonic calibrator
```

Fit on dev only; serialize:
```text
coefficients/parameters
feature schema
training split hash
threshold
version
```

### EXIT GATE
```text
✓ test/holdout never used to fit
✓ confidence model is versioned
✓ FPR <= .05
✓ answerable recall drop <= .02 vs unthresholded primary retrieval
```

---

## P6-D — Filter/search/cache scaling cleanup
**Priority:** P1  
**Status:** [ ]

### READ SET
```text
src/campusai/retrieval/hybrid.py
src/campusai/retrieval/contracts.py
src/campusai/retrieval/index_builder.py
```

### CHANGE SET
Metadata postings/index:
```text
program -> chunk indices
year -> chunk indices
document -> chunk indices
page -> chunk indices
```

Filter first, then rank eligible subset.

Dense:
```text
matrix[eligible_indices] @ query
```

Query cache key must include:
```text
index_generation
corpus fingerprint
calibration/confidence-model version
query-plan hash
```

Any document load/remove/rebuild invalidates affected cache entries.

### EXIT GATE
```text
✓ no full-corpus expansion solely because page/filter is present when subset index exists
✓ zero filter leakage
✓ stale generation cannot hit query cache
```

---

## P6-E — Final retrieval quality/resource evidence
**Priority:** P0 gate  
**Status:** [ ]

### REQUIRED REPORTS
For both regression and human-natural sets:
```text
Recall@1/3/5/10
MRR
nDCG@5/10
negative FPR
abstention precision/recall
routing accuracy
provenance loss
filter leakage
p50/p95/p99
```

Segments:
```text
answerable-hard
vi
en
vi-en
typo/no-accent
exact-code
table
prerequisite
multi-document
negative
OCR-degraded
```

Export:
```text
evaluation/results/phase6_failure_cases.json
```

Each failure:
```text
qid
query
expected evidence
returned IDs
route
bm25 rank
dense rank
fusion rank
acceptance score
threshold
root-cause category
```

### RESOURCE TARGET
Preferred:
```text
warm p95 <= 300 ms
concurrency=20 p99 <= 1000 ms
error rate = 0
timeout rate = 0
RAM headroom >= 25% on deployment target
```

If BGE-M3 cannot satisfy deployment RAM, document a two-profile architecture instead of hiding the limitation:
```text
quality/offline profile
light/free-web profile
```

### PHASE 6 FINAL GATE
```text
✓ generated regression benchmark PASS
✓ human-natural challenge benchmark PASS
✓ human answerable Recall@5 >= .92
✓ hard-answerable Recall@5 >= .88
✓ exact-code Recall@5 >= .99
✓ negative FPR <= .05
✓ provenance loss = 0
✓ filter leakage = 0
✓ hybrid > BM25 and dense with positive paired bootstrap CI
✓ no brittle year/source/token-count hacks
✓ calibrated acceptance model
✓ performance budget documented/passed
✓ phase6_grounding_regression.json non-empty and PASS
✓ release manifest generated on final clean commit
```

---

# 8. Cross-phase shared refactor

Do this only after the phase-local tasks above unless a task needs it.

## Evaluation shared primitives

Target:
```text
evaluation/
  datasets.py
  fingerprint.py
  manifests.py
  release.py
  metrics/
```

Common manifest fields:
```text
commit
dirty
python
platform
dependency lock hash

corpus hash
benchmark hash
config hash
model identity
prompt hash
policy hash
calibration hash

generated_at
```

Do not create a framework for its own sake. Extract only code duplicated by >=2 phase release pipelines.

---

# 9. FINAL-RECERTIFY

**Status:** [ ]

Run on a clean working tree after all P3→P6 code is frozen.

Order:

```text
1. full pytest
2. compile/import checks
3. secret/security scan
4. Phase 3 dense benchmark + persistence
5. Phase 4 contract benchmark
6. Phase 4 real-provider benchmark
7. Phase 5 grounding benchmark + calibration + package validation
8. Phase 6 regression retrieval benchmark
9. Phase 6 human-natural challenge benchmark
10. Phase 6 grounding regression
11. performance/concurrency run
12. generate manifests last
```

Final evidence rules:
- Reports must reference final code/config/model/data hashes.
- If any code/config changes after report generation, regenerate affected reports.
- Release manifests are generated last.
- Keep failed RC artifacts; do not overwrite history.
- Do not claim 9.5 if independent annotation/provider evidence is missing.

---

# 10. Codex Context Contract — minimize token use

## 10.1 Never start with full-repo reading

Bad:
```text
Read the whole repo and improve Phase 3.
```

Good:
```text
Implement task P3-A from this plan.
Read only the P3-A READ SET first.
Use rg only if a symbol dependency is unresolved.
Do not inspect unrelated phases.
```

## 10.2 Search before opening files

Preferred flow:

```bash
rg -n "RuntimeKey|get_encoder|model_revision" src tests
```

Then open only matching ranges/files.

Do not dump:
```text
entire src/
entire tests/
entire plan.md
large JSON reports
```

For JSON reports, inspect keys/summary with a script/jq instead of loading thousands of row records.

## 10.3 Read implementation before tests, tests before docs

Default order:
```text
1. exact implementation file
2. directly coupled contract/schema
3. focused tests
4. relevant config
5. only then docs/report
```

Exception: release/evaluation tasks may read config/report schema first.

## 10.4 One task = one context window

Do not ask Codex to implement P3-A…P6-E in one prompt.

Ideal unit:
```text
1 task
2–5 implementation files
1–3 focused test files
1 acceptance command
```

## 10.5 No speculative refactor

Codex must not:
- rename public APIs unless task requires it;
- introduce LangChain/LlamaIndex/Haystack;
- add FAISS before benchmark justifies it;
- modify Phase 1/2 behavior;
- modify benchmark labels/gold data to make metrics pass;
- tune on test/holdout;
- lower frozen thresholds after seeing failures;
- delete rejected RC evidence.

## 10.6 Diff-first continuation

On follow-up turns:

```bash
git diff --stat
git diff -- <files from current task>
```

Read the diff, not full files again, unless necessary.

## 10.7 Evidence compression

When reporting results to the user/Codex:
- return metric summary only;
- write detailed rows to JSON artifact;
- list top 5 failure categories, not all failures;
- cite artifact path.

## 10.8 Stop condition

Codex stops after:
```text
code change
focused tests
task gate evidence
```

It does not automatically start the next task.

---

# 11. Minimal task prompt template

Use this exact shape:

```text
Repo: campusai-university-rag
Task: <TASK_ID> from CampusAI Phase 3–6 Hardening Plan.

Rules:
- Read only this task's READ SET first.
- Use rg for unresolved dependencies; do not scan the whole repo.
- Modify only CHANGE SET / minimal adjacent dependencies.
- Preserve public behavior unless task explicitly changes it.
- Do not tune on test/holdout.
- Do not edit generated reports by hand.
- Run the task TEST SET.
- Stop after this task.

Return:
TASK
CHANGED
TESTS
METRICS
OPEN
```

---

# 12. Score rubric after implementation

| Phase | 9.5 requirement |
|---|---|
| Phase 3 | production-grade index identity/storage/publication + real-corpus dense evidence |
| Phase 4 | deterministic contract proof + independent real-provider quality proof |
| Phase 5 | system-owned provenance + human-reviewed grounding/calibration release |
| Phase 6 | statistically strong hybrid retrieval + natural-query validity + resource-safe deployment path |

A phase below any mandatory gate remains `<9.5`, regardless of how many features are implemented.
