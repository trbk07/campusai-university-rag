# Full-app QA audit

Current cycle: 2026-10-23. Goal: autonomous full-app testing and UX optimization.
Roadmap: [plan.md](plan.md). This audit remains in progress; Phase 12 MVP acceptance
does not prove all-app AI quality or public-release performance.

| ID | Severity | Finding | Status and evidence |
|---|---|---|---|
| QA-01 | P1 | Published app cannot import on a clean checkout: `campusai.ingestion.background` and other runtime modules were absent from Git. Upload also needs the worker-compatible index-builder signature. | FIXED: runtime dependencies and matching index builder included. Exact staged Git tree `360f670b2d5b078e11afa6a27fac4f6c8300d273` exported to an isolated directory: 98/98 local app tests PASS in 11.49 s, compared with import failure before repair. |
| QA-02 | P1 validation gap | Current-source native answer quality, calibration and held-out evaluation are not qualified. Fixture answers and successful HTTP responses do not establish live answer accuracy. | OPEN; tracked by P5-08/P5-09 in plan.md. No provider requests in this QA cycle. |
| QA-03 | P2 validation gap | Latest five-PDF throughput measurement uses tiny one-page fixtures; large/scanned/table/multicolumn PDFs and peak RSS need a comparable measured workload. | OPEN; preserve existing PDF regression evidence and measure actual bottlenecks before further optimization. |

Current-cycle clean-candidate command: project `.venv` Python, `PYTHONPATH` set to
exported `src`, with pytest on `test_web`, `test_web_documents`, `test_local_launcher`,
`test_ingestion_jobs`, `test_natural_conversation`, and `test_document_question_plans`.
The final export contains exactly the staged Git tree, without worktree copies;
temporary stores/indexes are isolated. See [TEST_SCENARIOS.md](TEST_SCENARIOS.md).

Earlier full-worktree regression: 2,368 PASS / 2 live SKIP. Earlier browser smoke:
39/39 PASS. These are historical checks from the preceding cycle, not new live
provider evidence or a clean-checkout full-suite result.
