# Task 1 — parser review and known failure cases

Generate a compact review artifact containing the first 30 chunks, first 10 tables, totals, and per-file exceptions:

```powershell
uv run python scripts/inspect_ingestion.py --input-dir data/raw --output data/processed/review.json
```

## Known failure modes to review manually

| PDF characteristic | Risk | Current handling |
|---|---|---|
| Repeated header/footer | Text pollution or false headings | Repeated top/bottom blocks are filtered using page position and frequency; unusual layouts still need review |
| Merged cells | Missing values or duplicate headers | Ragged rows are padded, whitespace normalized, and duplicate headers receive stable suffixes |
| Multi-page tables | Table may be split per page | Adjacent compatible schemas are stitched; repeated continuation headers are removed |
| Scanned/image-only pages | No text/table extraction | Detected and recorded as an OCR-required warning; OCR engine is not bundled |
| Complex nested tables | Several small extracted tables | Empty rows/columns are removed and cell text is normalized; ambiguous layouts are preserved for review |
| Vietnamese diacritics | Heading heuristic sensitivity | Unicode, numbering, font-size, and page-position signals are combined |
| Advanced layout | Reading order can be ambiguous | Text blocks, coordinates, font size, and margin filtering are used; no learned layout model is bundled |

The review artifact is generated local data and should not be committed.
