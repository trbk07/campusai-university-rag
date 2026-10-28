# App improvement log

## 2026-10-28 - guarded streaming transport complete

Closed QA-08c1 engineering: bounded SSE reader and request-local genuine model
timing; fixed progress metadata followed by the existing verified answer.
No raw drafts/thoughts, implicit retries or cached-token timing. Default native
transport remains enabled; experimental streaming requires explicit opt-in.
346 related tests,9 JS tests,43 default and44 opt-in browser checks PASS.
Final intermediate full:3134 PASS,0 FAIL,2 opt-in live SKIP. Corrected one stale
launcher assertion; explicit enable/default disable lifecycle tests both PASS.
Live20-case cohort fails the latency gate with3 timeouts; keep QA-08c open
and preserve all observations instead of rerunning the same method.
[Receipt](docs/ui/evidence/query-streaming-20261028.json).

## 2026-10-27 - local recovery/security closed

Closed QA-09c2:reject deep JSON decoder failures as400 and untrusted loopback
Host authorities as403 before WSGI.229 related tests PASS;11 real-process
recovery receipts retained. Intermediate full3079 PASS/2 optional live SKIP is
recorded separately. Removed the slow,inaccurate raster-table OCR experiment
instead of shipping it or repeating it.
[Evidence](docs/ui/evidence/request-safety-recovery-20261027.json).

## 2026-10-27 - native100 upload-to-ready performance closed

Closed QA-03c/QA-08d:20 fresh100-page/10.24MB native uploads,all ready,p95
12.246s (gate15s),maximum14.158s. Actual offline BGE-M3 CUDA embeddings,batch8;
model startup42.513s is separate. Exact text,source bytes and372 chunk contents
in both indexes are checked each run. No app/RAG/provider output is fabricated.

Parallelize physical PDFMiner decoding for large PDFs with at most4 workers per
document; retain ordered semantic assembly,continuation headers and scope. Close
decoded page caches after extracting packets. Small PDFs use the sequential
path; unavailable workers discard partial results before a sequential retry.
35 PDFs/368 pages retain exactly the same tables.625 related tests PASS,
including real worker-boundary inheritance and partial-pool failure recovery.
Preserve internal Phase5 DONE. [Evidence](docs/ui/evidence/native100-performance-20261027.json).

## 2026-10-27 - invisible PDF layer repair complete

Closed QA-03b1. A real18-page curriculum had corrupted invisible OCR that looked
like native evidence. Ignore that layer consistently in extraction, coverage,
tables, full-source text, explicit-page questions and quote lookup. Preserve
genuine filled/stroked glyphs; force fresh OCR for affected historical caches.
Unaffected v2 caches upgrade without chunk/index rebuild, and old job identities
still validate. Raised the minimum PyMuPDF to1.25.3 for visibility metadata;
the installed/locked1.28.2 is unchanged and offline lock validation passes.

33/34 parser outputs remain exact;34 PDFs/268 pages retain original bytes.
Actual local OCR completes all18 affected pages, no source changes. Natural100
predictions remain byte-identical with0 new provider calls. Parent PDF quality
remains OPEN: page coverage and parser agreement are not verified OCR accuracy.
[Evidence](docs/ui/evidence/pdf-visibility-20261027.json).

## Natural100 AI quality gates closed

Closed QA-07b/QA-07b8 after conservative95/100 accuracy qualification,
0/100 audit-detected unsupported answers and15/15 correct context cases.
Positive-only verified accuracy is75/80=93.75%. Five unrecognized field forms
remain outside the conservative accuracy count.100 external review decisions
use exactly5 approved Gemini Free requests, with complete source/body/output
bindings and no retries. The separate model audit supplements deterministic
gold-field checks; no independent-human/base-model validation is claimed.

Closed QA-07b8b3:preserve a full quoted normative award definition instead of
omitting its final necessary conjunct. The external reviewer missed this old
omission; automated field checks found it.0064 alone changes and its new literal
definition is source-proved;99 reviewed public responses stay unchanged.
Grounding-v37 bypasses the incomplete cached answer.793 related tests PASS,
0/400 accepted Phase5 outputs match the new predicate. No new CampusAI
inference was needed. [Evidence](evaluation/results/full-app-natural-20261026/quality-qualification.json).

## 2026-10-26 - context qualification and complete course-semester lists

Closed QA-07b8b1 and QA-07b8b2. All15 context cases satisfy17 source-reviewed
required fields; context point score100% against95% gate. Wrong values/roles,
reversed prerequisites, missing fields, unknown gold and absent history cannot
pass the bounded evaluator. No LLM judge or human-review claim is fabricated.
0075 now answers both course semesters from headed source rows, replacing its
NLP-only answer. Values/codes are not hardcoded; conflicting or partial source
identities fall back.546 related tests PASS. On the final100-case pipeline only
0075 changes;53 exact captures and47 local outcomes need0 new provider calls.
All100 schemas/82 citations validate. Accepted Phase5 predicates match0/400;
its internal DONE status is preserved. Whole100 accuracy/hallucination and other
full-app gates remain open. [Evidence](evaluation/results/full-app-natural-20261026/context-quality.json).

The full sweep finds one catalog-key defect causing all4 Phase7 failures
(3013 PASS/4 FAIL/2 optional live SKIP). Closed QA-09c2a by correcting only the
logical key, preserving original registry/blob bytes and all historical report
hashes.54 affected tests PASS, including a new whole-catalog safety invariant.
The recorded full failure is retained; no final full-suite sequence is claimed.

## 2026-10-26 - close five remaining natural100 false abstentions

Closed QA-07b8a: three notice date/deadline questions, one named-award necessary
grade condition and one course name/credits lookup. Values come from selected
source fields; no benchmark input, answer constants or gate changes enter runtime.
721 related tests PASS. The final100-case pipeline has0 pending/false abstentions,
0 negative gold cases answered,100 valid public schemas and82 valid citations.
Changed requested fields match unchanged reviewed gold;90 public responses stay
unchanged.54 exact native captures and46 local outcomes require0 new API calls.
All400 accepted Phase5 requests miss the new predicates; keep internal Phase5 DONE.
Full semantic/hallucination/context scoring remains the next task, not a claimed
100% quality score. [Evidence](evaluation/results/full-app-natural-20261026/remaining-five.json).

## 2026-10-26 - complete current-index natural100 campaign

Closed QA-07b7a/b. An opt-in offline adapter proves complete selected BM25/dense
byte equality across corpus manifests, while preserving exact HTTP inputs,
model/config identity, source artifacts and default whole-manifest rejection.
107 evidence-integrity tests PASS. A separate store copies81 files exactly,
preserves baseline statuses and overlays only the repaired curriculum.
Current100 is complete with64 bound captures and36 local outcomes,0 pending.
97 completed cases are retained. Three missing responses need4 actual POSTs:
one20s timeout is preserved and a bounded key_2 batch completes the remainder.
No quota reset, changed model/payload, failed-provider negative or new gold review
record.100 public schemas and79 literal quote/source bindings validate. Five
false abstentions remain;95% is a ceiling, not measured accuracy. Full semantic,
hallucination/context metrics and final full regressions remain open. No runtime
or accepted Phase5 gate changes. [Evidence](evaluation/results/full-app-natural-20261026/current100.json).

## 2026-10-26 - complete-source curriculum field lookups

Closed QA-07b6b2 and the bounded19-case QA-07b6b. Unique course identities and
source-derived acronyms are checked against every table in the selected index,
including tables absent from retrieval. Literal credit cells and physical semester
markers establish the requested fields. Complete provider groups cannot hide
missing/mixed providers or unknown scope markers. Conditions, extra questions,
ambiguous names, unselected/unauthorized sources and malformed tables fall back
without a fabricated answer. Grounding-v34 invalidates old refusals; SQLite
restart reuse and changed-source invalidation are tested. A mid-lookup index
replacement cannot publish/cache an old snapshot; the next request recovers.
607 related tests PASS.
The19-case final pipeline has14 local source outcomes and5 exact HTTP captures,
0 new Gemini calls.0085/0090/0092 are fixed, all19 requested fields and source
document/pages match unchanged reviewed gold, quotes validate, and no prior
positive becomes refused.11 public responses are byte-equivalent; five already
positive cases become local. The new lookup matches0/400 accepted Phase5 cases.
Whole100 quality metrics and final full regressions remain open; no gate, gold
or review record is changed. [Evidence](evaluation/results/full-app-natural-20261026/curriculum-lookup.json).

## 2026-10-26 - selected-source references preserve content questions

Closed QA-07b6b2a. Neutral/deictic document references use the single UI-selected
source instead of demanding an unspecified version. Explicit temporal requests
and unknown version labels retain their original checks, shared by ask/retrieve.
Natural "hoc ben" provider questions quote the complete source semester group;
grounding-v33 invalidates older cached responses.456 related tests PASS. Two
new bounded Gemini calls succeeded. Current19-case exact-HTTP replay has13
capture uses and6 local outcomes;0088 is repaired and15 earlier public answers
are unchanged. Three false abstentions remain:0085,0090,0092. The last case now
reaches inference but its extraneous citation remains rejected. No repeated
same-prompt call, invented support, altered gold or lowered quality gate.
All400 accepted Phase5 intents are unchanged and none enters the added provider
condition; this is a bounded delta check, not400 fresh predictions or a new
whole100 metric. [Evidence](evaluation/results/full-app-natural-20261026/selected-reference.json).

## 2026-10-26 - source-bound semester citations and location wording

Closed QA-07b6b1. Bind scope, named/code row and explicit column before numeric
matching; reject missing/conflicting cells, wrong scope and partial provider
coverage. Preserve comparison scope and original quoted rows. Compact Semester8
labels match spaced verification text, while selected-source locations cannot
lend their number to a factual credit count. Subtotal30 is not semester30.
Grounding-v32 bypasses stale refusals and survives SQLite restart.399 related
and244 cross-phase tests PASS. Only11 new native calls were made for19 affected
inputs; subsequent exact-HTTP replay needs0 new calls. Five prior false
abstentions are repaired with matching old-gold fields/source coordinates,
and0 prior positive rows regress. Four targeted failures keep QA-07b6b open;
no new whole100 accuracy/hallucination/context metric is claimed. Five affected
Phase5 cases reprocess identically after screening all400;395 are outside new
conditions. Raw provider captures, benchmark reviews and thresholds are intact.
[Evidence](evaluation/results/full-app-natural-20261026/semester-citations.json).

## 2026-10-26 - preserve continuing-table columns and physical semester scope

Closed QA-07b6a. Restored17 dropped source rows (94 to111), including a course,
semester markers and subtotal rows. A subtotal29 no longer becomes Semester29.
Inherited headers require an actual prior course/credit/provider header,
matching physical column widths and recognized source rows; unknown or mixed
scopes remain unlabelled. Chunk overlap carries only real markers, retains
original row indices/header provenance and cannot extend a semester past its
subtotal. Structure-v6/table-v4 versioning refreshes stale results on next
ingest. Corrected a real HTTP test that used the owner's default library;
its empty temporary store retains the original concurrency deadlines.
One broad run passes2836/2 live SKIP before the last scope guard;119 relevant
tests pass after the guard. The separate candidate keeps14 other documents and
all baseline files unchanged; current code reproduces47 chunks and all19 scoped
retrieval probes include explicit credit headers. No new model calls, quality
acceptance, gold/review edits, owner-data reprocessing or Phase5 reopening.
QA-07b6b (claim/citation repair and model qualification) remains open.
[Evidence](evaluation/results/full-app-natural-20261026/source-scope.json).

## 2026-10-26 - physical semester subtotal lookups

Closed QA-07b5. Read explicit labelled subtotal rows only after their physical
semester marker in the same table chunk, checking intervening scope changes.
No guessed metadata scope, course-option sums or missing/conflicting values.
Quotes retain selected original marker/subtotal rows. Grounding-v31 invalidates
old refusals; SQLite restart reuse is verified. Baseline11 targeted failures
and2 scope/cache failures are repaired;369 related tests PASS. Current100-case
replay is complete with69 exact-input captures and31 local outcomes,0 new model
calls. Five false abstentions are corrected, one already-correct answer becomes
local, and94 public outcomes are unchanged. The six changed subtotal pairs and
evidence coordinates match the existing reviewed rubric. False abstentions fall
20 to15, keeping overall AI quality FAIL. New parser matches0/400 Phase5 requests;
bounded production-delta reconstruction matches its previously verified runtime.
[Evidence](evaluation/results/full-app-natural-20261026/semester-totals.json).

## 2026-10-26 - literal course cells, cache upgrade and ordered source titles

Closed QA-07b4a/b/c/d. Single-course lookups require a unique literal identity
and explicit headed source cells; retain every unconditional prerequisite and
fall back for missing/OR/conditional/conflicting cells. Three formerly refused
history questions now answer locally; one already-correct query also avoids a
model call. Grounding-v30 bypasses stale refusals and persists the corrected
answer across SQLite restart. Complete article names now match in literal word
order, preserving Vietnamese/ASCII titles without accepting a generic fragment.
Three changed HTTP inputs receive3 real supported predictions; current100-case
replay is complete with75 exact-input captures/25 local outcomes. False
abstentions fall24 baseline to20; this remains quality FAIL, not80% measured
accuracy.740 affected and217 focused tests PASS in their recorded scopes;
60 final focused tests PASS after duplicate-test cleanup. All400 Phase5
public/internal responses are unchanged on this runtime. No gold/threshold
changes, invented review or reopening of accepted Phase5 tasks.
[Evidence](evaluation/results/full-app-natural-20261026/course-lookup.json).

## 2026-10-26 - real natural100 baseline and complete named source clauses

Collected100 existing reviewed natural cases with79 real model JSON outputs,
21 local outcomes and0 provider faults.24 false abstentions make the baseline
quality FAIL. Fixed a confirmed context-window truncation:the named article's
heading survived while its next-line condition disappeared. Selection now keeps
complete explicitly named clauses, including duplicate titles/comparisons;
numbered locators take precedence.531 affected tests PASS. Exactly3 HTTP inputs
change;3 fresh predictions now publish supported answers,76 existing captures
are reused only on exact request/model/config/index/body match. Total82 actual
POSTs,100 current pipeline outcomes,0 pending.23 false abstentions remain;
accuracy/context gates stay open. No benchmark/gold/threshold changes.
[Evidence](evaluation/results/full-app-natural-20261026/repair.json).

## 2026-10-26 - retain implicit conversational subjects

Fixed eight previously reviewed follow-ups losing their user topic before
retrieval. Whole-utterance grammar recognizes omitted objects in payments,
rewards, prerequisite and programme questions; explicitly named subjects start
a new topic. No corpus names/benchmark IDs are added to runtime. User history
remains untrusted and assistant assertions cannot supply evidence. Context
cache version advances to12. Topic retention7/15 to15/15; identical-index hybrid
gold-page coverage at8 improves14/15 to15/15 (BM25 control unchanged14/15).
429 affected tests PASS; all400 accepted Phase5 request resolutions unchanged.
No external model calls; whole-app AI-quality gates remain open.
[Evidence](docs/ui/evidence/natural-context-20261026.json).

## 2026-10-25 - same-page native/raster coverage

Fixed native headers hiding raster bodies. OCR now inspects displayed regions,
retains native text/styles and decoder column order,and excludes invisible
masked pixels and duplicate facts. Coverage-v2 invalidates stale extraction
without discarding old job identities. Existing-library repair:5/5 documents,
268 pages,40.65s;all7 source PDFs and prior jobs retained,0 provider calls.
After history grew to17 jobs,repeated path validation pushed API p95 to0.751s;
request-local batching and validated scope reuse reduce it to0.478s with all400
requests successful.2,718 full-suite PASS/2 live SKIP,126 focused,43 browser
checks and400 unchanged Phase5 outputs. The known VN raster fixture scores
98.44% character accuracy;independent real-scan/table fidelity and broader goal
gates remain open. [Evidence](docs/ui/evidence/hybrid-coverage-20261025.json).

## 2026-10-25 - library read latency and loading layout

Removed repeated6MB registry parses from ordinary metadata reads using a compact,
file-identity-checked projection. Pure PDF page counts retain authorization and
readiness checks while bypassing model admission;content/composite requests
remain bounded.20-user workload:166 busy responses to0,p95 2.737s to0.189s,
all400 requests successful. Reserved initial UI geometry reduces desktop CLS
0.1022 to0.0109;9/9 lab sessions PASS.2,688 full-suite tests and43 browser checks
PASS;400 Phase5 capture-regression rows unchanged,0 fresh model calls. The warm
100-page/6.17MB probe reaches p95 11.506s over20 runs;10MB qualification and
broader goal gates remain open. [Evidence](docs/ui/evidence/web-read-performance-20261025.json).

## 2026-10-23 - clean-source reproducibility

Exporting pushed commit 0ef54f90 exposed missing runtime dependencies and an
older worker/index-builder interface. Fix commit 3a04b7f1 retains the runtime
modules in Git. Exact clean staged source passed 98 app tests in 11.49 s;
the minimal candidate previously passed 98 tests in 10.62 s. The original
import failure is retained in QA history; no live provider was called.

## 2026-10-23 - mixed PDFs and parser memory

Commit 12ed6bd9 detects unread image/vector pages, selectively OCRs physical
pages, preserves native content and rejects incomplete OCR. Four pre-fix
failures reproduced silent missing scan content. Cache/job identities and
legacy readiness are checked. Five real public PDFs (104 pages, 28,184,916
bytes) retained exact native text/layout hashes while median parser time
fell from 0.8493 to 0.1194 s and sampled peak RSS from 93,302,784 to 76,345,344
bytes. Real local OCR recovered the expected advisor text on page 2, retained
native page 1 and skipped blank page 3. See PERFORMANCE_REPORT.md for limits.
Pre-compatibility regression: 2,376 PASS / 2 live SKIP; focused 52 PASS;
clean Git source 106 app tests PASS. Receipt retained by commit 12ed6bd9.

## 2026-10-23 - preserve existing job journals

The real local restart exposed a policy-upgrade failure missed by fresh-store
tests: new job identity validation rejected valid historical journal rows.
Commit 49a0fe52 accepts only exact canonical old/current identities, retains
history and uses current identities for new work; forged identities fail closed.
Existing app recovered with two ready PDFs and five jobs. No reset/deletion or
credential change. Migration/PDF/jobs 33 PASS; whole worktree 2,378 PASS /
2 live SKIP in 254.39 s; clean Git app source 108 PASS in 12.94 s. Receipt:
docs/ui/evidence/pdf-ingestion-tests.xml.

## 2026-10-23 - manual local OCR on the web

Commit 6ce75659 adds the document-detail OCR action without a second upload.
Explicit retry preserves job history; no automatic resend. Server-owned caps
are at most 50 scan pages/120 seconds. Source hash, trusted scope, active/ready
state and queue admission are checked; client limit overrides are rejected.
Admission errors remain visible and allow manual recovery. Recognition is local.
Focused OCR/web/PDF/jobs 37 PASS; full worktree 2,384 PASS / 2 live SKIP in
258.03 s; clean Git app source 114 PASS in 11.95 s. Browser E2E 41/41 PASS,
including axe OCR dialog and real local OCR after simulated admission failure.
The new browser flow needed scoped selectors and a wait for dialog loading.

Full-app goal remains active: full upload/OCR/index load and RSS, partially
text-bearing scan pages, OCR/table fidelity and current-source native model
quality remain open. Grounding thresholds and release status are unchanged.


## 2026-10-23 - repeated batches, safe deletion and stalled chunking

Five PDFs is a per-upload limit. Two five-file batches keep ten ready/selectable sources and preserve chat; actual browser query sends all ten IDs. Added deletion on orphan/failed/cancelled and active-job cards; running work cancels at a checkpoint, with a durable deletion intent, safe index/source/cache cleanup, restart recovery and visible retry on failure. Existing answers retain their source until they finish. Fixed the non-progressing page-ending heading loop, registry reader/writer replacement race and Windows path aliases; bound ONNX threads per OCR engine. Source extraction/provenance thresholds stay unchanged.

Full offline regression: 2,399 PASS / 2 live SKIP; Phase 5: 186 PASS x3; app-focused: 54 PASS; browser: 43/43 PASS. Large-PDF before/after evidence is in PERFORMANCE_REPORT.md; two large scans remain incomplete. Candidate-r4 freezes the actual Phase 5 runtime separately from web edits, validates the existing reviewed 400 rows, and starts current-source native dev inference using the byte-identical previously authorized 207-call packet. Native qualification, calibration and final quality gates remain in progress.
