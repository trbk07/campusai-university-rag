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

Current-cycle clean-candidate command: project `.venv` Python, `PYTHONPATH` set to
exported `src`, with pytest on `test_web`, `test_web_documents`, `test_local_launcher`,
`test_ingestion_jobs`, `test_natural_conversation`, and `test_document_question_plans`.
The final export contains exactly the staged Git tree, without worktree copies;
temporary stores/indexes are isolated. See [TEST_SCENARIOS.md](TEST_SCENARIOS.md).

Earlier full-worktree regression: 2,368 PASS / 2 live SKIP. Earlier browser smoke:
39/39 PASS. These are historical checks from the preceding cycle, not new live
provider evidence or a clean-checkout full-suite result.

Mixed-PDF cycle final checks: **2,376 PASS / 2 opt-in live SKIP** in 255.80 s
on the current worktree; [JUnit evidence](docs/ui/evidence/pdf-ingestion-tests.xml).
Focused PDF/web/job checks: **52 PASS**. Clean staged Git-tree export
`00b03737bb3ff7781e1aceb519111a20ffa20382`: **106 app tests PASS** in 11.68 s.
Source/runtime hashes for the full worktree are recorded in plan.md. The full
suite includes other pending Phase 5 edits; the clean export verifies this
app commit independently. Browser smoke was not rerun in this parser cycle.

Mixed-PDF cycle final checks: **2,376 PASS / 2 opt-in live SKIP** in 255.80 s
on the current worktree; [JUnit evidence](docs/ui/evidence/pdf-ingestion-tests.xml).
Focused PDF/web/job checks: **52 PASS**. Clean staged Git-tree export
`00b03737bb3ff7781e1aceb519111a20ffa20382`: **106 app tests PASS** in 11.68 s.
Source/runtime hashes for the full worktree are recorded in plan.md. The full
suite includes other pending Phase 5 edits; the clean export verifies this
app commit independently. Browser smoke was not rerun in this parser cycle.
