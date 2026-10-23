# Phase 5 release gates

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
