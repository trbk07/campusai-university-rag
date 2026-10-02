# CampusAI

CampusAI is an evidence-grounded university knowledge assistant. It ingests
university PDFs and produces Vietnamese or English answers with page-level
citations and explicit abstention when evidence is missing.

The runtime indexes documents uploaded by the user and scopes queries to the
selected document IDs. `data/corpus/university/` is an evaluation fixture.

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
  results/            checked-in evaluation evidence
tests/                offline tests, fixtures and opt-in integrations
configs/              defaults, example records and release settings
data/benchmark/       versioned benchmark datasets
data/corpus/          reproducible source corpus
docs/                 architecture, task guides, operations and planning
plan.md               permanent project roadmap, retained by the owner
```

Naming and artifact rules are in [the contribution guide](docs/contributing.md).

## Run locally

```powershell
.venv\Scripts\python.exe -m scripts.operations.serve
.venv\Scripts\python.exe -m scripts.retrieval.build_index --help
.venv\Scripts\python.exe -m scripts.retrieval.warm_retrieval --help
```

The demo uses a dependency-free WSGI UI. Production hosting still requires
provider configuration and managed process/storage services.

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
| Grounding evaluation | `make grounding-eval` | `evaluation.grounding.run_grounding_eval` |
| Grounding report validation | `make release-validate` | `evaluation.grounding.validate_grounding_release` |
| Grounding package validation | `make grounding-package-validate` | `scripts.release.package_grounding_release` |
| Hybrid benchmark construction | `make hybrid-benchmark` | `scripts.benchmarks.build_hybrid_benchmark` |
| Corpus index construction | `make hybrid-index` | `scripts.retrieval.build_corpus_index` |
| Hybrid confidence calibration | `make hybrid-calibrate` | `evaluation.retrieval.calibrate_hybrid_confidence` |
| Hybrid quality evaluation | `make hybrid-evaluate` | `evaluation.retrieval.evaluate_hybrid_release` |
| Hybrid release validation | `make hybrid-validate` | `evaluation.retrieval.validate_hybrid_release` |
| Student query dataset | `make student-natural-benchmark` | `evaluation.benchmarks.build_student_natural_benchmark` |
| Reranker release stages | `make reranker-<stage>` | `evaluation.reranker.release_workflow <stage>` |

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
