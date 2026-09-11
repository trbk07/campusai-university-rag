# Adaptive RAG for Financial & Business Reports

Adaptive RAG for semi-structured financial and business PDFs.

## Environment

This project uses `uv` so dependencies are isolated in `.venv` and reproducible with `uv.lock`.

```powershell
uv sync --extra dev
```

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

