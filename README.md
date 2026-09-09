# Adaptive RAG for Financial & Business Reports

Adaptive RAG for semi-structured financial and business PDFs.

## Environment

This project uses `uv` so dependencies are isolated in `.venv` and reproducible with `uv.lock`.

```powershell
uv sync --extra dev
```

The project supports Python 3.11–3.14. Do not commit `.venv`, `.env`, source PDFs, models, or generated indexes.

## Task 1: document processing

Put local PDFs in `data/raw/`, then run:

```powershell
uv run python scripts\ingest_documents.py --input-dir data\raw --output-dir data\processed
```

The output contains `chunks.jsonl`, `manifest.json`, and CSV tables under `tables/`. Text chunks retain `doc_id`, page, section, content type, and source. Tables remain structured as DataFrames during parsing and are serialized as CSV only at the output boundary.

Generate a compact manual review report with 30 chunks, 10 tables, and parser failures:

```powershell
uv run python scripts\inspect_ingestion.py --input-dir data\raw --output data\processed\review.json
```

See [`docs/task1_failure_cases.md`](docs/task1_failure_cases.md) for known parser limitations.

## Tests

```powershell
uv run pytest -q
```

## Data policy

Raw reports and generated outputs are local artifacts and are ignored by Git. Use small synthetic fixtures in tests; do not commit proprietary or large PDFs.

