# Task 2 feasibility benchmark for CampusAI

This document describes a repeatable benchmark, not a checked-in result. The
previous machine-specific financial snapshot and generated PDFs were removed
when the project moved to university knowledge.

## What is measured

The benchmark separates evidence-producing stages:

1. PDF admission and SHA-256 identity;
2. cold parsing, first ingestion and warm persisted-cache lookup;
3. optional Docling conversion for layout/table review;
4. optional embedding and reranker cold/warm measurements;
5. RSS peak, latency, throughput, embedding dimension and environment;
6. manual table/layout review checks;
7. conservative page and memory limits derived from the supplied corpus.

The runner is [`scripts/benchmark_t2.py`](../scripts/benchmark_t2.py). It
supports resume, isolates individual document failures, and does not write page
text into the report.

## Reproduction with a university corpus

Supply a directory containing representative university PDFs. Include both
Vietnamese and English text PDFs, at least one curriculum/regulation table, a
mixed-layout document and a holdout document outside the main input directory.

```powershell
.venv\Scripts\python.exe scripts\benchmark_t2.py `
  --input-dir <university-pdf-dir> `
  --holdout <holdout.pdf> `
  --output evaluation\t2_results.json

.venv\Scripts\python.exe scripts\validate_t2.py evaluation\t2_results.json
.venv\Scripts\python.exe scripts\create_t2_table_review.py `
  evaluation\t2_results.json --output evaluation\t2_table_review.json
.venv\Scripts\python.exe scripts\validate_t2.py evaluation\t2_results.json `
  --acceptance --review evaluation\t2_table_review.json
```

The output files are local benchmark artifacts and should only be committed
when they describe an intentional, reproducible CampusAI corpus. Do not commit
private university PDFs or extracted content.

## Optional heavy benchmark

```powershell
uv sync --extra feasibility
.venv\Scripts\python.exe scripts\benchmark_t2.py `
  --input-dir <university-pdf-dir> `
  --holdout <holdout.pdf> `
  --run-docling --docling-max-pages 30 --run-models --device cpu `
  --batch-size 2 --repeats 1 --model-text-count 8 `
  --memory-budget-mb 8192 --output evaluation\t2_results.json
```

Run CUDA separately only when the deployment target actually has CUDA. Model
downloads are explicit; missing optional dependencies are recorded as blocked,
not silently treated as successful measurements.

## Acceptance gates

An artifact is acceptance-ready only when:

- the supplied corpus completes and includes a holdout;
- Vietnamese/English, text, scan/mixed-layout and table cases are represented;
- optional model metrics are complete when model benchmarking is requested;
- Docling output has a manual comparison when requested;
- the table review queue is complete;
- measured limits pass the failure-rate gate;
- every promoted limit records its corpus, environment and command.

Task 2 results are feasibility evidence, not a product guarantee. Public web
quotas should be stricter than a machine benchmark and must be configured per
deployment environment.

## Product decisions based on the benchmark

- PyMuPDF remains the default parser for selectable-text PDFs.
- Docling is a review/fallback path for layout-heavy documents, not the normal
  interactive request path.
- Scan-only PDFs enter an OCR/review queue rather than blocking a web request.
- The normal query path is BM25 + dense + RRF; reranking is opt-in for hard
  questions and must have a memory/timeout fallback.
- Indexes are persisted per document/corpus version and query embeddings are
  reused across selected documents.
