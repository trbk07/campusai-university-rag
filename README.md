# CampusAI

CampusAI is an evidence-grounded university knowledge assistant. It ingests
text-based PDFs such as regulations, curricula, syllabi, student handbooks and
course catalogs, then retrieves page-level evidence for grounded answers with
citations and abstention.

The product domain is university information: academic regulations, curricula,
syllabi, student handbooks and course catalogs. Generated artifacts and
machine-specific reports are excluded from version control.

## Current state

- Package: `campusai`
- Distribution: `campusai-evidence-rag`
- Task 1 LLM foundation: implemented and acceptance-tested
- Task 2 PDF ingestion/retrieval foundation: implemented and acceptance-tested
- Production parser: PyMuPDF fast path with SHA-256 cache
- Retrieval: BM25 + dense + RRF; explicit `hybrid_rerank` for hard queries
- Basic RAG: bilingual grounded prompts, provenance-safe context budgets,
  versioned query-answer cache and deterministic abstention acceptance
- Academic metadata: language, document type, academic years and semesters
- Web UI/public deployment: next phase; the repository is currently the backend foundation

The detailed product plan, reuse decisions and deployment roadmap are in
[`plan.md`](plan.md).

## What is reused from the old Tasks

Task 1 is retained as the application reliability layer:

- Gemini and OpenAI-compatible clients;
- SQLite response cache and process-local single-flight protection;
- rate limiting, bounded retry/backoff and `Retry-After` handling;
- JSON parsing/schema validation;
- environment-only secret loading and provider factory.

Task 2 is retained as the document and retrieval layer:

- PDF validation, page provenance, tables, metadata and structure-aware chunks;
- document registry, SHA-256 deduplication and background jobs;
- BM25, dense fallback, hybrid RRF, query cache and optional reranking;
- evaluation scripts and measured performance artifacts.

The product domain is represented consistently in metadata, benchmarks and
retrieval examples: all production-facing examples target university documents.

## Local setup

```powershell
uv sync --extra dev
uv run pytest -q
```

Without `uv`:

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts\secret_scan.py
```

Optional model/feasibility dependencies are deliberately separate:

```powershell
uv sync --extra feasibility
```

Do not commit `.env`, API keys, source PDFs, model files, generated indexes or
cache databases.

## Task 1: LLM foundation

The provider-neutral client is under [`src/campusai/llm`](src/campusai/llm).
It supports `complete`, `generate` and validated `generate_json` for Gemini and
OpenAI-compatible endpoints. Identical prompts are cached; concurrent misses
are single-flight. Transient HTTP/network failures are retried with bounded
backoff, while credentials are kept out of URLs, cache keys, logs and errors.

Run the offline acceptance suite:

```powershell
.venv\Scripts\python.exe -m pytest -q tests\test_llm.py tests\test_llm_acceptance.py
.venv\Scripts\python.exe -m pytest -q --basetemp=D:\Project\.tmp\pytest-t1 -p no:cacheprovider --cov=campusai.llm --cov-fail-under=90
```

The live Gemini contract test is opt-in only:

```powershell
$env:RUN_LLM_INTEGRATION = "1"
$env:GEMINI_API_KEY = "<new key supplied only in the environment>"
.venv\Scripts\python.exe -m pytest -q tests\integration\test_gemini.py
```

See [`docs/t1_acceptance.md`](docs/t1_acceptance.md) for the exact acceptance
scope and security limitations. Current Task 1 evidence is 33 focused tests,
71 full-repository tests, and 95.01% LLM coverage. The cache is not encrypted
at rest.

## Task 2: ingestion and retrieval

The default ingestion path is intentionally lightweight:

1. validate size/page count and detect scan-only PDFs;
2. extract pages with PyMuPDF;
3. detect academic metadata;
4. extract tables and preserve raw values;
5. create page/heading/table chunks with provenance;
6. persist the document by SHA-256 and build indexes separately.

Docling is available as a layout/table review option. It is not the default
web parser because cold model loading and CPU layout processing are too slow
for interactive requests. Scan-only PDFs can use the explicit, bounded
RapidOCR ONNX worker; without `enable_ocr=True` they stop with a clear
`review_required/ocr_required` status.

Build an index for an ingested document:

```powershell
.venv\Scripts\python.exe scripts\build_index.py --help
.venv\Scripts\python.exe scripts\warm_retrieval.py --help
```

Use `mode=hybrid` for the normal fast path. Use `mode=hybrid_rerank` only for
hard questions when a reranker is configured and memory is available.

Validate the university seed benchmark:

```powershell
.venv\Scripts\python.exe scripts\validate_benchmark.py data\benchmark\dev.jsonl
```

The benchmark is currently a 20-question seed. Phase 8 in `plan.md` expands it
to 100–300 reviewed questions with temporal, multi-hop, unanswerable and
citation metrics.

Phase 1/2 acceptance evidence is regenerated in
[`evaluation/phase12_acceptance.json`](evaluation/phase12_acceptance.json).
The release scope, hashes, commands, OCR policy, and known limitations are in
[`docs/phase12_release.md`](docs/phase12_release.md).

## Phase 4: Basic RAG

Phase 4 provides the retrieval-to-grounded-answer flow. Context blocks retain
document/page provenance, budgets are enforced with a conservative token
estimate, and Vietnamese/English prompts require evidence-only JSON answers.
Repeated questions are cached by a SHA-256 key containing corpus/index version,
filters, retrieval mode, prompt/model version and context budget; API keys are
never part of the key or cached answer metadata.

Run the offline Phase 4 acceptance benchmark and focused tests:

```powershell
.venv\Scripts\python.exe evaluation\run_phase4_basic_rag.py
.venv\Scripts\python.exe -m pytest -q --basetemp D:\Project\.tmp\pytest-phase4 tests\test_phase4_basic_rag.py tests\test_grounding.py
```

See [`docs/phase4_release.md`](docs/phase4_release.md) and the generated
[`phase4_basic_rag.json`](evaluation/results/phase4_basic_rag.json). The
benchmark builds its university fixture corpus at runtime and does not use
`.tmp` artifacts as acceptance evidence.

Optional live Gemini grounding evidence is available with
`tests/integration/test_phase4_gemini.py`; it requires `RUN_LLM_INTEGRATION=1`
and a `GEMINI_API_KEY` supplied only through the environment.

## Performance evidence

The Task 2 benchmark engine in [`scripts/benchmark_t2.py`](scripts/benchmark_t2.py)
records parser/model measurements for an operator-supplied university corpus.
The useful engineering rules are:

- PyMuPDF is the production default for selectable-text PDFs;
- persisted SHA-256 cache lookup is much faster than first ingestion;
- the normal hybrid query path does not invoke a cross-encoder;
- encoder/reranker models are process-wide singletons when enabled;
- reranking is a deliberate hard-query feature because its CPU memory and cold
  load are too expensive for every web request.

See [`docs/performance_ux_checklist.md`](docs/performance_ux_checklist.md) for
the remaining web UX, observability, quota and deletion work.

## Free deployment target

The planned public demo uses a lightweight web frontend, background ingestion,
free-tier object/database storage and a provider free quota with mandatory
cache/rate limits. The free deployment must enforce small uploads, page limits,
per-user quotas and queue limits. It is a demo environment, not an unlimited
production SLA.

The architecture and phase-by-phase deployment work are documented in
[`plan.md`](plan.md). No API secret is required for the offline parser/retrieval
tests.

## Repository layout

```text
src/campusai/        package code
  ingestion/         validation, parsing, metadata, tables, chunking, jobs
  retrieval/         BM25, dense, hybrid, fusion, reranker, model runtime
  llm/               Task 1 provider/cache/retry foundation
  rag/               grounded answer and citation layer
tests/               offline and integration-contract tests
evaluation/          benchmark metrics and Task 2 evidence
data/benchmark/      small synthetic benchmark fixtures
configs/             local defaults and free-web quotas
docs/                acceptance and performance reports
```

## References used for design

- [MarkItDown](https://github.com/microsoft/markitdown) for a modular converter
  pipeline pattern and optional format dependencies;
- [FAISS](https://github.com/facebookresearch/faiss) for future vector-index
  scaling;
- [LlamaIndex ingestion pipeline](https://docs.llamaindex.ai/en/stable/module_guides/loading/ingestion_pipeline/)
  and [Haystack rankers](https://docs.haystack.deepset.ai/docs/ranker) for
  comparison of ingestion metadata flow and reranking placement.
- [Jmhzbmcn2/med_rag](https://github.com/Jmhzbmcn2/med_rag) for practical API,
  source-card, context-header and retrieval-evaluation patterns.
