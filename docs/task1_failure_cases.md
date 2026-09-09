# Task 1 — parser review and known failure cases

Generate a compact review artifact containing the first 30 chunks, first 10 tables, totals, and per-file exceptions:

```powershell
uv run python scripts/inspect_ingestion.py --input-dir data/raw --output data/processed/review.json
```

## Known failure modes to review manually

| PDF characteristic | Risk | Current handling |
|---|---|---|
| Repeated header/footer | Text pollution or false headings | Cleaned blocks repeated in the first/last two positions on at least two pages are removed before heading detection; varying, body-position, or unusual headers/footers remain for review |
| Merged cells | Missing values or duplicate headers | Rows are padded to the widest row, cell whitespace is normalized, all-empty rows/columns are dropped, and duplicate/blank headers receive stable names; cell-spanning meaning is not reconstructed |
| Multi-page tables | Table may be split per page or continuation rows may be misclassified | Consecutive page tables with identical normalized column names are stitched across 3+ pages; repeated continuation headers are removed after case/whitespace/punctuation/unit normalization; non-adjacent or differing schemas remain separate, with start/end pages recorded |
| Scanned/image-only pages | No text layer or native table extraction | Pages without text blocks produce an `OCR required` warning by default; with `--ocr`, local Tesseract renders and OCRs the page, records OCR failures, and preserves empty-result warnings. Tesseract and language data are installed separately by the setup script |
| Complex nested tables | Several small extracted tables or ambiguous cell boundaries | pdfplumber tables are normalized independently, empty rows/columns are removed, and cell text is cleaned; nested structure is not inferred or flattened semantically, so ambiguous layouts are preserved for review |
| Vietnamese diacritics | Heading heuristic sensitivity or OCR character errors | Heading detection is Unicode-aware and combines uppercase, numbering, relative font size, short-title, and page-position signals; Vietnamese OCR uses the separately installed `vie` language data, but scans still require review |
| Advanced layout | Reading order can be ambiguous | Text is read from PyMuPDF blocks and line spans using coordinates, font size, and block order; only repeated top/bottom margin blocks are filtered. No learned layout model or geometric table reconstruction is bundled |

The review artifact is generated local data and should not be committed.
