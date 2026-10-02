# Reranker implementation and release status

The optional retrieval reranker remains disabled by default. Production
activation requires a complete passing release manifest bound to installed
runtime code, model snapshot, index, device and calibration.

The implementation now includes sequential M0–M12 validation, independently
reviewed human benchmark intake, explainable dev-only routing, a five-cap
calibration sweep, paired generated/human test and holdout comparisons,
performance/capacity measurement, adversarial and grounding checks, controlled
failure injection, rollback across separate processes, and staging telemetry
auditing. Follow [the release runbook](reranker_release_runbook.md).

## Current evidence

| Gate | Current release evidence |
|---|---|
| M0 baseline | Historical RC3 and two frozen reruns preserved in `evaluation/results/retrieval_baseline_*` |
| M1 human benchmark | BLOCKED: canonical benchmark dataset, per-record scope/evidence metadata and frozen splits are absent |
| M2–M12 | Cannot advance until preceding gates PASS; code and unit fixtures do not replace measured artifacts |

The earlier generated-only exploration achieved candidate Recall@40 `1.0`
on test and `0.991453` on holdout, with no scope/provenance/duplicate errors.
Its route selected 89.3% of easy queries and CPU rerank p95 was roughly 10.8s.
Those historical exploratory observations do not satisfy the new release
contract and were not promoted into passing release evidence.

## Continuation measurements (2026-10-02)

The local RTX 4060 Laptop GPU (8 GB) is now available through the separate
`.tmp/phase7-gpu-runtime`, with PyTorch `2.14.0+cu126`. The CPU `.venv` was
preserved. A real offline snapshot probe produced identical repeated scores
(`max_score_delta=0`); it remains conditional exploratory evidence.

The latest real-corpus diagnostic used three hard **dev** questions and their
actual frozen Phase 6 candidates. GPU rerank-only latency was 229-345 ms at
cap 8, 243-398 ms at cap 10, and 288-487 ms at cap 20. Peak GPU allocation was
about 2.47 GB. These nine observations do not establish release p95/p99,
end-to-end latency, quality improvement or M7. Raw diagnostics are in
`.tmp/phase7-real-corpus-latency-gpu-current.json`; `release_eligible=false`.

Earlier code verification: **318 passed, 2 live LLM tests skipped**. The implementation
now includes separately bound question/review packets, live request/resource
collection, all eight staging rollback exercises, permanent-failure follow-up
checks, and an isolated staging collector command. Raw staging summaries and
frozen output coordinates are recomputed by the validator. Runtime identity
includes installed inference dependencies and distinguishes CPU/CUDA wheels.

The selected future free web GPU target and its quota constraints are recorded
in [the free GPU deployment decision](phase7_free_gpu_hosting.md). No public
Space or final release has been published. M1 remains blocked; M2-M12 need
their actual ordered measurements after that gate passes.

Human review is external input. No automatic question generation, placeholder
reviewer or fabricated staging window is used to satisfy M1/M11. The dataset
example in `configs/human_benchmark_record.example.json` deliberately has
pending review and incomplete fields, so it cannot pass validation.

## Optimization measurements (2026-10-02)

The precision, batch scheduler, bounded queue and calibration configuration now
carry explicit bindings. The production manifest also binds the measured
timeout, queue size, circuit limit and score-cache setting. Runtime transport
assigns request IDs on the server and validates document scope. Startup failure
and shutdown release provider resources. See the full measured comparison in
[the optimization report](phase7_optimization_report.md).

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

Final code verification: **374 passed, 2 live LLM tests skipped**, with
**88.15% coverage** (85% required), no test failures or resource warnings.
Compile and diff checks passed. Readiness remains conditional with a null
official score; code improvements do not substitute for the missing release
measurements.

The next measured loop is documented in [phase7_loop2_report.md](phase7_loop2_report.md).
Query-focused table inputs reached dev Recall@5 89.80% at cap 20 with 0/8
negative outputs; cap 40 reached 91.84%. Neither met the joint quality target.
The cap-20 BGE load probe failed at concurrency 5 and 20. GTE completed the
cap-10 concurrency-20 probe without errors but had weaker dev quality.
Table input transforms and GTE compatibility remain research-only.

[Loop 3](phase7_loop3_report.md) adds dev-calibrated low-score abstention as
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

`python -m evaluation.validate_reranker_release` rechecks hashes and evidence,
recomputes routing metrics, paired quality statistics, performance summaries
and staging decisions. It returns `score=10.0` only when every gate passes and
the tree is clean. `--through M0` is a partial baseline check and keeps the
score null. Runtime and test file names describe their task; phase numbers
remain in compatibility identifiers and report metadata where appropriate.
