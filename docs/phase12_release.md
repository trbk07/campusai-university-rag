# CampusAI Task 1/Task 2 release evidence

Status: acceptance-complete for Task 1, Phase 1/2, and extended T2 scope.

## Version and environment

- Release tags: `phase12-complete` and the final `task2-complete` tag
  (commit message: `chore: complete T2 extended acceptance`).
- Package version: `0.1.0` (`campusai-evidence-rag` / `campusai`).
- Python: `3.14.6`.
- OS: Windows 11, AMD64, CPU execution.
- Key packages: PyMuPDF `1.28.2`, pdfplumber `0.11.10`, PyYAML `6.0.3`, pytest `8.4.2`, pytest-cov `7.1.0`.
- OCR package: rapidocr-onnxruntime `1.4.4`, pytesseract `0.3.13`.
- Parser: `pymupdf-text-v1`.
- Chunker: `structure-v2`.

## Corpus and reproducibility

- Corpus: 8 public UET/VNU PDFs in `data/corpus/university`.
- Manifest SHA-256: `a99ce0f56ddd43eb38ede84d1dda0c80923822fd2a0dfccbf7b5bd6810222309`.
- Holdout: `uet_admission_2025.pdf` (`096c6bac40069130d9e6bec2343f9936ed41b308f4f9ec533b29bd70eb3003a7`).
- Acceptance report SHA-256: `d68322a2dbabab8c23da795861fcbbcdab5eb7e433c6789d1be83731d8ddd72c`.
- T2 report SHA-256: `3a8aef0d7962175524bfeaff14247b6c8506e97858a21838daafc94575ecb0a4`.
- T2 table-review SHA-256: `60325726a372bd508ea09f23c88921864e76277c53c792f6ce8017de90b60af0`.
- OCR acceptance SHA-256: `e0bdde1dde79f053c79345e68abd517528cb77fddacdc55ca77a0d495b42b91e`.
- Reports contain hashes/metrics and no extracted page text.
- OCR acceptance: RapidOCR ONNX processed the 32-page holdout with 32/32 pages
  containing text, average confidence `0.946419`, within a 180-second budget.

## Command results

```text
Full repository: 75 passed, 1 skipped
Full-source coverage: 86.29% (required >= 85%; run with
`pytest --cov=src/campusai --cov-report=term-missing`)
Phase 1/2 acceptance: 16/16 exit criteria true
T2 normal report validation: pass
T2 extended acceptance: pass (models, Docling comparison, table review)
Secret scan: pass
Compileall: pass
git diff --check: pass
```

The live Gemini test is opt-in and remains skipped without an externally
provided key. It is not used to claim offline acceptance.

## Policy and known limitations

- PyMuPDF is the default production parser for selectable-text PDFs.
- Docling comparison and table review are complete in the T2 evidence.
- Model benchmark completed on CPU: dense peak RSS about 2.6 GB and reranker
  peak RSS about 5.0 GB; reranking remains feature-flagged for safe deployment.
- Scan-only files use the explicit RapidOCR ONNX worker when OCR is enabled;
  page/time limits are enforced. Without opt-in, they still fail closed as
  `review_required/ocr_required` and are not indexed.
- The SQLite cache is not encrypted at rest; filesystem permissions remain an
  operator responsibility. Distributed multi-process locking is out of scope.
- LLM cache keys are provider/query hashes and contain no document ID, so full
  document deletion purges storage and retrieval indexes but leaves unrelated
  query responses untouched.
- The T2 report is reproducible extended benchmark evidence. The model run was
  CPU-only and the model/cache downloads are not committed; the report records
  the exact environment and measurements.

## Release hygiene

The release commit contains the reviewed code, documentation, reports, and
manifest. The working tree was clean after the commit/tag operation. No
credentials, live cache, or private PDF is included; the ignored public PDFs
are reproducible from the manifest/download script.
