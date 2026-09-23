# Adaptive Financial RAG

Implementation follows `plan.md` and its `src/finrag/` structure. Groups A and B provide the isolated LLM foundation plus PDF ingestion with validation, page provenance, tables, metadata, chunking, registry, and SHA256 caching.

## Environment

All Python dependencies are installed inside the repository's `.venv`; nothing is installed globally. The recommended one-command setup is:

```powershell
# Windows
python scripts\\bootstrap.py
.venv\\Scripts\\python.exe -m pytest -q

# macOS/Linux
python3 scripts/bootstrap.py
.venv/bin/python -m pytest -q
```

If `uv` is available, the equivalent reproducible setup is `uv sync --extra dev`, followed by `uv run pytest -q`. Copy `.env.example` to `.env` and set `GEMINI_API_KEY` (or `GROQ_API_KEY`) before using a real LLM. The first real request is sent to the provider; repeated identical prompts are served from `data/cache/llm_cache.sqlite` with original usage and latency preserved.

### Task 1 (T1): LLM foundation acceptance tests

Task 1 is the provider-neutral LLM foundation described in
[`docs/t1_acceptance.md`](docs/t1_acceptance.md). Offline acceptance tests use a
deterministic mocked transport and run with:

```powershell
python -m pytest -q tests/test_llm.py tests/test_llm_acceptance.py
```

The document-processing work below is separate ingestion work (Groups B / T3-T4),
not Task 1.

The optional live Gemini test must be explicitly enabled; it is skipped by default and never logs the API key:

```powershell
$env:RUN_LLM_INTEGRATION = "1"
$env:GEMINI_API_KEY = "..."
python -m pytest -q tests/integration
```

The SQLite cache stores response text, provider usage metadata, and original network latency. Cache hits do not invoke the provider or rate limiter. Concurrent identical cache misses are single-flight and create one provider request. Transient HTTP errors (408, 429, 5xx) and temporary network failures are retried with bounded exponential backoff; authentication and other 4xx errors are not retried. Gemini credentials use a request header and are never part of URLs or cache keys. Do not commit `.env`, API keys, or cache databases.

### Task 2 (T2): feasibility benchmark

Task 2 has a reproducible, opt-in benchmark at
[`scripts/benchmark_t2.py`](scripts/benchmark_t2.py). It separates cold PyMuPDF
parse time, first ingestion, and warm SHA-256 cache lookup; records page/table
coverage, RSS peak, environment metadata, and failure isolation. The benchmark
accepts only PDFs supplied through `--input-dir` and never names a production
document in code.

Run the parser-only evidence collection offline:

```powershell
.venv\Scripts\python.exe scripts\benchmark_t2.py `
  --input-dir <directory-containing-user-supplied-pdfs> `
  --output evaluation\t2_results.json
.venv\Scripts\python.exe scripts\validate_t2.py evaluation\t2_results.json
```

The optional feasibility environment is intentionally separate from production:

```powershell
uv sync --extra feasibility
.venv\Scripts\python.exe scripts\benchmark_t2.py `
  --input-dir <directory-containing-user-supplied-pdfs> `
  --run-docling --run-models --device cpu
```

Use `--device cuda` in a CUDA/Colab runtime and keep that JSON as a separate
run. Model downloads are never implicit. The report records the exact
FastEmbed `TextEmbedding.list_supported_models()` output, bge-m3 and
reranker cold/warm latency, throughput, embedding dimension, model-load RSS,
and CUDA metadata. A report is `acceptance_ready` only when model execution and
measured parser limits both exist; blocked or skipped components remain visible.

Create the manual table/layout review queue after parsing:

```powershell
.venv\Scripts\python.exe scripts\create_t2_table_review.py `
  evaluation\t2_results.json --output evaluation\t2_table_review.json
```

The queue has explicit checks for headers, numeric cells, column alignment,
merged cells, and page continuity. Do not promote the derived upload limits
until representative Vietnamese/English text PDFs, scan/mixed-layout PDFs,
model CPU/CUDA measurements, and the manual table review are complete. The
current checked-in `50 MB / 250 pages` values remain a provisional safety cap;
they are not presented as an SLA.

For the coverage gate and tracked-file secret scan:

```powershell
uv run --extra dev pytest -q --cov=finrag.llm --cov-fail-under=90
python scripts/secret_scan.py
```

On Windows, the equivalent Make targets are `make test-windows`,
`make coverage-windows`, and `make secret-scan-windows`. If `make` is not
installed, run the commands directly from PowerShell:

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m pytest -q --cov=finrag.llm --cov-fail-under=90
.venv\Scripts\python.exe scripts\secret_scan.py
```

## Ingestion (Groups B / T3-T4)

```powershell
uv run python -c "from finrag.ingestion.pipeline import ingest_document; print(ingest_document('path\provided\by\the\user\report.pdf'))"
```

The current parser uses PyMuPDF as a deterministic local adapter; scanned PDFs are rejected with a clear OCR error rather than producing unreliable text. Tables are stored as Parquet when an optional local Parquet backend is available, with a JSON schema beside each table; ingestion itself never fails just because that optional backend is absent. Outputs go to `data/store/<sha256>/` and repeat uploads use the cache.

### Groups A/B acceptance

The T1–T4 foundation is implemented in `src/finrag`: provider-neutral LLM clients
(`complete`/`generate` plus JSON parsing), SQLite response caching with original
usage and latency, a thread-safe RPM limiter, PDF validation, page-preserving
parsing, conservative table extraction, automatic metadata detection, and
text/table chunks. `ingest_document()` registers each successful document in
`<store>/registry.json`; a repeated upload is identified by the file SHA256 and
returns the persisted result without parsing again. Image-only PDFs fail fast
with an actionable OCR message. The default safety limits are 50 MB and 250 pages, selected from the Task 2 feasibility benchmark; they can be overridden explicitly for local experiments.

### Groups C/D: retrieval and dev evaluation

Build one BM25 and one dense index per ingested document:

```powershell
uv run python scripts\build_index.py --store-dir data\store --index-dir data\index
```

The default dense encoder is a deterministic hashed-vector fallback so the
pipeline is reproducible offline. To use `BAAI/bge-m3` and the optional
cross-encoder reranker, install `sentence-transformers` and pass the model
name with `--dense-model`; the persisted index still keeps each document
isolated. Search can combine BM25 and dense results with RRF and preserve
`doc_id`, page, chunk, and content type through `HybridRetriever`.

Validate the 20-row dev benchmark and run the T8 retrieval comparison with:

```powershell
uv run python scripts\validate_benchmark.py data\benchmark\dev.jsonl
uv run python evaluation\run_retrieval_eval.py --index-root data\index
```

The evaluator reports Recall@3, Recall@5, MRR, and per-query results for
BM25, dense, hybrid, and hybrid+rerank. Benchmark labels remain external
evaluation data; they are not used by ingestion or retrieval code.

For a complete Windows OCR setup after cloning:

```powershell
# Run PowerShell as Administrator because vie.traineddata is installed under Program Files
powershell -ExecutionPolicy Bypass -File scripts\setup_ocr_windows.ps1
uv run python scripts\ocr_check.py --language eng+vie
```

The project supports Python 3.11–3.14. Do not commit `.venv`, `.env`, source PDFs, models, or generated indexes.

## Task 1: document processing

Put local PDFs in `data/raw/`, then run:

```powershell
uv run python scripts\ingest_documents.py --input-dir data\raw --output-dir data\processed
```

For scanned/image-only PDFs, install the optional Python OCR dependencies and the Tesseract executable:

```powershell
uv sync --extra dev --extra ocr
# Windows: install Tesseract with winget (standard path is auto-detected)
winget install --id UB-Mannheim.TesseractOCR -e --accept-package-agreements --accept-source-agreements
# Or install from https://github.com/UB-Mannheim/tesseract/wiki
uv run python scripts\ingest_documents.py --input-dir data\raw --output-dir data\processed --ocr --ocr-language eng
# Optional word-level confidence and bounding boxes for review queues
uv run python scripts\ingest_documents.py --input-dir data\raw --output-dir data\processed --ocr --ocr-confidence
```

The adapter automatically detects `C:\Program Files\Tesseract-OCR\tesseract.exe`, PATH installations, and `TESSERACT_CMD`; it also accepts `--tesseract-cmd` for custom locations. For Vietnamese OCR, install the `vie` Tesseract language data and use `--ocr-language vie` (or `eng+vie`). The repository does not commit OS-specific Tesseract binaries; the setup script installs the correct runtime on each Windows machine.

The output contains `chunks.jsonl`, `manifest.json`, and CSV tables under `tables/`. Text chunks retain `doc_id`, page, section, content type, and source. Tables remain structured as DataFrames during parsing and are serialized as CSV only at the output boundary. Table manifests also retain non-destructive diagnostics for ambiguous merged or multi-row headers, numeric parse status, and high-confidence financial invariant warnings; raw cell values are not silently rewritten. With `--ocr-confidence`, the manifest also contains per-page Tesseract word confidence, low-confidence counts, and rendered-image bounding boxes; confidence is a review signal, not a calibrated probability.

Optional PDF repair/preflight support is available with `uv sync --extra pdf-repair`. It checks encryption and structural errors through pikepdf/qpdf without modifying the original PDF. Encrypted files still require the correct password.

Run a resumable, metrics-only benchmark over all PDFs (no extracted text is written): `uv run python scripts/benchmark_ingestion.py --input-dir data/raw --output data/processed/benchmark.json`. The report is checkpointed after every PDF and can resume with `--resume`; `summary.complete=true` and `summary.coverage=1.0` are the acceptance gates for the full corpus.

Generate a compact manual review report with 30 chunks, 10 tables, and parser failures:

```powershell
uv run python scripts\inspect_ingestion.py --input-dir data\raw --output data\processed\review.json
```

Run the anonymized ground-truth evaluator with `uv run python scripts/ground_truth.py --annotations data/ground_truth/annotations.json --predictions data/ground_truth/predictions.json --output data/processed/ground_truth.report.json`. It reports header and numeric-cell precision/recall/F1 plus table-dimension accuracy without storing document text. Financial validation also emits numeric warnings for unparsed cells and high-confidence invariant failures; explicit units such as million/billion are detected without guessing from magnitude.

See [`docs/t1_acceptance.md`](docs/t1_acceptance.md) for the reproducible Task 1 acceptance report and its documented limitations. Ingestion-specific diagnostics are described in the ingestion sections above.

## Tests

```powershell
uv run pytest -q
```

## Data policy

Raw reports and generated outputs are local artifacts and are ignored by Git. Use small synthetic fixtures in tests; do not commit proprietary or large PDFs.

