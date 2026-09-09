# Task 1 — parser review and known failure cases

Generate a compact review artifact containing the first 30 chunks, first 10 tables, totals, and per-file exceptions:

```powershell
uv run python scripts/inspect_ingestion.py --input-dir data/raw --output data/processed/review.json
```

## Known failure modes to review manually

| PDF characteristic | Risk | Current handling |
|---|---|---|
| Repeated header/footer | Text pollution or false headings | Text is normalized; footer classifier is future work |
| Merged cells | Missing values or duplicate headers | Rows are padded; duplicate headers get stable suffixes |
| Multi-page tables | Table may be split per page | Tables retain page metadata; stitching is future work |
| Scanned/image-only pages | No text/table extraction | Requires OCR, outside Task 1 |
| Complex nested tables | Several small extracted tables | Empty tables are discarded; manual review remains necessary |
| Vietnamese diacritics | Heading heuristic sensitivity | Unicode-aware basic heuristic; no layout model yet |

The review artifact is generated local data and should not be committed.
