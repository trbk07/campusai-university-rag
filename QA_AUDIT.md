# Full-app QA audit

## Natural100 qualification complete - QA-07b DONE

The exposed internal100-case workload now meets the three AI quality gates.
Conservative verified accuracy is95/100 (positive-only75/80=93.75%, both above90%).
Five unrecognized/strictly incomplete field contracts remain outside that lower
bound; model agreement never silently certifies them. The separate source-bound
semantic audit detects0 unsupported answers and0 unknown-support cases; context
remains15/15 with17 required fields (gate95%). No population/fresh-holdout,
independent-base-model or independent-human claim is made.

The external reviewer is Gemini3.5-flash-lite, the same base-model family as the
answer provider, called with a separate audit prompt and source/gold. Exactly5
approved POSTs cover100 cases,0 retries/key changes. HTTP bodies, raw final-text
responses, model identity, gold, original predictions and physical source chunks
are hash-bound and verified. Accuracy also requires deterministic entity/value/
unit/operator/prerequisite-direction checks; it is not solely an AI self-score.
Literal source citations are checked separately:100 valid schemas/82 citations.

The reviewer accepted the old0064 summary despite its missing active-contribution
conjunct. The deterministic required-field check catches this omission. The app
now preserves the entire single quoted award definition and re-verifies it through
normal grounding. Only0064 changes;99 public outputs retain their exact reviewed
bytes. The changed definition is proved directly from its complete literal source,
not falsely recorded as a newly model-reviewed answer. Grounding-v37 invalidates
the incomplete cached answer.793 related tests PASS; the predicate matches0/400
accepted Phase5 outputs. Their frozen acceptance remains DONE.

Original native100 had24 definite false abstentions: baseline accuracy was at
most76%, not a fabricated exact semantic score. The comparison covers the
accumulated parser/RAG repairs, not solely this final definition fix. No new
CampusAI generations were needed for this qualification. [Evidence and limits](evaluation/results/full-app-natural-20261026/quality-qualification.json).

Next:representative PDF quality, actual streaming TTFT,100-page/10MB performance,
remaining recovery/security and the final three full regression runs. Keep QA-07b
and internal Phase5 closed.

## 2026-10-26 - qualify context and repair a missing course answer

QA-07b8b1 DONE:15/15 history-bearing requests satisfy all17 reviewed required
fields (100%, gate95%). An offline evaluator checks explicit values, named roles,
prerequisite direction, bounds and omissions against unchanged gold. Exact input
history and literal source citations/document/pages are separately verified.
Unknown gold forms fail closed; no model judge or new review identity is used.
This is exposed internal dev evidence, not a fresh-holdout/general-context claim.

QA-07b8b2 DONE:0075 previously answered only NLP while the question also asks
advanced AI. A bounded2-4-course lookup requires every requested code/title and
an explicit, consistent semester column across the entire selected document.
Missing subjects, conditional values, combined identities, contradictory lower
tables, extra intents and incidental name substrings cannot produce a projection.
The real source establishes INT6146 in semester1 and INT6152 in semester2.
Final100 has53 exact captures and47 local outcomes,0 pending/new API calls;
99 public responses are unchanged,100 schemas and82 literal citations validate.
Grounding-v36 invalidates the incomplete cached answer.546 related tests PASS.
The new lookup matches0/400 accepted Phase5 requests. Whole100 semantic accuracy
and hallucination scoring remain OPEN; completeness checks must still cover
other conditions and tentative dates. [Evidence](evaluation/results/full-app-natural-20261026/context-quality.json).

The full sweep records3013 PASS/4 FAIL/2 optional live SKIP. All four failures
are Phase7 validators encountering one absolute catalog key from an earlier
archive update. QA-09c2a fixes that key to the record's existing relative identity;
the8,868,567-byte original and compressed hashes remain exact. A catalog-wide
safety/identity invariant now catches recurrence.54 affected tests PASS after
repair. This is not a new full-suite PASS or the required final three-run series.

## 2026-10-26 - close the remaining five false abstentions

QA-07b8a DONE. Source-owned lookups read the literal notice round/year and full
date/window, apply only an explicit necessary grade condition for the named award,
and resolve code/name/credits from consistent headed source rows. Unknown dates,
grade modifiers, exceptions, conflicting rows and extra intents fall back to RAG.
No presentation/grounding threshold was relaxed. Cache policy v35 bypasses old
refusals. 721 related tests PASS, including source conflicts and restart behavior.
The final same-index100 pipeline uses54 exact HTTP captures and46 local outcomes,
with0 fresh calls,0 pending,0 false abstentions and0 negative gold rows answered.
All100 public schemas and82 literal citation bindings validate. A separate
post-inference check matches changed requested fields to unchanged reviewed gold;
90 public responses are unchanged. EMA3143 uses the same literal row on page6
instead of reviewed page9; this is not a new review record. All400 accepted Phase5
requests miss these source lookups, preserving its internal acceptance. Whole100
semantic accuracy, hallucination/context scoring and final full regressions remain
OPEN. [Evidence](evaluation/results/full-app-natural-20261026/remaining-five.json).

Current cycle: 2026-10-26. Goal: autonomous full-app testing and UX optimization.
Roadmap: [plan.md](plan.md). This audit remains in progress; Phase 12 MVP acceptance
does not prove all-app AI quality or public-release performance.

Latest campaign closes QA-07b7a/b:100/100 current-index pipeline cases,0 pending.
64 exact HTTP captures and36 local outcomes run on one repaired index.56 captures
additionally prove selected-document BM25/dense bytes unchanged across global
corpus manifests; original model/config/request/body, producer identities and
artifacts stay bound and revalidated. The normal NativeCapturePool remains
whole-manifest strict.107 evidence-integrity regression tests PASS.

A separate source store preserves all baseline records/statuses and overlays
only the repaired curriculum;81 copied files were byte-verified.97 completed
cases are retained, not generated again. Three missing model responses needed4
real POSTs: one20s timeout remains journalled; a bounded new batch with configured
key_2 completes the two remaining cases. No quota reset or failed-provider row is
counted as a correct negative. All100 public schemas and79 literal citation/source
bindings validate. Five known false abstentions remain:0111/0112/0121/0128/0160;
zero negative gold cases are answered.95% is only an accuracy ceiling from these
errors, not a measured accuracy score. Full semantic, hallucination and15-case
context scoring remain OPEN. App runtime is byte-identical to the preceding
curriculum fix; no accepted Phase5 evidence or gate is reopened.
[Evidence](evaluation/results/full-app-natural-20261026/current100.json).

Earlier curriculum lookup closes QA-07b6b2 and the bounded19-case QA-07b6b.
Complete selected-document tables establish a unique literal/source-derived
course acronym, explicit credit cell and physical semester marker. Provider
lookups require a complete group with one consistent, nonempty source provider.
Lower-ranked tables participate in ambiguity checks; malformed/partial scopes,
conditions, extra intents, unknown versions and unauthorized sources do not gain
an answer. Grounding-v34 bypasses stale refusals and survives SQLite restart.
Index replacement during a lookup returns no cached/published stale projection;
the next request reads the new values.607 related tests PASS. Current19-case pipeline has14 local source outcomes and5
exact HTTP captures,0 new provider calls/outputs. All19 explicit requested fields
and document/page coordinates match the unchanged reviewed gold; every citation
quote validates.0085/0090/0092 are corrected,11 public responses are unchanged,
five already-positive cases become local and no prior positive becomes refused.
All400 accepted Phase5 requests were tested against their full selected frozen
index tables; none enters this new lookup. This does not constitute400 fresh
inferences or a new100-case accuracy/hallucination/context score. QA-07b remains
OPEN for the complete100-case qualification on a consistent index and the other
time/condition cases. [Evidence](evaluation/results/full-app-natural-20261026/curriculum-lookup.json).

Earlier routing repair closes QA-07b6b2a. A neutral/deictic reference to one
UI-selected document is not an unspecified version request. Explicit dates,
years, cohorts, versions, comparisons and applicability remain on their original
temporal path; an arbitrary named version is not stripped. Ask and retrieve
share the same selected-source condition. Natural "hoc ben" provider questions
now require the complete semester group, with grounding-v33 cache invalidation.
456 related tests PASS. Two bounded native calls return two genuine JSON outputs;
current19-case replay uses13 exact HTTP captures and6 local outcomes.0088 is
corrected with the full source group and unchanged reviewed gold coordinates;
all15 previously published responses are unchanged.0085/0090/0092 remain failing
(missing provider claim, acronym interpretation, extraneous conflicting citation).
0092 now reaches inference; this does not count as a quality pass. All400 accepted
Phase5 resolved requests retain their temporal intent and none matches the new
provider-question condition. No full400 generation or whole100 quality metric is
claimed. [Evidence](evaluation/results/full-app-natural-20261026/selected-reference.json).

Earlier citation repair closes QA-07b6b1 while QA-07b6b remains open. Semester
locators are checked separately from serial/credit values, named/code rows and
explicit semester columns stay bound, and complete provider groups cannot hide
a different source provider. Compact Semester8 labels normalize for verification
while public quotes retain original bytes. Proven selected-table locations can
explain answer wording without licensing their number as a credit count.
Subtotal wording is not a thirtieth semester. Grounding-v32 bypasses stale
refusals and persists corrected results across SQLite restart.399 related and
244 cross-phase tests PASS; these are not final full runs.

The targeted new-index campaign has19 complete cases,11 genuine JSON responses
and8 local outcomes,0 provider faults. Current reprocessing reuses exact HTTP
captures with0 fresh calls: five old false abstentions are corrected and no
previously answered row becomes a new false abstention. Repaired numeric/provider
fields and source coordinates match the unchanged reviewed gold. Four cases
remain failing (provider claim omission, FSA abbreviation, two undated-source
temporal intents), so qualification is still FAIL. Do not combine these19 with
81 old-index cases into a new whole100 metric; the last complete100 measurement
still has15 false abstentions. All400 Phase5 records were inspected for affected
conditions; five affected cases reprocess with identical public/internal outputs,
395 are outside the new conditions, and no new provider calls or reopening of
internal acceptance occurred.
[Citation evidence](evaluation/results/full-app-natural-20261026/semester-citations.json).

Earlier source repair closes QA-07b6a. Physical review of the three-page public
curriculum and an exact raw-row multiset check exposed17 dropped rows and a
subtotal mislabelled as Semester29. Producer structure-v6/table-v4 retains
111/111 rows, checks inherited-header column geometry, keeps unknown spillover
unscoped and never applies the last marker to a multi-semester table. Chunks
retain original marker/row/header provenance and close scope at a subtotal.
A full run after HTTP-fixture isolation passed2836/2 opt-in live SKIP before
the last closing-scope guard;119 related tests PASS after that guard. These
are not the three final full regressions. The HTTP test previously read the
actual data/store, making its deadline depend on workspace history; it now
uses an empty temporary library with unchanged response deadlines.

A separate index candidate updates only this one public PDF, preserving the
baseline and all14 other documents. Current code reproduces its47 stored
chunks;19/19 targeted requests retrieve an explicitly headed credit table.
QA-07b6b remains OPEN: finish semester-aware claim/citation resolution and then
collect predictions on the new index.0 new provider calls and no new answers
are claimed. The last complete natural100 quality measurement remains15 false
abstentions. Owner PDFs/jobs/live store and accepted Phase5 evidence are intact.
[Source integrity evidence](evaluation/results/full-app-natural-20261026/source-scope.json).

Earlier natural100 repair closes QA-07b5: explicit semester subtotal rows are
bound to their nearest physical marker in the same table chunk, with unknown
scope switches, wrong columns, missing values and conflicting totals rejected.
No course options are summed. Grounding-v31 avoids stale cached refusals and
the corrected result survives SQLite restart.369 related tests PASS. All100
pipeline cases are complete using69 exact-HTTP captures and31 local outcomes,
with0 new provider calls. Five false abstentions are fixed, one already-correct
answer becomes local, and94 other public outputs are unchanged. Six changed
rows match existing source-reviewed gold subtotal pairs and evidence coordinates.
There are15 definite false abstentions left (accuracy ceiling85%, not measured
accuracy); whole-app quality remains FAIL. None of400 accepted Phase5 resolved
requests matches this new subtotal intent. Reconstructing the runtime without
the new module/hook/cache namespace matches the previously verified runtime;
this is a non-interception proof, not a fresh400-case replay.
[Current evidence](evaluation/results/full-app-natural-20261026/semester-totals.json).

Earlier natural100 repair closes QA-07b4a/b/c/d: literal single-course table
lookups return explicit credit/prerequisite cells, with complete unconditional
lists and ambiguity guards. Grounding-v30 bypasses stale refusals; SQLite
restart reuse is tested. Full literal source titles use ordered folded tokens,
not the retrieval token bag.740 affected tests and217 focused tests PASS at
their recorded source versions; removing an identical duplicate test leaves
60 focused PASS on the final source. Only3 new HTTP inputs were sent, all3
published supported answers. Current100-case replay has0 pending,75 exact-input
captures and25 local paths;20 definite false abstentions remain (accuracy
ceiling80%). No known context false abstentions is not a full context score;
hallucination remains unmeasured. All400 Phase5 public/internal responses stay
unchanged on this production runtime, with no new provider calls for that
compatibility check. Whole-app AI quality remains FAIL. Next: semester/table
scope and the remaining date/condition errors. No thresholds/gold were changed.
[Current evidence](evaluation/results/full-app-natural-20261026/course-lookup.json).

Earlier natural100 inference baseline:80 positive/20 negative cases,15 with
history,10 typo cases,79 successful real JSON model outputs plus21 local paths;
79 POSTs,0 provider faults. This baseline definitely false-abstains24 positives,
so accuracy cannot exceed76%, irrespective of remaining semantic review. A
confirmed P1 truncation ended at a named article's title and omitted its next-
line predicate. Source windows now retain the complete specifically named
article, all equally named/compared clauses within budget and explicit numeric
locators.531 affected tests PASS. Only3 HTTP inputs changed:3 new real calls
produce supported answers;76 existing captures remain exact-input reusable.
That recorded100-case reprocessing has0 pending and23 definite false
abstentions (accuracy ceiling77%, context ceiling80%). Hallucination remains
unmeasured. Quality is FAIL, not accepted; next work is structured course/table
false-abstentions. No gold/review/threshold changes and no Phase5 reopening.
[Baseline](evaluation/results/full-app-natural-20261026/diagnostic-score.json),
[repair and trace bindings](evaluation/results/full-app-natural-20261026/repair.json).

Storage check: the new natural100 raw payloads are archived and hash-verified,
with only compact inputs/reports staged. The repository-wide artifact guard
still flags two pre-existing frozen reports, `phase5-mixed-absence-20261024/`
`v28-final-score.json` and `v29-final-score.json`, as full observations. Their
accepted bytes/bindings are retained unchanged; this storage-policy finding
does not reopen Phase5 quality acceptance and remains for artifact cleanup.

Natural-context repair: the existing180 owner-approved inputs include15 history
cases. Eight lost their topic before retrieval (7/15 retained); bounded whole-
utterance ellipsis detection now retains15/15, including accentless forms.
Explicit subjects still start a new topic; assistant assertions are excluded
and missing user anchors request clarification. Cache identity is versioned.
The identical public-index hybrid probe retrieves all gold pages at8 for15/15
instead of14/15; the BM25-only control stays14/15. This is page-coordinate and
request-context coverage, not model answer accuracy.16 new baseline failures,
153 focused PASS and429 affected cross-phase PASS are retained in one
[receipt](docs/ui/evidence/natural-context-20261026.json). No external inference,
gold/review changes or user-document modifications. All400 accepted Phase5
request resolutions remain identical; its internal acceptance stays closed.
Whole-app real-model quality and the final stable-source full-suite sequence
remain open. The full runs below belong to their recorded earlier source.

Accepted Phase5 source `a21a4cd5`: three consecutive full regressions each2,663 PASS/2 opt-in live SKIP. Phase5 internal400/400 acceptance and all5 gates PASS. The broader app audit remains open.

Latest hybrid-PDF cycle:2,718 full-suite PASS/2 opt-in live SKIP,126 focused
checks and43/43 browser checks. Native headers previously hid raster bodies on
the same page. Coverage-v2 now audits those regions,OCRs actual displayed pixels,
preserves native text/font signals and decoder column order,and avoids duplicate
facts. Historical cache/job identities remain readable without reusing stale
extraction. Five existing documents/268 pages were successfully reindexed in
40.65s;all native lines,7 original PDFs and prior job states were retained.
Cancelled/review-only sources were not reprocessed. The larger job history
exposed repeated path checks:20-user API p95 0.751s before batching,0.478s after,
400/400 HTTP200. Every action still validates source paths;authorization remains
per row/request. All400 Phase5 outputs remain unchanged. [Current evidence](docs/ui/evidence/hybrid-coverage-20261025.json).

Earlier web/cache cycle:2,688 full-suite PASS/2 opt-in live SKIP;43/43 browser
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
