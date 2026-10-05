# Reranker implementation and release status

The optional retrieval reranker remains disabled by default. Production
activation requires a complete passing release manifest bound to installed
runtime code, model snapshot, index, device and calibration.

The implementation now includes sequential M0–M12 validation, role-declared
human benchmark review (project owner or independent reviewer), explainable dev-only routing, a five-cap
calibration sweep, paired generated/human test and holdout comparisons,
performance/capacity measurement, adversarial and grounding checks, controlled
failure injection, rollback across separate processes, and staging telemetry
auditing. Follow [the release runbook](reranker_release_runbook.md).

## Current release and dev research (r18, 2026-10-04)

The active selector points to `phase7-release-20261004-r18`. M0/M1/S1 PASS,
M2 FAIL: human-test hard all-gold coverage@40 is 26/28, below 95%. The active
release has 3/19 passing gates and no final score. Its test/holdout are consumed.

Subsequent dev-only changes fix query-operation grammar, prioritize full course
names in normal fast lookup, and require local grade-rule source relationships.
On the audited 491-row exposed-dev probe, actual GPU cap-10 v1 probability
calibration retains Recall@5 309/315 and FPR 1/176 in fitted and grouped OOF;
routing hard recall is 124/126 and easy unnecessary rate 15/168. All 150 model
calls completed without inference errors; rerank p95 is 163.18 ms. This is
conditional feasibility, not an official M4/M5 result or M6 uplift.

Final full suite: 763 passed, two opt-in live tests skipped, coverage 89.51%. Exact
raw outputs, source snapshot, provenance, reproduction and test evidence are
in [the dev archive](../../evaluation/results/phase7-dev-feasibility-20261004/README.md).
The frozen r18 benchmark/report/locks remain unchanged. Next is independently
eligible source-fact coverage and a fresh release freeze; see
[plan.md](../../plan.md#phase-7-joint-dev-feasibility--2026-10-04).

## Historical candidate (r17/r11, 2026-10-03)

The active selector is [phase7_release_cycle.json](../../configs/phase7_release_cycle.json);
the authoritative roadmap is [plan.md](../../plan.md#phase-7--reranker).
M0–M4 and S1–S2 passed at source commit 618a6ef. Their receipts predate the
current evaluation edits, so they cannot qualify the current source unchanged.
M5 remains unsuccessful: primary dev Recall@5 is 96.23%, but negative FPR is
3.77%, above the 1% limit, and only two primary no-evidence examples are scored.

The completed auxiliary integrity task checks every decoded source body,
reconstructs owner-authorized AI records, keeps shared templates in connected
groups, and restricts auxiliary loading to explicit exploratory calibration.
The release workflow and validator retain their existing benchmark criteria.
Corrected cap-8 measurement scored 85 requests (evidence classes 6/14/65);
combined and OOF FPR are 10.53%, so it is not release evidence. Related checks:
80 passed. Failed trials, actual source bytes and hashes are retained in
[the task archive](../../evaluation/results/phase7-source-context-20261003-r17/dev_auxiliary_integrity_task/task_summary.json).
Runtime schema changes are awaiting specific permission following automatic
approval review. No M6/M7 run has started on this candidate.

## Completed dev evidence task (r12, 2026-10-03)

This historical cycle was `phase7-dev-extension-20261003-r12`. Thirteen dev-only
absent-field questions reuse course facts already mentioned in parent dev.
Every absence proof binds all scoped curriculum body chunks; authorization
keeps AI origin explicit. The 60 test and 60 holdout records are unchanged;
no new heldout or independent review claim is made. M1/S1 freeze and lineage
validation PASS. The dev split now has 193 records.

Initial actual cap-8 inference scored 82 requests: evidence classes 11/9/62,
Recall@5 0.96296, fitted FPR 0.17241 and OOF FPR 0.18966, with no inference
errors. Hash round-robin had placed both rare negative families in one fold.
Deterministic class-balanced allocation retains whole connected groups and
uses labels only for stratification. Replay reaches Recall@5 0.96296 and FPR
0 in both OOF and fitted policy. This is not a fresh inference run or M5 PASS.
Final-source M2 fails the fact stratum (0.93939) despite aggregate holdout
Recall@40 0.98291. The actual failed report is archived. Source/table decoding
must be repaired and measured in a successor cycle before M3/S2, M4 and the
full five-cap M5 sweep.

Offline verification: **687 passed, 2 skipped, coverage 89.31%**. The two opt-in
live integration tests separately passed on the new Gemini model. All failed
and passing dev attempts, actual receipts, JUnit and coverage are retained in
[the task archive](../../evaluation/results/phase7-dev-extension-20261003-r12/dev_extension_task_summary.json).

## Completed source/routing task after r10 (2026-10-03)

The completed large task repairs query-operation routing and source retrieval, and
completes the M6 collection/review sequence and M7/S6 measurement orchestration.
The final dev-only operation router produced hard recall 0.96552 and easy unnecessary
rate 0.125 with grouped out-of-fold validation and a source-stable receipt. This is an exploratory fit;
M4 has not passed and its held-out evaluation has not started.

Source-body BM25, course-heading priority, actual semester table rows, bilingual
academic aliases and source-scope absence checks improved exploratory dev
Recall@5 from 0.76296 to 0.95556. That run still has negative FPR 0.08889;
subsequent personal-grade and negated-subject fixes are being calibrated.
No benchmark gold or held-out data were changed. Latest offline verification:
655 passed, 2 skipped, coverage 89.31%. An exploratory score calibration reached
Recall@5 0.96296 but was rejected because it scored only four no-evidence examples
(at least five per class are required). The next task adds source-checked dev
coverage for evidence calibration. Raw reports, JUnit, coverage and the route
receipt are preserved in the
[task summary](../../evaluation/results/phase7-source-routing-task-20261003-r11/task_summary.json).
The r10 reports below bind commit `7529608`; changed
source must be measured again before release.

The owner authorized switching Gemini models and supplied the corrected local
key. The explicit new `api_key` assignment was normalized locally. Actual model
inventory/probes selected `gemini-3-flash-preview` with HTTP 200; both concrete
client integration tests passed (citation and cache contract). This is not an
uncached M6 quality run. The default config/client and live tests now use the
selected model; those changes are included in the dev evidence task. Credentials are
never included in reports or Git. See
[provider evidence r12](../../evaluation/results/phase7-dev-extension-20261003-r12/provider_switch_verification.json).

## Committed evidence (dev metadata cycle r10, 2026-10-03)

The historical cycle `phase7-dev-metadata-20261003-r10` uses matching benchmark
and result directories. M0–M3 and S1–S2 were measured again and PASS on the
source at commit `7529608`. The completed task fixes missing-topic clarification and longer
contextual followups, and corrects 14 dev difficulty labels inherited from the
legacy `serial % 3` generator. Every correction is replayed against actual
scoped table rows. Original owner input bytes, legacy labels and the previous
dev allocation remain hash-bound. Questions, gold evidence and document scopes
are unchanged; test/holdout bytes and exposure history are preserved. No new
heldout or independent review claim is made.

Full offline verification: **596 passed, 2 skipped, 89.32% coverage**. The two
skips require live Gemini integration. Both new live calls failed with provider
quota HTTP 429 and are retained as failures. S2 uses the concrete Gemini client
with its normal cache permitted; it is not an uncached answer-quality run.
M4 still has no feasible grouped dev fit; no route freeze or M4 heldout run has
been created. Later gates remain outstanding. See the
[active readiness report](../../evaluation/results/phase7-dev-metadata-20261003-r10/readiness.json).

## Historical candidate cycle r9

The owner explicitly approved all existing inputs, authorized creation of missing
questions and requested author attribution to **Trương Bảo Kiên**. The current
cycle is `data/benchmark/phase7_review_cycles/phase7-owner-20261003-r8`, with results
in `evaluation/results/phase7-candidate-20261003-r9`. The unchanged r8 frozen
benchmark is reused; r9 does not claim a fresh held-out bank.

M0, M1, M2 and S1 now PASS. The benchmark contains 180 owner-authored historical
questions in dev and 120 new source-checked AI questions commissioned and approved
by the owner: 60 test and 60 holdout, with 15 disjoint source-fact groups in each.
The report explicitly declares `personal_owner_source_checked_ai`, 180 human / 120
AI records and `independent_review_complete=false`. This is the owner's personal
acceptance profile. It does not establish independent human benchmark validity.

All 180 historical questions have proven prior candidate-coverage exposure. Their
exact original split bytes, question IDs and physical index were matched against
the archived prior report. They remain dev-only. The new source bank binds actual
table rows, credit headers, course codes, pages/chunks, arithmetic and absent-course
negatives. A pre-generation history snapshot and explicit owner chat authorization
are hash-bound; no old exposure is relabelled as unexposed.

The large task resolving owner approval, exposure, fresh data and M1/S1 is complete.
The failed r8 candidate run is retained. Dev-driven fixes cover contextual filler
words, program/semester routing, spaced course codes, table-row links and corpus-bound
typos. The r9 GPU candidate measurement passes with test/holdout Recall@40 and
all-gold recall of 1.0. Candidate generation retains scope and provenance guards,
and uses its own cache key independently of final answer acceptance thresholds.

Latest full offline verification: **548 passed, 2 skipped, 89.29% coverage**.
Both real Gemini integration tests passed separately. Two full live-suite attempts
each had one provider HTTP 503 failure; neither is reported as a passing full run.
The ignored local key file `configs/gemini.yaml` is loaded only into process
environment by `scripts.operations.with_gemini_key`.

M3 and S2 now PASS in the authoritative GPU validator. S2 records actual cold
rejection, one startup load, three request inferences with no model reload,
closed admission, drain counters and exact Phase 6 fallback after a missing snapshot.
Context cases use physical dev indexes and live Gemini grounding; empty scope,
missing history and unverified selection are measured through actual abstention.
Raw observations and failed attempts are preserved by content hash. Cache inputs,
citation counts and lifecycle counters are recomputed by the validator.
M4–M12 and S3–S6 remain outstanding; no final 10/10 score has been issued.

## Historical evidence before owner cycle r8

Latest full-suite verification: **480 passed, 0 failed, 2 live LLM tests skipped;
89.28% coverage**. Compile, tracked-file secret scan, `git diff --check`, and the
Phase 7 focused regression suites pass. See the
[02/10/2026 implementation audit](phase7_audit_20261002.md) and
[current code verification](../../evaluation/results/phase7_code_verification_20261003_r5.json),
[readiness report](../../evaluation/results/phase7_readiness_20261003_r5.json) and
[task ledger](../../evaluation/results/phase7_task_ledger.json) for current scope.
All supplemental gates S1–S6 participate in validation and production activation.

| Gate | Current release evidence |
|---|---|
| M0 baseline | Historical RC3 and two frozen reruns preserved in `evaluation/results/retrieval_baseline_*` |
| M1 human benchmark | FAIL: the legacy 180-row approvals lack valid roles/current policy binding; negative scope and exposure history remain unresolved |
| M2–M12 | Cannot advance until preceding gates PASS; code and unit fixtures do not replace measured artifacts |
| S1 | FAIL: synthetic legacy review/exposure observations are rejected; owner decisions and an audited exposure registry are missing |
| S2 | PASS: current context/lifecycle evidence recomputes successfully |
| S3–S6 | BLOCKED: actual frozen statistics, reviewed paired outputs and deployment observations are missing |

The owner selected local RTX 4060 acceptance first; public acceptance follows later.
The normalized 180-question staging pool retains the original author's bytes. Its
89 confirmed prior-dev exposures, 91 unresolved histories and 45 missing negative
scopes are recorded explicitly. Team consensus is documented in an
[confirmation approved by Trương Bảo Kiên](../benchmarks/human_review_confirmation.draft.md); it does not
constitute per-record approval. On 2026-10-03 the owner allowed self-review for this
personal project. The policy accepts `project_owner` and `independent_reviewer`, and
does not describe owner decisions as independent. A previous lineage generator wrote
synthetic approval/exposure fields; its old outputs are not release evidence and the
generator now requires an explicit intake audit and recomputes S1 against the
current exposure registry. The release entry point supports a read-only
`preflight` and delegates ordered stages to the authoritative workflow.

M1 resume now reads the configured owner self-review policy automatically,
checks audit coverage/content before freeze, and assembles S1 before the final
M1 validation. The input diagnostic lists per-qid failures and the safe split
proposal. With current evidence, all 180 records remain dev-only; independent
test/holdout coverage cannot be claimed. See
[current input gaps](../../evaluation/results/phase7_review_inputs_20261003_r6.json).

The current owner-review dossier is
[phase7-release-20261003-r3](../benchmarks/phase7_review_cycles/phase7-release-20261003-r3/phase7_review_questions.draft.md),
with hash-bound PDF/BM25 evidence, unchanged questions/context/gold, pending per-record
decisions and a scope proposal for the 45 negatives. The owner must decide each record
and document the 91 unresolved exposure histories before F0/F1. Preparation created
no approvals, exposure decisions, splits or release evidence.

The real offline BGE FP16 startup/sharing/shutdown probe passed on RTX 4060:
zero cold-request model loads, one shared model, repeated score delta zero, and
no reranker model retained after the last provider closes. Raw observations are
in [the verified lifecycle probe](../../evaluation/results/phase7_startup_lifecycle_verified.json).
This dev diagnostic is not an M3/M7 release measurement.

The earlier generated-only exploration achieved candidate Recall@40 `1.0`
on test and `0.991453` on holdout, with no scope/provenance/duplicate errors.
Its route selected 89.3% of easy queries and CPU rerank p95 was roughly 10.8s.
Those historical exploratory observations do not satisfy the new release
contract and were not promoted into passing release evidence.

## Continuation measurements (2026-10-02)

The local RTX 4060 Laptop GPU (8 GB) is now available through the separate
`.tmp/phase7-gpu-runtime`, with PyTorch `2.14.0+cu126` (`reranker-gpu-runtime`
was the historical directory label). The CPU `.venv` was
preserved. A real offline snapshot probe produced identical repeated scores
(`max_score_delta=0`); it remains conditional exploratory evidence.

The latest real-corpus diagnostic used three hard **dev** questions and their
actual frozen Phase 6 candidates. GPU rerank-only latency was 229-345 ms at
cap 8, 243-398 ms at cap 10, and 288-487 ms at cap 20. Peak GPU allocation was
about 2.47 GB. These nine observations do not establish release p95/p99,
end-to-end latency, quality improvement or M7. Raw diagnostics are in
`.tmp/reranker-real-corpus-latency-gpu-current.json`; `release_eligible=false`.

Earlier code verification: **318 passed, 2 live LLM tests skipped**. The implementation
now includes separately bound question/review packets, live request/resource
collection, all eight staging rollback exercises, permanent-failure follow-up
checks, and an isolated staging collector command. Raw staging summaries and
frozen output coordinates are recomputed by the validator. Runtime identity
includes installed inference dependencies and distinguishes CPU/CUDA wheels.

The selected future free web GPU target and its quota constraints are recorded
in [the free GPU deployment decision](../operations/gpu_hosting.md). No public
Space or final release has been published. M1 remains blocked; M2-M12 need
their actual ordered measurements after that gate passes.

The original strict human profile requires human inputs. The personal profile
also accepts owner-directed AI questions with explicit approval and frozen source
validation. Placeholder reviewers or fabricated staging windows cannot satisfy
release gates. The dataset
example in `configs/human_benchmark_record.example.json` deliberately has
pending review and incomplete fields, so it cannot pass validation.

## Optimization measurements (2026-10-02)

The precision, batch scheduler, bounded queue and calibration configuration now
carry explicit bindings. The production manifest also binds the measured
timeout, queue size, circuit limit and score-cache setting. Runtime transport
assigns request IDs on the server and validates document scope. Startup failure
and shutdown release provider resources. See the full measured comparison in
[the optimization report](reranker_optimization_report.md).

On a three-query hard-dev probe, BGE FP16 preserved the observed FP32 rankings,
reduced cap-10 p95 from 407 to 174 ms and approximately halved VRAM. This is
sample evidence, not a guarantee over unseen queries. A smaller MiniLM model
completed 100 uncached requests at concurrency 20 without errors (p95 475 ms),
but failed the dev abstention/quality target. BGE context lengths 256/512/1024
and dev rank-fusion/evidence-signal searches were also measured. None achieved
the joint recall/FPR target. No failed research configuration was promoted.

These studies are isolated under `.release/reranker/studies`; they retain raw
scores, request failures, input hashes and conditional status. Official M1-M12
remain blocked. Performance probes are reranker-only; full service/staging and
live LLM checks remain separate requirements.

Historical code verification before this implementation: **374 passed, 2 live LLM tests skipped**, with
**88.15% coverage** (85% required), no test failures or resource warnings.
Compile and diff checks passed. Readiness remains conditional with a null
official score; code improvements do not substitute for the missing release
measurements.

The next measured loop is documented in [inference_optimization_report.md](inference_optimization_report.md).
Query-focused table inputs reached dev Recall@5 89.80% at cap 20 with 0/8
negative outputs; cap 40 reached 91.84%. Neither met the joint quality target.
The cap-20 BGE load probe failed at concurrency 5 and 20. GTE completed the
cap-10 concurrency-20 probe without errors but had weaker dev quality.
Table input transforms and GTE compatibility remain research-only.

[Loop 3](abstention_optimization_report.md) adds dev-calibrated low-score abstention as
an explicit policy action; legacy policies keep Phase 6 fallback, as do
provider faults and low rank margins. The validator recomputes quality with
the recorded action. A fixed-policy natural-dev stress check showed severe
recall loss (70.00% baseline to 28.33% with abstention), so the measured
threshold remains conditional and production stays disabled.

## Runtime protection

Fallback returns exactly the requested Phase 6 output. Candidate generation
at 40 is separate from the dev-fitted rerank subset. Routing features always
use the same five-result retrieval plan as calibration. All provider output
coordinates, original ranks, scores and model identity are checked; NaN,
infinity, malformed objects and out-of-set candidates fail closed. Exception
traces expose fixed reason codes instead of arbitrary provider paths.

Model identity is verified before activation; the runtime cache includes the
snapshot digest. Requests use a bounded queue, timeout and circuit breaker.
Startup warm-up uses a separate 60-second timeout. Rollback closes admission,
cancels queued inference, disables new reranker calls and changes the answer
cache namespace without rebuilding the index.

The service can optionally use a deterministic canary cohort. Promotion is
0→1→5→10→25%, with three healthy windows per step. Auto-rollback monitors
latency, timeout, FPR, errors, memory, citation, scope and provenance.

## Validation authority

`python -m evaluation.reranker.validate_reranker_release` rechecks hashes and evidence,
recomputes routing metrics, paired quality statistics, performance summaries
and staging decisions. It returns `score=10.0` only when every gate passes and
the tree is clean. `--through M0` is a partial baseline check and keeps the
score null. Runtime and test file names describe their task; phase numbers
remain in compatibility identifiers and report metadata where appropriate.

## Original-source successor preparation — 2026-10-04

[The source expansion archive](../../evaluation/results/phase7-source-expansion-20261004/README.md)
retains original UET PDFs, rendered source tables, exact raw chunks and a complete
restorable physical index. Actual offline CUDA BGE-M3 adds 158 chunks from Robot
2020 and Electronics masters 2022 to a separate 12-document index; the original
10-document index and consumed r18 benchmark/locks are unchanged. The scan-only
Nano biology PDF remains excluded.

There are 95 explicit source course rows and 43 connected proposals after screening
27,957 historical question occurrences, including English, wrapped aliases and
spaced course codes. Semantic approval, successor questions and freeze remain
pending. No fresh heldout scores were measured. Official status stays **3/19
PASS, M2 FAIL**, score unavailable. Roadmap: [plan.md](../../plan.md).

Final source/audit suite: **786 passed, 2 live LLM tests skipped**, coverage
**89.51%**. The restored index reproduces all 26 exact file hashes and the final
43-group history screen. These checks do not count as live-provider acceptance.

## Validated successor dev inheritance — 2026-10-04

[The inheritance preflight](../../evaluation/results/phase7-dev-inheritance-20261004/README.md)
reconstructs **817 dev-only rows** from 804 consumed r18 records plus 13 exposed
r12 absence records. It preserves 180 human / 637 AI origins and three historical
authorizations, verifies all 54 parent artifacts and 22 old index files, and rejects
817/817 attempted heldout assignments. No new benchmark or model scores exist.

M1/S1 now validate mixed new-generation and inherited provenance while refusing
injected internal metadata, altered fields, mismatched owners and heldout reuse.
Final regression: **810 passed, 2 opt-in live LLM tests skipped**, coverage
**89.51%**. Rechecking active r18 through M2 still yields M0/M1/S1 PASS, M2 FAIL,
conditional status, null score and `all_release_gates_pass=false`.

## Successor source batch b — 2026-10-04

[The batch-b archive](../../evaluation/results/phase7-successor-source-20261004b/README.md)
adds two original public PDFs and 47 actual CUDA-indexed chunks to a separate
14-document index. PDF renders corroborate 43 new explicit course rows, for
138 total. The Mechanics URL publication year is 2019, with cohort unspecified;
uncoded electives and the scan-only Nano biology source remain excluded.

Exposure now propagates through shared course codes and bilingual/wrapped
aliases across all indexed ancestors. Screening 28,774 historical question
occurrences in 177 datasets leaves 47 connected proposals. All 30 index files
restore exactly and reproduce the final audit. Semantic exposure approval,
new benchmark questions, split preflight and successor freeze remain pending.

Final regression: **812 passed, 2 opt-in live LLM tests skipped, coverage
89.51%**. GPU build and CPU audit snapshots have separate physical bindings;
neither is a clean release manifest. Active r18 remains **3/19 PASS, M2 FAIL**,
null score and `all_release_gates_pass=false`. Roadmap: [plan.md](../../plan.md).
