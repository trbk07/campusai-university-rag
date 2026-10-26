# App test scenarios

Latest cycle:2026-10-26. See [QA_AUDIT.md](QA_AUDIT.md) for open findings.

Actual natural100:80 positives,20 negatives,15 contextual and10 typo cases from
the existing owner-approved dataset. No gold/labels enter inference. Baseline
completes100 pipeline cases using79 real model outputs/POSTs and21 local paths.
Named-article source-window tests reproduce loss of the predicate after its
title; retain comparisons, duplicate titles and explicit article precedence.
The final531-test affected suite PASS includes grounding, citation, arithmetic,
temporal, multi-hop and relation checks. Only3 changed prompts need fresh
inference; all3 return supported answers. The current100-case checkpoint uses
76 unchanged real captures plus these3, with21 local paths and0 pending. These
are genuine captured responses, not79 new generations on the final source.
Quality still FAIL:23 definite false abstentions; the repair does not establish
the remaining answers' correctness or hallucination rate.
[Evidence](evaluation/results/full-app-natural-20261026/repair.json).

Natural-context cycle:429 affected tests PASS across request completeness, API,
Phase7 candidate generation, source-course generation, relations, multi-hop,
temporal and routing.16 accented/accentless ellipsis cases check user-only
topic inheritance, clarification without a user anchor and selected-text
handling;8 explicit-subject cases prevent previous-topic contamination.
All15 existing owner-approved history cases retain their topic; actual hybrid
retrieval reaches all reviewed pages at8 in15/15. No model was called, so these
checks do not close real-model accuracy or context gates. Baseline/results and
physical inputs are bound in [one receipt](docs/ui/evidence/natural-context-20261026.json).

Previous hybrid-cycle source:2,718 full-suite PASS/2 opt-in live SKIP,126 focused checks,
43/43 browser checks and400 unchanged Phase5 capture-regression rows.
`tests/test_hybrid_pdf.py` covers native headers with raster bodies,known
Vietnamese/English text,both OCR backends,masked/clipped images,decoder column
order,duplicate regions,cache upgrades and manual OCR/index/search without
reupload. `tests/test_tesseract_process.py` also checks layout integrity and
deadline/cancellation when a worker never reads a large input. Metadata tests
verify scoped validation and fresh authorization/source checks across requests.
One browser failure was a mid-hashchange visibility assertion:the original
answer node/hash remained present and became visible after navigation. The
harness now awaits that transition before checking conversation preservation.
[Current evidence](docs/ui/evidence/hybrid-coverage-20261025.json).

Earlier cache cycle:2,688 full-suite PASS/2 opt-in live SKIP;43/43 browser checks.
`tests/test_metadata_read_path.py` verifies busy-model admission versus local
facts,scope isolation,no repeated full-content parses,same-size atomic file
replacement,deletion,caller mutation and fail-closed corruption. Registry/HTTP
concurrency checks also PASS. Reproduce the non-model400-request workload with
`python -m scripts.operations.benchmark_metadata_reads --output <new-report.json>`.
Use `node tests/ui/measure_web_vitals.cjs` with a new `UI_VITALS_OUTPUT` for the
read-only layout probe. Exact400-row Phase5 capture regression is unchanged;
this is reuse of real responses,not new inference. Current evidence and limits:
[performance receipt](docs/ui/evidence/web-read-performance-20261025.json).

The following scenario table records earlier coverage;its source-specific
counts do not replace current measurements.

| Flow | Expected behavior | Evidence |
|---|---|---|
| Clean startup | Source archive imports app and local launcher without local-only modules. | Initial archive fails; repaired candidate covered by 98-test clean-source run. |
| Upload lifecycle | Real PDF upload, worker/index readiness, duplicate validation, retry, source/feedback/delete/re-upload and five concurrent uploads remain consistent. | `tests/test_web_documents.py`, `tests/test_ingestion_jobs.py`; clean candidate PASS. |
| Parallel queries | Four independent EN/VI requests retain their own response content and request ID. | `tests/test_web.py`; clean candidate PASS. |
| Natural phrasing | Accents/no accents, page-count variants, real follow-up versus topic change, ambiguous multi-document scope and injection checks. | `tests/test_natural_conversation.py`; clean candidate PASS. Its 100-turn check is structural PDF metadata, not 100 verified live model answers. |
| Page/multiple intents | Exact physical page/range, invalid pages and page-count plus content question preserve scope and both intents. | `tests/test_document_question_plans.py`; clean candidate PASS with deterministic local provider. |
| UI end to end | Six-file rejection, five uploads until ready, chat/citations/source/delete, mobile/desktop and accessibility. | Prior 39/39 browser smoke documented in `docs/ui/phase12-ui.md`; not rerun in this packaging cycle. |
| Live AI quality | Verify correctness, completeness, groundedness, naturalness and hallucination against reviewed source/gold. | OPEN: whole-app natural/multi-turn evaluation; Phase5 internal qualification is already DONE. |
| Large/scan PDF load | Verify extraction/table/OCR and latency/RSS under five realistic PDFs plus query load. | OPEN for current app performance cycle; unit PDF regressions alone do not prove this workload. |
| Mixed text/scan and legacy cache | Preserve native text and physical pages; never mark partial extraction ready; detect old incomplete success flags. OCR budget applies only to selected pages. | `tests/test_mixed_pdf.py`; 8 tests PASS, included in the 52-test focused PDF/web/jobs run. Real local OCR of page 2 independently verified. |
| Real-PDF parser RSS | Compare identical input hashes and preserve exact native text/layout while reducing image-buffer overhead. | Three fresh-process runs per version, five PDFs/104 pages; `docs/ui/evidence/pdf-parser-batch.json`. Parser scope only. |
| Upgrade existing job ledger | Prior identity rows remain readable; new work gets the new identity; fabricated legacy identity still fails closed. | `tests/test_job_identity_migration.py`; 33-test migration/PDF/jobs group PASS; actual existing local journal startup verified. |
| Clean app after compatibility upgrade | No missing runtime modules; mixed-PDF/legacy-ledger behavior works from Git source alone. | Tree `4b9e11da8779b74f20893baf959dcdc9114757e9`, clean exported source: 108/108 app tests PASS; final whole-worktree suite 2,378 PASS / 2 live SKIP. |
| Clean app after compatibility upgrade | No missing runtime modules; mixed-PDF/legacy-ledger behavior works from Git source alone. | Tree `4b9e11da8779b74f20893baf959dcdc9114757e9`, clean exported source: 108/108 app tests PASS; final whole-worktree suite 2,378 PASS / 2 live SKIP. |

All current-cycle API/worker scenarios use isolated local test stores and no
external provider. Existing production/user documents must not be deleted.

Local OCR web cycle: `tests/test_web_ocr.py` adds six cases for source hash,
authorization, busy/ready documents, server-owned limits, queue capacity and
manual retry with preserved history. Focused OCR/web/PDF/jobs: 37 PASS. Clean
Git tree `d4fa931f219a8b47423474e9a10003fb55089917`: 114 app tests PASS; full
worktree 2,384 PASS / 2 live SKIP. Browser E2E 41/41 PASS includes axe OCR dialog
and actual local OCR/recovery without reupload. Six established responsive
viewports remain covered; the OCR action itself was exercised at desktop size.


2026-10-23 batch/delete/chunking cycle: two concurrent five-file batches accumulate ten ready sources; all ten can be queried in one conversation. Twenty consecutive integration repetitions accepted/indexed 200 PDFs. Browser smoke has 43 PASS checks, including second-batch conversation preservation and deletion of a failed upload without a registry record. `tests/test_web_deletions.py` covers active parsing/index publication, queued work behind another PDF, authorized scope, failed/cancelled uploads, durable recovery, failure/retry, reupload and an in-flight answer. `tests/test_chunker_progress.py` bounds formerly infinite heading-continuation cases with child-process deadlines. Current app group: 54 PASS; full worktree: 2,399 PASS / 2 live SKIP; frozen Phase 5 group: 186 PASS on each of three consecutive runs.
