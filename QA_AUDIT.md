# Full-app QA audit

Current cycle: 2026-10-25. Goal: autonomous full-app testing and UX optimization.
Roadmap: [plan.md](plan.md). This audit remains in progress; Phase 12 MVP acceptance
does not prove all-app AI quality or public-release performance.

Accepted Phase5 source `a21a4cd5`: three consecutive full regressions each2,663 PASS/2 opt-in live SKIP. Phase5 internal400/400 acceptance and all5 gates PASS. The broader app audit remains open.

Latest web/cache cycle:2,688 full-suite PASS/2 opt-in live SKIP;43/43 browser
checks PASS, including desktop/mobile, ten PDFs, deletion and local OCR recovery.
Fixed repeated full-registry parsing and expensive-query admission for pure PDF
metadata.20 concurrent users now receive400/400 HTTP200, p95 0.189s; before,
166/400 requests returned429 and p95 was2.737s. Existing scopes, deletion intents,
registry corruption handling and model-query bounds remain tested. Fixed loading
layout shifts:CLS0.1022 to0.0109, nine lab sessions PASS. All400 Phase5 outputs
remain exactly unchanged using bound native HTTP captures,0 fresh provider calls.
The100-page probe is6.17MB, not the full10MB target; whole-app completion stays
unproven. [Measured evidence](docs/ui/evidence/web-read-performance-20261025.json).
Historical browser source `3fcd4a46`:
43/43 browser checks PASS on Chrome155, including two batches of five PDFs,
deletion, six viewports, accessibility and actual local OCR recovery. The browser
uses a deterministic test provider; it does not measure live AI quality.
[Current browser evidence](docs/ui/evidence/phase5-v27-20261024/browser-results.json).
The parser inventory covers34 distinct PDFs with physical page counts/sequences
preserved. Its0.542-second parser-only measurement is not full ingestion latency
or independent extraction/OCR accuracy.
[PDF inventory](docs/ui/evidence/phase5-v27-20261024/pdf-parser.json).

Twenty simultaneous read workers exposed a P2 transport-capacity issue:197/200
requests succeeded, two returned503 and one connection failed; p95 was525ms.
The baseline loopback HTTP server limited active handlers and its backlog to8.
This is a failed load check, measured alongside native qualification/regression,
not a controlled SLO result. The transport fix and controlled read remeasurement
are complete below; historical inference sources are retained.
[Load evidence](docs/ui/evidence/phase5-v27-20261024/read-concurrency.json).

Transport candidate [d2d3626](https://github.com/trbk07/Adaptive-RAG-for-Financial-Business-Reports/commit/d2d3626)
is prepared on `fix/local-http-capacity`, separate from the frozen inference
source. It raises bounded HTTP admission/backlog to32 while keeping the app's
query/ingestion limits. Forty-eight web/recovery tests PASS. In three interleaved
measurements with explicitly fresh empty stores, the8-handler baseline rejected
318/600 reads; the candidate served600/600, p95 40.9-42.2ms per run. This proves
read admission, not20 simultaneous model generations or a production SLO.
[Before/after evidence](docs/ui/evidence/phase5-v27-20261024/http-capacity-before-after.json).
The preliminary measurement without an explicit store binding is invalid for
comparison and retained with that label. Initial isolated-candidate missing-bundle
failures are retained. The transport fix is integrated as `af75a6f2` and the final
producer a21a4cd5 passes3 complete regression suites. Phase5 internal qualification
is now PASS400/400; this does not certify unmeasured full-app SLOs.

| ID | Severity | Finding | Status and evidence |
|---|---|---|---|
| QA-01 | P1 | Published app cannot import on a clean checkout: `campusai.ingestion.background` and other runtime modules were absent from Git. Upload also needs the worker-compatible index-builder signature. | FIXED: runtime dependencies and matching index builder included. Exact staged Git tree `360f670b2d5b078e11afa6a27fac4f6c8300d273` exported to an isolated directory: 98/98 local app tests PASS in 11.49 s, compared with import failure before repair. |
| QA-02 | P1 validation gap | Current-source native answer quality, calibration and held-out evaluation are not qualified. Fixture answers and successful HTTP responses do not establish live answer accuracy. | DONE for internal Phase5:400/400 physically recomputed, all5 gates PASS;159 real new JSON responses/241 POST starts in the completion cycle. Public fresh-holdout acceptance stays separate. See phase5-closure.json. |
| QA-03 | P2 validation gap | Full upload/OCR/index latency and peak RSS for realistic batches remain unqualified. | PARTIAL: parser-only before/after measured on five real PDFs, 104 pages/28,184,916 bytes. Median 0.8493 to 0.1194 s; sampled peak RSS 93,302,784 to 76,345,344 bytes. Exact native text/page/layout hashes unchanged. Full pipeline and OCR-table quality still OPEN. |
| QA-04 | P1 | Mixed native-text/scan PDF was marked succeeded while image-only pages disappeared from parsed content. | FIXED: detect unread image/vector pages, fail closed until OCR covers them, OCR selected physical pages and preserve native pages. Invalidate old ingestion cache/job identities; audit legacy ready sources once and block incomplete scope. 52 focused PDF/web/job tests PASS; real local OCR recovered page 2, preserved native page 1 and skipped blank page 3. |
| QA-05 | P2 | Web upload previously had no per-document OCR/reprocessing control. | FIXED: detail-dialog local OCR action; bounded server-side page/time limits; source-hash and authorization checks; manual retry retains history and needs no reupload. Focused 37 PASS; actual local OCR through browser with admission-error recovery and accessibility PASS. |
| QA-06 | P1 | Coverage job-identity salt initially prevented startup against an existing journal. Fresh-store tests did not detect this upgrade failure. | FIXED: validate exact old/current canonical identity formats, retain old rows, never deduplicate new work against the old identity; reject forged identities. Migration/PDF/job checks 33 PASS. Actual local app restarted successfully with 2/2 documents ready and 5 historical jobs retained. |
| QA-10 | P2 | Cancelling OCR still recognized remaining physical pages; progress stayed fixed during OCR and could move backwards afterwards. | DONE:page callbacks check cancellation and report completed pages; job updates retain the highest progress under the existing lock. Before:2 reproducible failures. After:30 focused tests and2,665 full-suite tests PASS,2 opt-in live SKIP. Evidence:docs/ui/evidence/ocr-evaluation-20261025.json and ocr-regression-20261025.xml. |
| QA-11 | P1 | Large scans exhausted RapidOCR's120s budget; its dictionary cannot preserve Vietnamese tones. A process-wide OCR thread limit also slowed embeddings. | DONE for bounded processing. Pinned Vietnamese/English Tesseract runs in a separate process with cancellation/deadline and no parent OpenMP changes.5/5 real PDFs ready,0 job failures;68 focused and2,681 full-suite tests PASS. The final persistence/index handoff is also monotonic. Known six-layout accuracy97.54%. CPU full indexing remains255.41s and independent real-scan/table quality stays OPEN in QA-03/07/08. Evidence:docs/ui/evidence/ocr-isolation-20261025.json. |

Current-cycle clean-candidate command: project `.venv` Python, `PYTHONPATH` set to
exported `src`, with pytest on `test_web`, `test_web_documents`, `test_local_launcher`,
`test_ingestion_jobs`, `test_natural_conversation`, and `test_document_question_plans`.
The final export contains exactly the staged Git tree, without worktree copies;
temporary stores/indexes are isolated. See [TEST_SCENARIOS.md](TEST_SCENARIOS.md).

Earlier full-worktree regression: 2,368 PASS / 2 live SKIP. Earlier browser smoke:
39/39 PASS. These are historical checks from the preceding cycle, not new live
provider evidence or a clean-checkout full-suite result.

Current local-OCR UI cycle: **2,384 PASS / 2 opt-in live SKIP** in 258.03 s;
[JUnit evidence](docs/ui/evidence/ocr-ui-tests.xml). Focused OCR/web/PDF/jobs:
37 PASS. Clean staged Git tree `d4fa931f219a8b47423474e9a10003fb55089917`:
**114 app tests PASS** in 11.95 s. Current source/runtime hashes are in plan.md.
Other pending Phase 5 edits are included in the full-worktree suite; the clean
export independently verifies this app source. Browser E2E: **41/41 PASS**, six
viewports, no script errors, including real local OCR and a simulated admission
failure followed by manual recovery. [Browser evidence](docs/ui/evidence/ocr-browser-results.json).
No external provider requests were made. Full-pipeline load/OCR-table accuracy
and current-source native answer quality remain open; the full-app goal is active.


2026-10-23 current-source checkpoint: full offline suite **2,399 PASS / 2 live SKIP** (516.42 s); Phase 5 suite **186 PASS x3** in frozen candidate-r4. Source/runtime identity and native qualification progress are in plan.md. Browser batch/delete smoke: 43/43 PASS, six viewports, no script errors.

Additional repaired findings: shared registry read/write leases prevent Windows atomic-replacement races (five concurrency/path cases); bounded ONNX thread pools avoid multiplying OCR workers; failed/cancelled/unregistered and active uploads can be deleted with durable intents and deferred safe cleanup; a numbered heading followed by ordinary text previously looped forever in chunking (isolated two-second timeout reproduced; two progress regressions now PASS). Two batches of five preserve ten selectable PDFs and the conversation. A natural Vietnamese selected-document page-count query now routes to trusted metadata.

The full five-PDF/104-page BGE/OCR run is measured, not passed: both versions ready only 3/5 documents; two large scans still exceed the OCR budget. Phase5 internal acceptance is complete; whole-app AI accuracy/OCR/streaming/concurrency acceptance remains open.

2026-10-25 OCR investigation:changing ONNX threads1 to2 gave an early first-page gain but did not improve the actual five-PDF outcome:3/5 ready,202.32 versus206.91 seconds. The default character dictionary lacks Vietnamese tone characters; swapping to two newer official recognition models still lacks required characters. Neither model nor thread settings were deployed. An isolated Tesseract5.5.3/vie+eng candidate improved character accuracy on one known clean image from57.83% to90.34%; this is preliminary synthetic evidence, not independent real-scan qualification. A process-wide OMP_THREAD_LIMIT=1 experiment also slowed BGE indexing and was stopped; that setting is rejected. No user PDFs were transmitted or production defaults changed.

The isolated Tesseract candidate subsequently returned nonempty text for73/73 selected physical scan pages across35/32/6-page PDFs in27.26 seconds with3 workers. This establishes bounded OCR completion and page coverage only; real-scan accuracy, table fidelity and full upload/index latency remain OPEN. Raw measurements, asset hashes, character dictionaries and reproduction sources are consolidated in[ocr-evaluation-20261025.json](docs/ui/evidence/ocr-evaluation-20261025.json). Generated experiment stores were removed; original PDFs, historical raw test reports and the Phase5 accepted snapshot are retained.

Post-repair Phase5 regression:400/400 exact-input pipeline outcomes match every accepted output/evidence row,0 pending and0 fresh HTTP calls. Prediction artifact SHA256 remains`1afe33c603c724783f411360b44308a2adea84849a39144056b08e71362e62e0`. This is behavior regression evidence for the changed app; the accepted frozen producer and release report remain unchanged.
