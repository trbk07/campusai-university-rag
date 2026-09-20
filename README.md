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

## Ingestion (Groups B / T3-T4)

```powershell
uv run python -c "from finrag.ingestion.pipeline import ingest_document; print(ingest_document('report.pdf'))"
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
with an actionable OCR message. The default safety limits are 50 MB and 200
pages and can be overridden explicitly for local experiments.

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

See [`docs/task1_failure_cases.md`](docs/task1_failure_cases.md) for known parser limitations and [`docs/task1_acceptance.md`](docs/task1_acceptance.md) for the reproducible Task 1 acceptance report and Task 2 handoff criteria.

## Tests

```powershell
uv run pytest -q
```

## Data policy

Raw reports and generated outputs are local artifacts and are ignored by Git. Use small synthetic fixtures in tests; do not commit proprietary or large PDFs.

