# Task 2 feasibility validation

## What is measured

The benchmark is intentionally split into evidence-producing stages:

1. PDF admission and SHA-256 identity.
2. Cold local parsing, first ingestion, and warm persisted-cache lookup.
3. Optional Docling conversion on the same operator-supplied PDFs.
4. FastEmbed supported-model inventory without a download.
5. Optional `BAAI/bge-m3` and `BAAI/bge-reranker-v2-m3` CPU/CUDA runs.
6. RSS peak, cold/warm latency, throughput, embedding dimension, and runtime metadata.
7. A manual table/layout review queue with five explicit checks.
8. A conservative page limit derived from measured p95 parse latency and memory.

The runner is `scripts/benchmark_t2.py`. It writes after each PDF, supports
`--resume`, isolates failures, and keeps document text out of the report.

## Reproduction

Parser-only run:

```powershell
.venv\Scripts\python.exe scripts\benchmark_t2.py `
  --input-dir <directory-containing-user-supplied-pdfs> `
  --output evaluation\t2_results.json
.venv\Scripts\python.exe scripts\validate_t2.py evaluation\t2_results.json
.venv\Scripts\python.exe scripts\create_t2_table_review.py `
  evaluation\t2_results.json --output evaluation\t2_table_review.json
```

Install the opt-in benchmark stack before running Docling or model downloads:

```powershell
uv sync --extra feasibility
.venv\Scripts\python.exe scripts\benchmark_t2.py `
  --input-dir <directory-containing-user-supplied-pdfs> `
  --run-docling --run-models --device cpu
```

For Colab/CUDA, run the same command with `--device cuda` and retain the
environment metadata and JSON as a separate run. `--run-models` is explicit so
large model downloads cannot happen accidentally.

## Acceptance gates

The report can be called acceptance-ready only when all of these are true:

- `summary.complete` is true for the supplied corpus;
- there is representative Vietnamese and English text, scan/mixed-layout, and
  table coverage, including a holdout document;
- `models.status == "success"` contains dense and reranker cold/warm metrics,
  throughput, dimension, and RSS;
- Docling output has been reviewed against the local parser;
- the table review queue is filled for the selected sample;
- `limits.status == "measured"` and its failure-rate gate passes;
- CPU and CUDA/Colab runs are reported separately when both deployment modes
  are in scope.

The validator accepts older schema-1 artifacts for compatibility, but new runs
use schema 2 and require explicit `fastembed` and `limits` sections. Missing
optional dependencies are recorded as `blocked`; they do not count as a model
benchmark.

## Current local evidence

The checked-in local run contains one 213-page English text PDF and one
125-page image-only PDF. The text PDF produced a cold parse measurement and a
warm cache measurement; the scan was correctly skipped with an OCR-required
reason. FastEmbed is installed and reports 37 supported models, but
`BAAI/bge-m3` is not one of them. Docling and sentence-transformers are
installed, yet their model snapshots are not present locally and outbound
Hugging Face traffic is blocked, so no bge latency or reranker result is
claimed. The CPU and CUDA attempts are retained separately in
`evaluation/t2_results.json` and `evaluation/t2_results_cuda.json`; the latter
records `cuda.available=false`. The table queue is pending manual review.

The derived page limit is intentionally not copied into production config until
the missing corpus, model, and review evidence is supplied. The configured
`50 MB / 250 pages` remains a provisional safety cap, not a measured model SLA.
