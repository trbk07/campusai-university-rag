# Phase 5 release status

**70%: P5-01 through P5-07 DONE; P5-08 through P5-10 remain open.**
[Plan](../../plan.md) is the authoritative checklist. Current source SHA-256 is `5f708c44a55c0723b1a6da403f4267219c5e60bcd7f21d7641e825c82f1fa727`; runtime is `e6e8ac0ca3cb4294878b09c61308b387079a3ed6b1dc1b9c120359b54303f385`. Phase 5 focused regression: 427 PASS. Broad regression: 2,343 PASS / 2 live-provider SKIP after excluding five unrelated platform/harness modules. Historical r4 dev120 has below-threshold metrics; current-source inference and held-out quality remain open.

The previous-source v2 packet touched 103/120 dev rows and captured real model JSON
for 57 distinct IDs across 99 journaled request starts. Its 95-evaluable-row diagnostic
still had 2.04% unsupported-claim leakage. Those outputs bind older source/runtime
hashes and cannot qualify the repaired source. Official predictions remain 0.

Gemini Chat returned 33/33 supplementary source-review records. The audit found 13
records with citation, absence-inspection, reason, or page-boundary issues; it supplied
0 CampusAI predictions and does not replace native inference.

The owner reviewed the authored questions and approved independent AI review plus
owner sign-off with disclosed benchmark exposure for Phase5. All680 candidate
records have usable source findings. The selected400 are dev120/test130/holdout150;
family leakage0, legacy temporal status23/23 resolved. [Physical review validation](../../evaluation/results/phase5-acceptance-20261021/benchmark-validation.json)
PASS. Original400 gold records, all680 candidates and actual review evidence remain.
Public release still requires fresh holdout data. No numeric threshold changed.

The completed qualification attempt used immutable candidate-r2, commit
`d7f83c986906d02421cc2f9de046ae007530d1aa`, source `5b75d28e8c44114fc803830961ce200c0d01bb4afcee7223e14b8f67384a330d`,
and the owner-selected60-second profile. It produced389/400 pipeline outcomes:
dev120, test130, holdout139. There were402 provider POSTs and400 successful real
model responses; follow-ups mean these are not400 unique answered questions.
One60-second timeout and oneHTTP429 remain failures;11 records were not attempted.
The provider reported500 requests/day exhausted. There were no retries, quota
resets or key changes. **Official accepted predictions:0.**

Calibration implementation, cache isolation and checksum pinning are DONE.
The real dev-only artifact was fitted on120 outcomes and pinned before held-out
inference; payload checksum `1ff16439e70251cdf7e92770c8371547ec3d7807f8dd7edbad13632d862d03ca`.
Held-out quality is not PASS. The baseline report measured grounded-claim
precision53.06%, citation precision55.93%, abstention precision70%, ECE0.087448
and Brier0.112089 across389 outcomes. These fail the unchanged thresholds.
Incomplete-population review errors do not invalidate the separate reviewed400.

Subsequent main-workspace repairs address wrong foundation/general admission
columns and generic regulations being used for actual personal records. Bounded
field projections preserve physical row/year/source proof; personal-event claims
fail closed without a supporting individual record. Cache policy is nowv16.
These changes are separate from the older native actor and cannot inherit its
native qualification. Admission repair:160 focused PASS,2247 full PASS/2liveSKIP.
Personal-scope repair:72 focused PASS; [final full run](../../evaluation/results/phase5-acceptance-20261021/personal-scope-full-run.json)
PASS2251 tests/2liveSKIP with identical start/end source. Live skips are not passes. Other phases keep
their statuses, baselines and stores.

[Execution status](../../evaluation/results/phase5-acceptance-20261021/native-execution.json),
[manifest](../../evaluation/results/phase5-acceptance-20261021/manifest.json) and
[raw evidence archive](../../evaluation/results/phase5-acceptance-20261021/native-timeout60-evidence.zip)
retain the failures, predictions, retrieval, calibration and source identities.
The archive is byte-verified against the immutable captures; original captures
and historical baselines remain. No further question-content review is required
for this Phase5 benchmark. Remaining work is runtime quality repair, a complete
qualification on the repaired frozen source after provider capacity is available,
then passing physical/quality validation and final closure. See the
[handoff](phase5_completion.md) and [gates](grounding_release_gates.md).

The22/10 coverage/metric repair additionally PASS151 focused metric/native/release
checks and115 image/scope/native checks. [Final full regression](../../evaluation/results/phase5-acceptance-20261021/coverage-metrics-full-run.json)
PASS2263 tests,2 live SKIP; source start/end identical. Reader policyv2 detects
inline images; unrendered image resources alone no longer imply incomplete text.
Evaluator policyv4 ignores a list ordinal only with fact-aware safeguards; changed
values, required identities, years, units and source coordinates remain strict.
Diagnostic reanalysis corrects3 old test-row labels, with0 dev label changes.
Grounded precision is55.10% and citation precision58.19% on that diagnostic;
these remain FAIL, not new native qualification. The original report remains.
The new four-file delta follows the earlier seven-file development delta and
reconstructs that573-file regression checkpoint. Owner has authorized the bounded
PDF/vision extension and its exact capability probe. Implementation and capture-integrity
tests now PASS95, with131 combined PDF/retrieval checks. The provider probe remains
unexecuted while the shared daily quota is exhausted;0 new requests were sent.
The latest full regression PASS2320 tests,2 live SKIP; source start/end identical
([receipt](../../evaluation/results/phase5-acceptance-20261021/quantity-chunk-full-run.json)).
PDF implementation, PO/PLO retrieval repair and offline regression are DONE;
provider capability probe has now passed; native quality qualification remains open. The16-file
`pdf-outcome-delta.zip` follows the earlier two deltas and reconstructs576 source files.

Named-course headed credit proof accepts the optional Course prefix; complete
date/time identity checks preserve formatting equivalence and reject reordered
values. Credit-count answers must contain a value. These repairs PASS265 focused
checks and the full2305 suite above;0 new provider requests. Cache policyv18 and
promptv13 isolate older answers. The8-file calendar-names delta follows the
existing reconstruction chain, retaining576 physical source files. A separate
source/index audit confirms quantity-only lines incorrectly split curriculum
labels from their values; that ingestion/index repair is now DONE. Native
quality gates still require new current-source qualification.

P5-08f is DONE: producer structure-v5 keeps standalone credit values beside
their source labels, restores split multi-page course rows only under a verified
credits header and explicit semester marker, and carries that scope into the
table chunk. Same-hash stored documents are reparsed when producer versions
change. The current v14 store/index contain14 physical PDF identities,528
chunks and79 tables; index checksum validation passes and all14 documents bind
structure-v5/table-v3. The MAI Semester 4 table returns “Strength of Materials
— 3 credits” as the top retrieval result with its header and scope. The existing
v13 index, captures and baseline remain untouched. Focused synchronized
regression is246/246 PASS; the current full-suite attempt was stopped at70%
after a CPU-bound integration test, with no failures reported before stopping.
The subsequent full source-current suite completed2345 PASS,2 live SKIP; source
and runtime fingerprints remained unchanged. The skipped live integrations are
not counted as passes. Current-source native quality gates remain open.

The initial current-source v2 batches used owner-approved packet v2
(`87913b13855f2cb7a28c515b10fe2d6812f557c1b766a839345a6d1fac190944`), commit
`13b193a0f2f383413a9b19d97fc1d2133249cde0`, source
`91a68a42c1bac692eb7d34e942da3574a2f30810d2e63699e6587491cf36e5c4`, runtime
`cd001c4d3d7683c90ef13d21ea21d3ae1b1e3878bdc6e7096bd8ea8fe6fc04a2`, and v14
index `13523be6ca09e6e54126ae40c596df00f01cd877f02f5692b0d03045aa38111a`.
The first run recorded8 pipeline outcomes and4 provider POSTs, with3 successful
real JSON model outputs; it stopped on HTTP503 `provider_overloaded` for
`draft-0454`. A disjoint continuation skipped all previously attempted IDs and
recorded26 pipeline outcomes,19 POSTs and14 real JSON outputs before HTTP503 on
`draft-0023`. No retry or test/holdout request was sent. Across both runs there
are34 unique diagnostic rows,23 POSTs,17 successful real JSON model outputs,
two provider failures and0 official predictions. Partial metrics are grounded
precision100%/recall90.91%, unsupported leakage0%, citation precision100%/recall
90.91%, abstention precision96%/recall100%, and reason accuracy95.83%. Excluding
the two provider-failure rows gives32 diagnostic rows with100% observed
grounding/citation/abstention/reason metrics, but the subset mixes local and
model outcomes and does not qualify the release. See the [first run](../../evaluation/results/phase5-current-native-qualification-20261022/dev-native-v2-approved/run.json)
and [disjoint continuation](../../evaluation/results/phase5-current-native-qualification-20261022/dev-native-v2-continued/run.json)
journals with their raw captures. Current-source dev, calibration, held-out
quality and P5-09b remain open.

Subsequent continuations of the same packet have now touched71/120 dev rows and
captured48 successful real model JSON outputs across74 journaled request
attempts. Two transient case recoveries succeeded after provider cooldowns;
other provider503 and timeout failures remain preserved. No current-source
calibrator or test/holdout run exists, and `official_predictions=0`. Chat-based
review is supplementary and does not exercise CampusAI retrieval or response
generation, so it cannot substitute for native inference or satisfy P5-09b.


## Current-source remediation - 23/10/2026

The Phase 5 inference changes narrow multi-role claims, prevent scope expansion in generated claims, and allocate native collection budget to initial question coverage before optional full-document follow-ups. That code snapshot was source/runtime `1bd90be27f1021fcf5bf641ebb5b3d9fff93f650919705b03e7804990936a70e` / `108980205dabd944e81fd34897ab43c015762b73bdddb1f54a669f7414624e80`; the current r5 identity, including the web performance fix, is recorded below.

Full offline regression on current source r5: 2362 PASS, 2 live provider tests skipped; focused document-scope/native-PDF/web/ingestion suite: 72 PASS. Source/runtime SHA-256: `91f4f5dd4628feacc0d6efd95cc99e1f5fea199b1e2b363f0f9237c322f07758` / `7ab2731095bc8388a877df5e28d4fa8e33fa0393201178955a5d4f5e9b03a918`.

The owner-approved dev packet SHA `49c57804767a8c4ef62763b76732c55defbb9e03777b5c5e1fc4d6b368630345` was attempted on the pre-fix fingerprint. The collector stopped at the first provider error (`draft-0459`, `provider_unavailable`): 59 POSTs, 48 successful real model JSON outputs, 71/120 pipeline outcomes, 0 official predictions, no retry.

Partial diagnostic metrics on 70 rows: grounded claim P/R 94.74%, unsupported leakage 5.26%, citation precision 93.94%, citation recall/completeness 94.74%, abstention P/R 100%, reason accuracy 100%, ECE 0.049678, Brier 0.031978. This sample is incomplete, has failed claim/citation gates, and binds source/runtime `0f975a8879652de73d94a8d5f6205562ede915076a08a6bfb365aa2b174bda36` / `db454eb10dc74bf3bd6b277fbef8450016f03a4feb50a01bb02560a8e3c3723a`; it does not qualify the patched source.

The post-fix native dev run at `evaluation/results/phase5-current-native-qualification-20261023/dev-native-af97-r2/run.json` completed all 42 selected rows with 61 POSTs, 51 real JSON outputs, 0 provider failures, and no retry. Score: `evaluation/results/phase5-current-native-qualification-20261023/dev-score-af97-r2.json`; diagnostic grounded P/R 97.22%, unsupported leakage 2.78%, citation precision 96.77%, recall/completeness 97.22%, ECE 0.068397. `draft-0551` contains an extra unrequested researcher role in claims. This 42/400 subset does not qualify; calibration and complete dev/test/holdout remain open. The old packet remains consumed. No quality thresholds changed.

The current-source packet `3e06611d8760914c9e6217ce537aae3f0078d6b232d1788e8c66489f28f7655d` ran at `evaluation/results/phase5-current-native-qualification-20261023/dev-native-scopefix-1bd90be2-10898020-r2/run.json`: 48 POSTs, 39 valid JSON outputs, 31 pipeline outcomes from 42 selected dev questions, and 0 official predictions. It stopped at `draft-0078` after a valid model JSON requested a full-document absence check not included in that row's approved packet. The application returned `provider_unavailable`, but there is no failed HTTP/raw-model record for that row; classify this as a fail-closed packet-scope mismatch, not a confirmed Gemini outage. The partial score is `evaluation/results/phase5-current-native-qualification-20261023/dev-score-scopefix-1bd90be2-10898020-r2.json` and remains BLOCKED: grounded P/R 95.45%/87.50%, unsupported leakage 4.55%, citation precision/recall 95.00%/87.50%, abstention P/R 90.00%/100%, Brier 0.040140, ECE 0.076332. Complete dev, calibration, test and holdout remain open; quality thresholds are unchanged.

The current r5 dev120 packet is `evaluation/results/phase5-current-native-qualification-20261023/dev-egress-current-source-r5-91f4f5dd-7ab27310-20261023/egress.json` (SHA-256 `7b8fe9b8e0170a14b61f1007c9f701b9dce35bfe8dd8c0457c7d554094346edd`), bound to source/runtime `91f4f5dd4628feacc0d6efd95cc99e1f5fea199b1e2b363f0f9237c322f07758` / `7ab2731095bc8388a877df5e28d4fa8e33fa0393201178955a5d4f5e9b03a918`. It covers all 120 dev rows; 69 require model inference and have exact conditional full-document follow-ups, with 207 planned/capped calls. All 138 request cases and PDF sources are byte-identical to the previously approved packet; selected dev IDs and current source/runtime bindings match; `provider_posts=0`. The new exact packet hash still requires approval before inference. Last quota observation: 483/500 on Pacific day 2026-10-22. No quality thresholds changed.
