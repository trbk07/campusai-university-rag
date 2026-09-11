# Task 1 acceptance report

## Scope

Task 1 covers structure-aware ingestion of the local financial/business PDF corpus. The
pipeline must preserve text and tables separately, attach provenance metadata, avoid
silently rewriting ambiguous values, and produce diagnostics for cases that need manual
review.

## Reproducible checks

Run these commands from the repository root:

```powershell
uv run python scripts\ingest_documents.py --input-dir data\raw --output-dir data\processed\task1-one --clean-output
uv run python scripts\benchmark_ingestion.py --input-dir data\raw --output data\processed\task1-benchmark.json
uv run python scripts\inspect_ingestion.py --input-dir data\raw --output data\processed\task1-review.json
uv run pytest -q
```

The benchmark is a metrics-only corpus check. The review report contains the first 30
chunks, first 10 tables, page geometry, diagnostics, and parser failures. Generated
reports are local artifacts and are intentionally ignored by Git.

## Current corpus result

The checked-in local corpus contains 7 PDFs:

| Check | Result | Interpretation |
|---|---:|---|
| PDFs discovered | 7 | Full local corpus was included |
| Benchmark coverage | 1.0 | Every PDF was processed |
| Benchmark complete | `true` | No corpus file was skipped |
| Failed documents | 0 | No document caused an unhandled ingestion failure |
| Pages | 773 | Pages processed |
| Chunks | 1,291 | Structure-aware text chunks emitted |
| Tables | 378 | Tables preserved as separate structured outputs |
| Review-required tables | 310 | Ambiguous tables are retained and queued for review |
| Numeric coverage | 90.07% | 2,458 of 2,729 numeric candidates parsed deterministically |
| Parser failures in review report | 0 | Review report completed for every PDF |

## Acceptance interpretation

Task 1 is **parse-ready and suitable as the input contract for Task 2**:

- the complete corpus is processed;
- no document fails at the parser boundary;
- chunks retain document/page/section/content-type provenance;
- tables remain structured and are serialized separately at the output boundary;
- ambiguous headers, numeric cells, OCR pages, and PDF issues produce diagnostics;
- output provenance is recorded in `run_manifest.json`.

Task 1 is **not claim-complete for every table**. `review_required` is an intentional
quality queue, not a parser crash. The current corpus has a high proportion of difficult
financial tables (single-column extraction, generated/duplicate headers, ambiguous
merged headers, and unparsed numeric candidates). Those records must not be silently
flattened or rewritten. They remain usable for manual review and should be filtered or
weighted during retrieval evaluation.

The following are known non-blocking limitations, documented in
[`task1_failure_cases.md`](task1_failure_cases.md): chart semantic extraction, full
merged-cell reconstruction, nested-table semantics, and learned layout understanding.

## Definition of done

- [x] Parser handles native text and image-only pages with an optional OCR path.
- [x] Text and tables are emitted as different content types.
- [x] Chunks contain `doc_id`, page, section, source, and content type metadata.
- [x] Tables retain schema and diagnostics before CSV serialization.
- [x] OCR, PDF, table, and numeric warnings are categorized.
- [x] Full local corpus benchmark has `complete=true`, `coverage=1.0`, and `failed=0`.
- [x] A reproducible 30-chunk/10-table review report is generated.
- [x] Failure cases and unsupported features are documented.
- [x] Regression suite passes.
- [ ] All ambiguous tables manually corrected. This is intentionally deferred; raw values
      are preserved and the review queue is explicit.

## Handoff to Task 2

Task 2 may start using the 1,291 emitted chunks, with these safeguards:

1. preserve the chunk metadata and table identifiers in every retrieval result;
2. report whether evidence came from text or a table;
3. exclude or separately analyze `review_required` tables in the first retrieval baseline;
4. do not use the UI's demonstration metrics as research results until a retrieval
   ground-truth benchmark has been run.
