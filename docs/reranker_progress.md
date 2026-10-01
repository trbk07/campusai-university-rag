# Reranker implementation and release status

The optional retrieval reranker remains disabled by default. Production
activation requires a complete passing release manifest bound to installed
runtime code, model snapshot, index, device and calibration.

The implementation now includes sequential M0?M12 validation, independently
reviewed human benchmark intake, explainable dev-only routing, a five-cap
calibration sweep, paired generated/human test and holdout comparisons,
performance/capacity measurement, adversarial and grounding checks, controlled
failure injection, rollback across separate processes, and staging telemetry
auditing. Follow [the release runbook](reranker_release_runbook.md).

## Current evidence

| Gate | Current release evidence |
|---|---|
| M0 baseline | Historical RC3 and two frozen reruns preserved in `evaluation/results/retrieval_baseline_*` |
| M1 human benchmark | BLOCKED: no independently reviewed human dataset supplied |
| M2?M12 | Cannot advance until preceding gates PASS; code and unit fixtures do not replace measured artifacts |

The earlier generated-only exploration achieved candidate Recall@40 `1.0`
on test and `0.991453` on holdout, with no scope/provenance/duplicate errors.
Its route selected 89.3% of easy queries and CPU rerank p95 was roughly 10.8s.
Those historical exploratory observations do not satisfy the new release
contract and were not promoted into passing release evidence.

Human review is external input. No automatic question generation, placeholder
reviewer or fabricated staging window is used to satisfy M1/M11. The dataset
example in `configs/human_benchmark_record.example.json` deliberately has
pending review and incomplete fields, so it cannot pass validation.

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
0?1?5?10?25%, with three healthy windows per step. Auto-rollback monitors
latency, timeout, FPR, errors, memory, citation, scope and provenance.

## Validation authority

`python -m evaluation.validate_reranker_release` rechecks hashes and evidence,
recomputes routing metrics, paired quality statistics, performance summaries
and staging decisions. It returns `score=10.0` only when every gate passes and
the tree is clean. `--through M0` is a partial baseline check and keeps the
score null. Runtime and test file names describe their task; phase numbers
remain in compatibility identifiers and report metadata where appropriate.
