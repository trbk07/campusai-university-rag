# CampusAI Phase 1/2 release evidence

Status: acceptance-complete for the declared offline scope.

## Version and environment

- Release tag: `phase12-complete` (commit message: `chore: close Task 1 and Phase 1/2 acceptance gates`).
- Package version: `0.1.0` (`campusai-evidence-rag` / `campusai`).
- Python: `3.14.6`.
- OS: Windows 11, AMD64, CPU execution.
- Key packages: PyMuPDF `1.28.2`, pdfplumber `0.11.10`, PyYAML `6.0.3`, pytest `8.4.2`, pytest-cov `7.1.0`.
- Parser: `pymupdf-text-v1`.
- Chunker: `structure-v2`.

## Corpus and reproducibility

- Corpus: 8 public UET/VNU PDFs in `data/corpus/university`.
- Manifest SHA-256: `a99ce0f56ddd43eb38ede84d1dda0c80923822fd2a0dfccbf7b5bd6810222309`.
- Holdout: `uet_admission_2025.pdf` (`096c6bac40069130d9e6bec2343f9936ed41b308f4f9ec533b29bd70eb3003a7`).
- Acceptance report SHA-256: `5c4db7ad9415fc1cfe09759af5635b320cce7990a805cbc4ebef25390d51a83f`.
- T2 report SHA-256: `353f4104695c1223ba179ac1b8da24289b2614a445ef17112061c14f947cfe40`.
- Reports contain hashes/metrics and no extracted page text.

## Command results

```text
Task 1 tests: 33 passed
Full repository: 70 passed, 1 skipped
Task 1 coverage: 95.01% (required >= 90%)
Phase 1/2 acceptance: 16/16 exit criteria true
T2 normal report validation: pass
Secret scan: pass
Compileall: pass
git diff --check: pass
```

The live Gemini test is opt-in and remains skipped without an externally
provided key. It is not used to claim offline acceptance.

## Policy and known limitations

- PyMuPDF is the default production parser for selectable-text PDFs.
- Docling is an optional layout/table review or fallback path; extended model
  and Docling acceptance is a Phase 3 feasibility gate, not a Phase 1/2 gate.
- Scan-only files fail closed as `review_required/ocr_required` and are not
  indexed. OCR production is deferred until an OCR worker is installed and
  independently verified with page/time/cost limits.
- The SQLite cache is not encrypted at rest; filesystem permissions remain an
  operator responsibility. Distributed multi-process locking is out of scope.
- The T2 report is reproducible normal benchmark evidence. Its extended
  `--acceptance` mode intentionally remains deferred because models, Docling,
  and manual table review are not mandatory for the declared scope.

## Release hygiene

The release commit contains the reviewed code, documentation, reports, and
manifest. The working tree was clean after the commit/tag operation. No
credentials, live cache, or private PDF is included; the ignored public PDFs
are reproducible from the manifest/download script.
