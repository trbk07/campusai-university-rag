# Phase 5 operations and rollback

Native collection journals provider attempts before transport, raw responses
before pipeline post-processing, and each completed prediction immediately,
with flush/fsync. `run-started.json` records source/config/index/benchmark and
cap before calls; `model-started.jsonl` preserves pending prompt identities.
An interrupted run without final `run.json` fails closed. Preserve its spent
attempts and raw output; do not reset quota, overwrite files, silently retry
or treat a missing response as an unused request. A later recovery needs an
explicit new scope and must not invent outputs. These are collector safeguards;
they do not alter app/provider retry or quality thresholds.

Start the local transport with `python -m scripts.operations.serve`. Probe `/live` for
process liveness, `/ready` for index readiness, `/health` for service health,
and `/metrics` for bounded latency/error summaries. Query responses are safe
only when `ok=true`; abstentions are normal safety outcomes.

Ingestion jobs are asynchronous. Inspect the job endpoint/adapter, retry only
jobs marked `retryable`, and do not re-submit a running content hash. During a
provider outage, keep retrieval available but publish only structured
abstentions. Never bypass the grounding validator.

For index corruption, stop traffic, retain the corrupt directory for audit,
restore the last immutable index version, run `scripts/operations/recovery_check.py`, and
only restore readiness after every checksum loads. For rollback, point the
deployment at the previous immutable code, calibration and index bundle, clear
answer caches by corpus/policy version, run `scripts/operations/rollback_check.py`, then
repeat deployment smoke probes. Database and document metadata backups must be
restored before indexes because citations depend on stable document IDs.

Graceful shutdown calls `CampusAIApplication.close()`, drains the ingestion
executor, and closes query/cache resources. Forced termination may leave a job
in progress; restart from immutable source input and verify the resulting
index checksum rather than trusting a partial directory.

## Benchmark audit and native evaluation

Preserve original benchmark bytes, exposure history and historical baselines.
The repair tool writes an unapproved review packet to a new directory; it
refuses to overwrite reviewer edits. It never creates reviewer identities or
approvals. The [current handoff](../grounding/phase5_completion.md) lists the
current review contract and existing evidence. Phase 5 now additionally supports
the owner-authorized [AI review and owner sign-off policy](../grounding/phase5_ai_review.md);
human requirements in other phases remain unchanged.

```powershell
.venv/Scripts/python.exe -m evaluation.grounding.audit_phase5 --help
.venv/Scripts/python.exe -m evaluation.grounding.repair_benchmark --output evaluation/results/phase5-review-new
.venv/Scripts/python.exe -m scripts.benchmarks.validate_benchmark_data data/benchmark/grounding_reviewed.jsonl --release
```

The current original benchmark fails release hygiene; that failure is expected
until review and new independent families resolve the audit. `make
grounding-eval` runs a gold-derived fixture diagnostic only. It cannot provide
model-quality or production approval evidence. The legacy runner's runtime
mode requires `--responses` and is explicitly replay, not native inference.

Prepare a bounded exact-payload egress packet before calling the current
CampusAI pipeline. Preflight sends no provider requests and creates no model
predictions. Select an offset/limit for the intended batch and inspect the
packet's destination, questions and retrieved context. The owner approved the
four payloads in `phase5-egress-20261016` once; that budget is now consumed.

```powershell
.venv/Scripts/python.exe -m evaluation.grounding.collect_native_predictions --benchmark data/benchmark/grounding_reviewed.jsonl --index .tmp/hybrid-index --config configs/free_llm.yaml --offset 4 --limit 8 --max-provider-calls 4 --prepare-egress --output evaluation/results/phase5-egress-next
# After authorization of that new packet and its destination:
.venv/Scripts/python.exe -m evaluation.grounding.collect_native_predictions --benchmark data/benchmark/grounding_reviewed.jsonl --index .tmp/hybrid-index --config configs/free_llm.yaml --offset 4 --limit 8 --max-provider-calls 4 --egress-packet evaluation/results/phase5-egress-next/egress.json --output evaluation/results/phase5-native-next
.venv/Scripts/python.exe -m evaluation.grounding.score_native_predictions --benchmark data/benchmark/grounding_reviewed.jsonl --native-dir evaluation/results/phase5-native-next --output evaluation/results/phase5-native-next-score.json
```

Use the actual repaired/reviewed benchmark path for official work. Inference
receives only the user question, language and declared scope/history; gold and
labels are loaded by the separate scorer. Retain `raw-model.jsonl`,
`predictions.jsonl`, `provider-posts.jsonl`, `run.json`, the exact source bundle,
model/config/index identities and benchmark hash. Raw captures are internal.
Archive the source before editing it; changing the evaluator creates a new
analysis identity and does not rewrite the identity of earlier predictions.

The collector stops at the actual provider-call cap or first provider failure;
it does not silently retry. Check completed IDs before selecting the next
offset, and reconcile all batch populations before release. Local abstentions,
cache hits, transport failures and successful uncached provider outputs have
separate counts. A partial batch is not a complete evaluation.

The optional `--http503-recovery-authorization` requires a physical owner
decision bound to the exact packet hash and call budget. It permits one
evaluation-only recovery per case after the provider cooldown (at most300s),
within the same total call cap. Failed raw responses and elapsed cooldown stay
in the audit trail. Other errors or a second503 stop the run. Default behavior
and the application Free profile retain zero retries; quota and circuit state
are shared without resets.

Use the existing shared quota governor and circuit state. Never reset their
databases, rotate keys, bypass cooldown or remove historical attempt charges to
obtain a PASS. The original sandbox attempts failed with WinError 10013; their
failure evidence and quota accounting remain retained.

Only after genuine independent annotation and exposure review, freeze the
benchmark/policy, fit calibration on dev-only native predictions, and run the
release validator. Pass `--annotation-signoff <actual-signed-file>` to the
native scorer. Missing calibration, incomplete population, stale bindings,
missing review or a dirty working tree remain BLOCKED. The present pilot has
no official signoff and must not be relabeled as approved evaluation evidence.

## Bounded batches and pinned calibration

The native scorer accepts repeated `--native-dir` arguments. Batches must have
disjoint prediction IDs and matching benchmark/source/model/config/index and
document-scope policy identities. The reader requires all three raw artifacts, reconciles
measured counters, rejects negative/reused/orphan capture indices and checks
parsed model JSON against raw provider text. Local outcomes and cached outputs
remain distinct from successful uncached model outputs. A provider/pipeline
failure prevents release even if its abstention happens to match a gold negative.

```powershell
.venv/Scripts/python.exe -m evaluation.grounding.score_native_predictions --benchmark <reviewed-benchmark.jsonl> --native-dir <batch-01> --native-dir <batch-02> --output <combined-native-score.json>
.venv/Scripts/python.exe -m evaluation.grounding.calibrate_confidence <native-dev-score.json> --output <dev-calibration.json>
```

Fit from dev-only native rows before opening fresh holdout. Calibration based on
unreviewed gold remains diagnostic. The production collector accepts
`--calibration-artifact <dev-calibration.json> --calibration-sha256 <artifact_sha256>`;
both arguments are required together. It checks the benchmark binding and
declared dev fit before creating the provider client and records the calibrator
identity in each run. Include these same arguments in egress preflight and
collection. The scorer records protocol `dev-fit-then-pinned-evaluation-v1`.
It accepts the original uncalibrated dev-only training captures together with
test/holdout captures using the pinned calibrator. It verifies dev membership
against the physical benchmark, keeps the original scores/public responses,
and recomputes the exact dev fit. Never relabel training captures as calibrated
or recollect dev just to make calibration identities match. Every test/holdout
capture must bind the one pinned calibrator. Mixed source/config/index identities,
uncalibrated held-out rows, wrong calibrators and report-only split changes fail.
The validator also checks calibrated numeric scores, confidence labels and
policy versions against each published capture; changing run metadata is not
evidence that calibration actually ran.

```powershell
.venv/Scripts/python.exe -m evaluation.grounding.score_native_predictions --benchmark <reviewed-benchmark.jsonl> --native-dir <original-dev-fit-batch> --native-dir <calibrated-test-batch> --native-dir <calibrated-holdout-batch> --calibration-artifact <dev-calibration.json> --calibration-sha256 <artifact_sha256> --annotation-signoff <actual-approved-signoff.json> --output <candidate-score.json>
```

Scoring recomputes dev-only isotonic fit from the captured dev predictions and
requires an exact match to the pinned artifact; it never refits using test or
holdout. If dev inference changed, resolve/freeze its calibration before opening
holdout. The scorer keeps captured numeric confidence unchanged and reports
calibrator metrics/risk separately. Re-evaluation cannot repair incorrect
predictions, replace missing independent review or erase exposure history.

Standalone and package validators both inspect physical native artifacts,
current source, config/index checksums, model binding, captured scores and the
calibration fit/population. Merely supplying a path, a checksum or
`fit_split=dev` does not establish these facts. No additional provider calls
were needed to add or test this workflow.

## Complete textual source scope

Serving configures the owner-authorized reader for managed uploads. An ordinary
model absence proposal can trigger one bounded complete-text inference only
after physical source checks. Sources with images, missing text, redaction,
changed hashes, filters or truncation remain insufficient evidence. No public
proof flag is accepted. An explicit page request never expands to other pages.

Native collection opts in with `--source-store <registered-store>` and optional
repeated `--source-root <operator-authorized-root>`; the default root is that
store's uploads. Include exactly the same flags in preflight and collection.
Preflight lists `initial` and conditional `complete_document_scope` prompts;
its call cap includes both stages. Consent for an initial prompt does not
authorize the optional follow-up. The collector checks emitted prompt hashes
before transport, saves both raw captures, retains initial retrieval in the
scope audit and final physical-page evidence in the prediction, and stops on
provider failure. Policy identity must match across batches. Full-source
answers are rechecked on another request rather than persisted in the ordinary
answer cache. The policy and bounds are documented in the
[source-scope mechanism](../grounding/document_scope_integration.md).

The20/10/2026 runtime change supersedes the old fresh-study runtime freeze.
Keep the existing test/holdout and source reviews as historical/diagnostic
evidence. They do not regain holdout independence by updating a hash or
repartitioning; establish a new frozen study before official holdout inference.

## Independent signoff and benchmark revisions

`scripts.release.annotation_signoff validate` checks the full current contract:
aggregate coverage, independent per-row decisions, benchmark/annotation
hashes, holdout exposure evidence and benchmark split hygiene. A legacy blanket
attestation cannot receive PASS from this CLI. Its JSON stdout stays parseable
on Windows code pages; dependency import diagnostics go to stderr.

```powershell
.venv/Scripts/python.exe -m scripts.release.annotation_signoff validate <reviewed-benchmark-revision.jsonl> <actual-signed-review.json>
```

The optional `template` command only prepares pending fields when explicitly
invoked with actual creator IDs. It uses the actual benchmark population, leaves
unverified aggregate findings unknown, supplies no reviewer/row decisions, and
refuses to overwrite an existing file. The existing
`.release/grounding/annotation_signoff.json` remains untouched: pending, zero
records reviewed and no independent per-row decisions. It cannot unblock release.

Release manifests now bind `benchmark_path` alongside `benchmark_sha256`, so
reviewed corrections can live in a new revision while the original gold
file remains unchanged. The benchmark must resolve inside the repository and
package artifact paths must stay inside the package directory. Legacy manifests
without `benchmark_path` retain the original default path, but still undergo
all current review/native/quality validation. No threshold was relaxed.

For the owner-authorized Phase 5 AI review path, create a fresh pending template:

```powershell
.venv/Scripts/python.exe -m scripts.release.annotation_signoff template <benchmark-revision.jsonl> <new-pending-signoff.json> --creator-id <actual-author-id> --review-type independent_ai_owner
.venv/Scripts/python.exe -m scripts.release.annotation_signoff validate <benchmark-revision.jsonl> <completed-signoff.json> --root .
```

The AI path requires `review_policy=phase5-ai-owner-v1`, actual AI task/model
identity, source-based per-row findings and physical audit/source bindings.
`owner_authorization` records permission to change policy; `owner_approval`
separately approves the frozen benchmark and `review_bundle_sha256`. A reused
policy decision, pre-review approval, stale bundle, unresolved temporal finding
or AI evidence relabeled human fails closed. Whole-document absence requires
whole-document source scope. A justified temporal abstention can explicitly
record an undeterminable date without pretending to know it. The
[policy](../grounding/phase5_ai_review.md) describes the fields and limits.

Current observations/proposals are in
`evaluation/results/phase5-owner-ai-review-20261016/`. They retain all400 original
records and expose202 design/source issues; they do not approve the original
annotations or the proposed corrections. No provider calls were added by this
policy migration. Other phases retain their existing review requirements.

For the owner-approved exposed benchmark, use `--acceptance-scope phase5_acceptance`
with annotation-signoff validation, native scoring and report validation. This is
an explicit operator choice; a report cannot select its own validation scope.
Default validation and public release packaging still require fresh holdout data.

Serving can use the same pinned calibration as native evaluation. Set both
`CAMPUSAI_ANSWER_CALIBRATION` (artifact path) and
`CAMPUSAI_ANSWER_CALIBRATION_SHA256` (its checksum). The launcher rejects a missing
pair, invalid checksum or non-dev artifact before loading provider/retrieval
dependencies. With neither set, serving retains the default heuristic confidence.

The22/10 Phase5 checkpoint stopped at observed provider quota500 requests/day.
Do not reset its ledger/circuit, rotate keys or relabel429 outcomes as successful
absence answers. The owner-selected60-second qualification profile is isolated
from application defaults; it does not change prompt, model or retry count.
HTTP503 recovery remains disabled as the owner explicitly declined it. Preserve
all failed requests and raw captures; a failed or completed ID is not an
unattempted continuation. Check the [terminal manifest](../../evaluation/results/phase5-acceptance-20261021/manifest.json)
before any subsequent qualification. That manifest separates the frozen native
actor from newer tested main-workspace repairs; older captures do not qualify
new runtime code. Existing question-content approval is complete for Phase5.

The PDF source-scope extension is implemented and opt-in only through
`llm.allow_pdf_scope`; `configs/free_llm.yaml` remains unchanged. It requires the
existing durable quota and `max_retries=0`, measures the pinned complete request,
then admits at most one generation. Exact body/endpoint/binary checks apply in
native collection. Keep measurement POSTs in the call budget and journal; count
only returned generation outputs as model responses. The separately authorized
two-POST capability probe has not run while the shared daily quota is exhausted.

The current root-source repair index is `.tmp/phase5-current-native-v14-index-20261022`,
paired with `.tmp/phase5-current-native-v14-store-20261022`. It contains the
same14 physical PDF identities, rebuilt with `structure-v5` and
`table-v3-inherited-multipage-course-columns`, BGE-M3 revision1 on CUDA, with
provider calls disabled. Its manifest SHA-256 is
`13523be6ca09e6e54126ae40c596df00f01cd877f02f5692b0d03045aa38111a`; physical
index integrity passes. Same-hash stored documents are now reparsed when the
parser, chunker or table-extractor version is stale, then reindexed. The MAI
joint-curriculum table now carries the explicit “Semester 4” scope and verified
credits header through retrieval. The current-source dev egress packet is
`evaluation/results/phase5-current-native-qualification-20261022/dev-egress/egress.json`;
it records zero provider posts and remains pending authorization. Historical
v13 indexes, captures and calibration remain immutable and do not qualify the
current source.
