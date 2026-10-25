# CampusAI

Canonical repository: [trbk07/campusai-university-rag](https://github.com/trbk07/campusai-university-rag).

CampusAI is an evidence-grounded university knowledge assistant. It ingests
university PDFs and produces Vietnamese or English answers with page-level
citations and explicit abstention when evidence is missing.

The runtime indexes documents uploaded by the user and scopes queries to the
selected document IDs. `data/corpus/university/` is an evaluation fixture.

Phase 7/8 are complete under the owner's Chat-quality acceptance scope. Live
provider performance, availability and native API format qualification remain
open release conditions. Optional reranker qualification is deferred and the
feature stays disabled. See [the current roadmap](plan.md); historical
20-task/19-gate reports remain available for audit and future activation.

## Evaluation artifact storage

Git keeps benchmark/gold references, summaries and hash manifests. Historical
raw observations, corpus PDFs, models and indexes live in ignored local/external
storage. A clean clone needs the artifact bundle for historical recomputation;
missing evidence fails release validation. See [artifact storage and restore
commands](docs/operations/artifact_storage.md) and the [2026-10-05 size/history
audit](docs/operations/storage_audit_20261005.md). Run `make storage-check` before
committing and `make storage-verify` before release.

## Setup

Python 3.11–3.14 is supported. Run commands from the repository root.

```powershell
uv sync --extra dev
uv run pytest -q
uv run python -m scripts.dev.secret_scan
```

With an existing virtual environment:

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m scripts.dev.secret_scan
```

Optional parser, embedding, and reranker dependencies:

```powershell
uv sync --extra dev --extra feasibility
```

Copy `.env.example` to `.env` and supply provider credentials in the environment
for live LLM calls. Offline tests do not require an API key. Live provider tests
require `RUN_LLM_INTEGRATION=1` and `GEMINI_API_KEY`.

## Repository layout

```text
src/campusai/          application package
  documents/          document registry
  ingestion/          PDF parsing, OCR, tables, metadata, chunks, jobs
  retrieval/          BM25, dense search, fusion, routing, reranking
  llm/                provider clients, cache, retries, rate limits
  rag/                grounded answers, claims, citations, abstention
scripts/              operational commands, grouped by task
  dev/                environment setup and secret scanning
  ingestion/          corpus download, PDF acceptance and feasibility
  benchmarks/         dataset construction, review and validation
  retrieval/          index construction, isolation and warming
  operations/         server, load, accessibility, security, recovery
  release/            annotation signoff and release packaging
evaluation/           metrics and evaluation workflows
  common/             shared metrics and artifact bindings
  benchmarks/         schemas, human intake and dataset freezing
  grounding/          answer quality and grounding calibration
  retrieval/          baseline and hybrid retrieval evaluation
  reranker/           model, calibration, capacity, canary and release
  release/            grounding package validation
  artifacts/          raw artifact catalog and runtime manifests
  results/            canonical summaries and historical manifests
tests/                offline tests, fixtures and opt-in integrations
configs/              defaults, example records and release settings
data/benchmark/       versioned benchmark datasets
data/corpus/          source metadata; ignored local corpus PDFs
docs/                 architecture, task guides, operations and planning
plan.md               permanent project roadmap, retained by the owner
```

Naming and artifact rules are in [the contribution guide](docs/contributing.md).

## Run locally

On Windows, double-click **`start-campusai.cmd`** to start CampusAI and open the
browser. The launcher loads `.env` and your existing ignored `configs/key.yaml`
when needed, using the checked-in `free_llm.yaml` profile (Gemini 3.5 Flash-Lite). It never prints
keys, rotates credentials or enables billing. Existing environment settings
take priority. Keep its console open while using the app.

For local Vietnamese/English scan OCR, install the optional package and pinned
language data once:

```powershell
uv sync --extra dev --extra feasibility --extra ocr
uv run python -m scripts.operations.setup_ocr
```

The launcher selects this backend when its package and language checksums
validate. OCR runs in a separate bounded process; cancelling or timing out a
document stops that process. Open document details to start OCR on an existing
scan or mixed PDF. Uploads never download OCR models or send PDFs to an OCR
service. Explicit `CAMPUSAI_OCR_BACKEND` settings take priority.

An available CUDA GPU can be selected with `CAMPUSAI_DEVICE=cuda` in `.env`.
The owner laptop uses this setting after a same-model comparison:five real PDFs
finish in46.85s versus255.41s on CPU, with matching content hashes and near-identical
vectors. This is a local workload result; the full-app performance gates remain
in[the roadmap](plan.md).

Gemini 503 responses open a shared 60–300 second cooldown. During a provider
failure, the local app can show up to three verified original-source excerpts
with PDF links, so document lookup remains usable. The UI labels this degraded
view explicitly; the AI answer stays abstained, and excerpts are neither cached
as generated answers nor included in conversation history. Further lookups during
the cooldown do not call Gemini. The next user query after cooldown can recover
normal generation; the app never automatically resends a question.

A 429 response identifies an API quota/rate limit or a busy local query separately.
Four active queries are admitted by default; health, UI, document polling
and source lookup continue while that query waits. Corpus deletion waits for
the query to finish using its sources. No provider error is cached as an answer.
The [source-excerpt review](docs/deployment/phase13/provider-continuity.md) records
the failed live Flash-Lite experiment and the separate offline recovery tests.
Free API availability and unlimited generated answers have not been established.

Phase 13 targets [free cloud deployment](docs/deployment/phase13/profile-decision.md)
on Oracle Always Free, independently of the development laptop. Provisioning and
cloud acceptance are still pending; the detailed tasks remain in [plan.md](plan.md#phase-13--deployment).

The [cloud configuration/preflight guide](docs/deployment/phase13/runtime-configuration.md)
defines external state/config/model/release paths and pinned encoder identity.
`python -m scripts.operations.preflight --config /etc/campusai/deployment.json`
audits prerequisites without provider calls; it does not accept deployment.

```powershell
.venv\Scripts\python.exe -m scripts.operations.local --open-browser
.venv\Scripts\python.exe -m scripts.retrieval.build_index --help
.venv\Scripts\python.exe -m scripts.retrieval.warm_retrieval --help
```

Open **http://127.0.0.1:8000** for the CampusAI UI: AI assistant, document
library, metadata collections and guide. Upload a PDF, wait for **Sẵn sàng**,
select the source, ask a question, then open its citation or submit feedback.
The HTML/CSS/JavaScript frontend lives in `src/campusai/ui/`; no Node/build step
is needed to run the application. Assets are included in the Python package.

The default free profile admits one model request at a time, paced at ten
requests per minute with a bounded wait. New questions asked immediately after
one another can take about 6 seconds; an exact-context cache hit is much faster.
Validated answers are stored locally in `data/cache/grounded-answers.sqlite3`
across app restarts. Set `CAMPUSAI_RAG_CACHE_PATH=:memory:` to keep answer bodies
only until the process exits. Document deletion clears stored answers.

The profile retrieves up to eight ordinary-query candidates and fits verbatim
source windows into an 8,000-character evidence budget. Tables retain their
serialization; temporal/multi-hop requests retain the established serializer.
Durable admission and separate 429/503 cooldowns prevent repeated sends during
known faults. The owner confirmed Free tier; a bounded probe observed a Free
limit of 15 RPM and stopped at the first 429. Production stays at 10 RPM;
TPM/RPD ceilings remain unverified. During cooldown, manual local lookups stay
available and failed-question retries wait. See [quota result and handoff](docs/deployment/phase13/quota-exhaustion.md),
[model qualification and limits](docs/deployment/phase13/model-selection.md)
and [applied repository ideas](docs/deployment/phase13/repo-application-review.md).
The historical `product_llm.yaml` stays unchanged for explicit evaluation;
explicit environment/.env profile choices continue to take priority.

Questions about an uploaded PDF such as “tài liệu có mấy trang” are answered directly
from PDF metadata. Natural follow-ups keep their topic; a complete new question
starts a new topic. Section summaries retain more relevant source context, and
the active Free profile resolves model-selected citation IDs to original source
pages/quotes. See [natural conversation checks and fixes](docs/deployment/phase13/natural-conversation.md).

The local MVP is single-user. Set `CAMPUSAI_LLM_CONFIG` to select a different
existing provider configuration. Without credentials, the launcher shows setup
instructions. The advanced `scripts.operations.serve` transport still requires
explicit environment settings; it does not auto-load credentials. Real
embedding uploads need the optional `feasibility` dependencies and the model
available locally. The app uses `CAMPUSAI_STORE_DIR` / `CAMPUSAI_INDEX_DIR` for runtime
storage. An evaluation calibration is no longer selected implicitly for user
uploads; set `CAMPUSAI_RETRIEVAL_CALIBRATION` only to a calibration matching your
runtime corpus. Explicit calibration fingerprint checks remain enforced.

See [UI architecture, API mapping and acceptance](docs/ui/phase12-ui.md) for
screenshots, offline test results, clean setup and browser test commands.
Production hosting still requires provider configuration, authentication and
managed process/storage services; R-01/R-02 remain open in [plan.md](plan.md).

The default PDF path uses PyMuPDF and a SHA-256 cache. Docling is an optional
layout/table review tool. Scan-only PDFs require explicit bounded OCR; otherwise
ingestion returns a review-required status. Normal hybrid queries avoid loading
the cross-encoder. The optional reranker is enabled explicitly for hard queries.

## Evaluation and release commands

Use `python -m package.module` for consistent imports on Windows and Unix.
The Makefile selects the virtual environment's Python for the current platform.

| Task | Make target | Python module |
| --- | --- | --- |
| Offline tests | `make test` | `pytest -q` |
| Grounding fixture diagnostics | `make grounding-eval` | `evaluation.grounding.run_grounding_eval` (gold-derived; not release evidence) |
| Grounding report validation | `make release-validate` | `evaluation.grounding.validate_grounding_release` |
| Grounding package validation | `make grounding-package-validate` | `scripts.release.package_grounding_release` |
| Hybrid benchmark construction | `make hybrid-benchmark` | `scripts.benchmarks.build_hybrid_benchmark` |
| Corpus index construction | `make hybrid-index` | `scripts.retrieval.build_corpus_index` |
| Hybrid confidence calibration | `make hybrid-calibrate` | `evaluation.retrieval.calibrate_hybrid_confidence` |
| Hybrid quality evaluation | `make hybrid-evaluate` | `evaluation.retrieval.evaluate_hybrid_release` |
| Hybrid release validation | `make hybrid-validate` | `evaluation.retrieval.validate_hybrid_release` |
| Student query dataset | `make student-natural-benchmark` | `evaluation.benchmarks.build_student_natural_benchmark` |
| Reranker release stages | `make reranker-<stage>` | `evaluation.reranker.release_workflow <stage>` |

Phase 5 native inference, benchmark repair and independent-review requirements:
[current audit and handoff](docs/grounding/phase5_completion.md),
[operations workflow](docs/operations/grounding_operations.md).

Reranker stages are `baseline`, `human-freeze`, `candidate`, `model`, `route`,
`calibration`, `quality`, `performance`, `security`, `faults`, `rollback`,
`staging`, `staging-collect`, `validate`, and `release`. Pass extra options with
`RERANKER_ARGS`. The workflow enforces prerequisites and evidence bindings.

For hybrid CPU measurements, set `OMP_NUM_THREADS=1` and `MKL_NUM_THREADS=1`
before running `make hybrid-operations`.

## Documentation

- [Product roadmap](plan.md) and [release hardening plan](docs/planning/release_hardening_plan.md)
- [Provider acceptance](docs/llm/provider_acceptance.md)
- [Ingestion release](docs/ingestion/ingestion_release.md) and [PDF feasibility](docs/ingestion/pdf_pipeline_feasibility.md)
- [Grounding contract](docs/architecture/grounding_contract.md) and [production reproducibility](docs/grounding/production_reproducibility.md)
- [Hybrid retrieval release](docs/retrieval/hybrid_release.md) and [hybrid operations](docs/operations/hybrid_operations.md)
- [Reranker release runbook](docs/reranker/reranker_release_runbook.md) and [release plan](docs/reranker/release_plan.md)
- [Data governance](docs/operations/data_governance.md)

Checked-in reports retain their original measurements, hashes and release IDs.
Source-bound release fingerprints must be regenerated after this restructuring
from a clean, reviewed commit. The historical manifests cannot certify the
current source tree. See [artifact rules](docs/contributing.md#evaluation-evidence).
