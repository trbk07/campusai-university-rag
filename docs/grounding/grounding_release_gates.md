# Phase 5 release gates

## Internal closure process amendment —25/10/2026

The owner permits lower closure-process gates provided Phase5 quality remains
unchanged: “có thể hạ thấp gate đóng nhưng phải đảm bảo chất lượng của phase 5
được giữ nguyên”. The implementation choice is an explicit
`native-http-checkpoint-v1` path for **Phase5 internal acceptance only**.

All400 reviewed cases, split populations, numeric quality thresholds, physical
source/citation checks, source review and regression requirements remain.
This does not authorize gold-derived predictions or invented approval evidence.

A real recorded Gemini response may be reused only for the same case/request,
model/config/index and exact canonical HTTP body. The original native run,
raw response, transport journal, producer identity and hashes remain bound.
Current CampusAI must execute again against those recorded inputs; merely
editing a stored prediction is insufficient. Selection is fixed by source
completion/time, never expected correctness. Pinned dev training captures keep
their original selection. Offline misses remain pending, never negative gold.
Changed or missing inference inputs require genuine inference within an existing
valid egress authorization and cumulative quota. Reuse does not refund spending.

Reports distinguish reused native responses, deterministic reprocessing and
fresh provider POSTs. Reprocessing supplies no new live-latency evidence.
Calibration uses dev only and is pinned before current held-out reprocessing;
historical generation/pin times remain explicit and are not relabelled.
The physical validator must recompute current pipeline outcomes and fail closed
on missing inputs, altered captures, forged counters or output mismatches.
Public release retains its fresh-holdout and native-inference requirements;
checkpoint-only internal acceptance cannot satisfy those gates.

The production candidate is immutable and keeps its3 consecutive full regression
receipts. A later scorer-only verifier extension may use focused regression plus
physical source-tree comparison, provided production runtime and inference inputs
are byte-identical; it is not reported as3 full suites on the newer scorer source.
All quality thresholds and complete-population physical validation still apply.

Internal checkpoint receipts may survive a later documentation/evidence-only
Git commit when both physical code/runtime hashes remain identical, the recorded
commit is an ancestor, and the complete commit diff is limited to plan.md,
QA_AUDIT.md, docs/ and evaluation/results/. Changed benchmark, configuration,
UI/runtime or scorer bytes fail this check. Native/public validation keeps exact
commit identity. This avoids invalidating tested code merely by committing its
own receipt; it does not waive physical recomputation or any quality threshold.

Metric policyv7 fixes calendar/academic-year quantity ambiguity and layout
ordinals whose value is retained in the fact. A longer literal source condition
or shared list minimum needs exact source proof; changed bounds, units, dates,
roles and invented additions remain failures. No numeric threshold is lowered.

The release validator is authoritative; reports cannot contain a manually
supplied pass flag. A release candidate must use runtime mode and include the
benchmark checksum, code fingerprint, schema/policy versions and calibration
artifact checksum. `runtime` also requires a native CampusAI collector run,
raw provider captures and physical artifact bindings; fixture and replay
reports cannot qualify as release evidence.

Required dataset gates:

- at least 400 records;
- dev >= 120, test >= 130, holdout >= 150;
- all Phase 5 categories present;
- unique IDs, evidence for every answerable gold claim, and a reason for every
  gold abstention;
- no uncontrolled cross-split source/template leakage.
- every split contains both answerable and abstention cases so holdout metrics
  are meaningful rather than degenerate.

Observable source/template/intent-paraphrase families must not cross splits.
Repair and validation use `evaluation/benchmarks/families.py`, including source
IDs from gold evidence and author-declared selected-document scope. Uploaded
filenames and `Topic:` casing cannot conceal identical templates. The validator
also rejects the legacy `Topic:` suffix that copies a complete gold claim into
the question. Normal source-scoped questions and fact-check assertions are not
automatically treated as gold disclosure by that bounded check.
Split-specific template labels cannot hide duplicates.
Previously exposed rows remain exposed after regrouping; the grouped candidate
is not approved merely because leakage becomes zero. Minimum split sizes and
population balance still apply.

On2026-10-21 the owner explicitly allowed two bounded Phase5 dev designs:
`conflict` may use controlled synthetic input PDFs visibly labelled FICTIONAL,
with actual conflicting facts under identical applicability and equal authority;
`provider_abstention` may test benign over-refusal with source-supported
answerable gold. Synthetic inputs never count as model outputs or genuine
institutional rules. Provider faults/refusal fixtures remain separate and count
as zero successful native outputs. All proposals still require independent
source review, owner final sign-off and the unchanged quality thresholds.
See the [resolution and authorization](phase5_remaining56_resolution.md).

Independent annotation evidence is mandatory. On 2026-10-16 the owner explicitly
authorized `phase5-ai-owner-v1`: independent AI source review plus owner sign-off
may replace independent human review for Phase 5. The existing
`independent_human` path remains supported. AI review is recorded as
`independent_ai_owner`, never as human review. See the
[review policy and authorization](phase5_ai_review.md).

`annotation_signoff` must bind the exact `benchmark_sha256`, actual population,
creator IDs, attested independent reviewers and complete approved
`row_decisions`, each with its `annotation_sha256`, reviewer and date. The AI
path additionally binds physical source-audit artifacts and a concrete owner
approval of the frozen benchmark and review bundle. Permission to change policy
or perform work does not stand in for that final approval. An `exposure_review` must bind sorted
holdout IDs and reference the actual exposure audit. Public release requires a fresh holdout.
Creator/reviewer overlap, missing/stale decisions, unresolved source findings,
missing AI owner approval or missing exposure evidence fail closed. These are
provenance requirements; the numerical thresholds below
are unchanged. See the [current audit and reviewer steps](phase5_completion.md).

On 2026-10-21 the owner confirmed the existing authored questions had been
reviewed and met the standard, then explicitly accepted the reviewed benchmark
with disclosed exposure for Phase 5 acceptance. `--acceptance-scope phase5_acceptance`
allows this specific exposure exception only with a physical owner decision,
benchmark/holdout/review-bundle bindings and `holdout_fresh=false`. The default
`public_release` validator and release package remain strict: Phase 5 acceptance
cannot certify freshness or public release. Numerical thresholds, real inference,
calibration, source fingerprints and clean Git checks remain unchanged.
The exact owner statements and deterministic 400-row selection are recorded in
[owner decisions](../../evaluation/results/phase5-acceptance-20261021/owner-decisions-exposure.json).

Required safety gates:

- unsupported and contradicted public-claim leakage: 0;
- citation coordinate validity: 100%;
- citation precision >= 0.99, recall/completeness >= 0.98;
- grounded claim precision >= 0.99 and recall >= 0.95;
- abstention precision >= 0.99, recall >= 0.98, reason accuracy >= 0.95;
- schema/internal-field leakage: 0.

The Phase 5 scorer has an explicit, Phase 5-only option for reviewed
cross-language source subspans. It may match a claim to gold only when the
prediction is a contiguous literal phrase inside that gold claim's reviewed
evidence quote, its visible citation is physically bound to the same document
and page and covers the complete reviewed span, all numeric anchors and
programme-code identities in gold remain in the claim, and
negation/condition/restriction/exclusion scope is preserved. A source-side scope marker immediately before the copied phrase
cannot be dropped. Only a leading discourse marker such as Vietnamese "lưu ý"
or English "note that" is ignored. This is a source-copy check, not semantic
translation or general entailment; it cannot add unsupported clauses. The
native Phase 5 scorer, release validator, and calibration labeler enable this
option together. Other phase callers retain the default behavior. Release
thresholds and runtime claim validation do not change.

Required calibration gates:

- fit split is dev only;
- holdout ECE <= 0.05 and Brier <= 0.08;
- calibration count >= 400;
- risk at 80%/90% coverage <= 1%/2%, measured over publishable
  non-abstained answers; abstentions remain outside the coverage denominator.

If any gate fails, status is `pre-release` or `release_candidate`, never
production-ready. Thresholds, annotations and policy are frozen before the
final holdout run; fixes produce a new release candidate.

The validator recomputes overall/split/category metrics and checks published
answers/claims/citations against native predictions. It rejects malformed,
non-finite, incomplete or inconsistent reports and physically verifies
benchmark, source, calibration, signoff and native artifact hashes. A dirty
workspace is reported honestly and cannot receive a production release PASS.

For bounded native batches, every run is physically bound through
`generation.native_runs`; duplicate IDs or mixed source/model/config/index/
document-scope identities are rejected. Under the explicit
`dev-fit-then-pinned-evaluation-v1` protocol, only batches whose IDs all belong
to dev in the physical benchmark may be uncalibrated training captures. Every
test/holdout batch must bind the one pinned calibrator. Original training scores
are preserved; captured calibrated scores/labels/policy versions are checked.
Report-supplied split labels cannot establish the dev exception. The three raw artifacts and their measured
counters must reconcile. Published output and captured numeric scores must
match evaluation rows. Provider failures cannot serve as valid negative gold
evidence. Config/index files are checked physically, including index contents.
The calibration artifact must equal the dev-only fit on the captured dev
predictions; its declared split alone is insufficient. Release package checks
invoke these same physical checks rather than using structural validation alone.

The native collector must execute CampusAI/evaluation modules from its own
candidate checkout. A shared editable virtualenv cannot substitute another
checkout's runtime. Before sending requests, the collector verifies that the
packet binds the actual source/runtime identity. Physical release validation
also verifies the packet hash and its source, benchmark, config, index, model
and document-scope bindings against every native run. A mismatch is diagnostic
evidence only and cannot be relabelled as a qualified candidate capture.

A scorer-only repair may retain native inference from its original immutable
checkout under `physical-scorer-only-v1`. This does not relabel any capture:
the report binds the separate inference and scoring identities and retains
the producer checkout physically inside the scoring workspace. The validator
recomputes both complete source fingerprints and every changed-file hash.
Only the four explicitly named scoring modules and tests may differ; changes
to application code, collector, scripts, configuration, dependencies or any
other fingerprinted input require new inference. Native batches still share
one original producer identity and match their original packets exactly.
Calibration is fitted with the repaired scorer before held-out collection.

Quote policy `reviewed-span-coverage-v6` additionally recognizes an ASCII
transliteration of a complete reviewed claim only when all ordered tokens
match after accent removal, with unchanged numeric/role checks and every
condition retained. Citation quotes remain literal and their physical source
coordinates must still match. This does not introduce accent-insensitive
fuzzy matching, alter gold or change any threshold.

Git cleanliness covers every tracked edit and untracked source/configuration,
including the root plan. Generated evaluation results and corpus/data files
are data artifacts: their own physical hashes and review bindings are checked
separately, and retaining an untracked raw result does not imply edited code.
The physical validator recomputes source cleanliness instead of trusting the
report's declaration. This rule never ignores an edited tracked file.
