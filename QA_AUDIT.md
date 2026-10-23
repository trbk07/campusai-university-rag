# Full-app QA audit

Current cycle: 2026-10-23. Goal: autonomous full-app testing and UX optimization.
Roadmap: [plan.md](plan.md). This audit remains in progress; Phase 12 MVP acceptance
does not prove all-app AI quality or public-release performance.

| ID | Severity | Finding | Status and evidence |
|---|---|---|---|
| QA-01 | P1 | Published app cannot import on a clean checkout: `campusai.ingestion.background` and other runtime modules were absent from Git. Upload also needs the worker-compatible index-builder signature. | FIXED: runtime dependencies and matching index builder included. Exact staged Git tree `360f670b2d5b078e11afa6a27fac4f6c8300d273` exported to an isolated directory: 98/98 local app tests PASS in 11.49 s, compared with import failure before repair. |
| QA-02 | P1 validation gap | Current-source native answer quality, calibration and held-out evaluation are not qualified. Fixture answers and successful HTTP responses do not establish live answer accuracy. | OPEN; tracked by P5-08/P5-09 in plan.md. No provider requests in this QA cycle. |
| QA-03 | P2 validation gap | Full upload/OCR/index latency and peak RSS for realistic batches remain unqualified. | PARTIAL: parser-only before/after measured on five real PDFs, 104 pages/28,184,916 bytes. Median 0.8493 to 0.1194 s; sampled peak RSS 93,302,784 to 76,345,344 bytes. Exact native text/page/layout hashes unchanged. Full pipeline and OCR-table quality still OPEN. |
| QA-04 | P1 | Mixed native-text/scan PDF was marked succeeded while image-only pages disappeared from parsed content. | FIXED: detect unread image/vector pages, fail closed until OCR covers them, OCR selected physical pages and preserve native pages. Invalidate old ingestion cache/job identities; audit legacy ready sources once and block incomplete scope. 52 focused PDF/web/job tests PASS; real local OCR recovered page 2, preserved native page 1 and skipped blank page 3. |
| QA-05 | P2 | Web upload has no per-document OCR opt-in control. Scan documents correctly remain in review with OCR disabled; backend selective OCR is available. | OPEN UX work: expose bounded local OCR/reprocessing, retain existing limits and explain progress/review. No external provider calls are needed. |
| QA-06 | P1 | Coverage job-identity salt initially prevented startup against an existing journal. Fresh-store tests did not detect this upgrade failure. | FIXED: validate exact old/current canonical identity formats, retain old rows, never deduplicate new work against the old identity; reject forged identities. Migration/PDF/job checks 33 PASS. Actual local app restarted successfully with 2/2 documents ready and 5 historical jobs retained. |

Current-cycle clean-candidate command: project `.venv` Python, `PYTHONPATH` set to
exported `src`, with pytest on `test_web`, `test_web_documents`, `test_local_launcher`,
`test_ingestion_jobs`, `test_natural_conversation`, and `test_document_question_plans`.
The final export contains exactly the staged Git tree, without worktree copies;
temporary stores/indexes are isolated. See [TEST_SCENARIOS.md](TEST_SCENARIOS.md).

Earlier full-worktree regression: 2,368 PASS / 2 live SKIP. Earlier browser smoke:
39/39 PASS. These are historical checks from the preceding cycle, not new live
provider evidence or a clean-checkout full-suite result.

Current post-upgrade worktree regression: **2,378 PASS / 2 opt-in live SKIP**
in 254.39 s; [JUnit evidence](docs/ui/evidence/pdf-ingestion-tests.xml).
Focused PDF/web/jobs: 52 PASS before compatibility follow-up; migration/PDF/jobs:
33 PASS after it. Clean staged Git-tree export
`4b9e11da8779b74f20893baf959dcdc9114757e9`: **108 app tests PASS** in 12.94 s.
Current source/runtime hashes are in plan.md. Other pending Phase 5 edits are
included in the full-worktree suite; the clean export independently verifies
this app source. Browser smoke was not rerun in this parser cycle. Live local
checks confirm backend coverage fields, current UTF-8 assets, two ready PDFs and
five retained jobs. No external provider requests were made.
