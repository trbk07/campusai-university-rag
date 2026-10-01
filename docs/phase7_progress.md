# Phase 7 reranker progress (not a release)

Phase 7 is opt-in and remains **disabled** until a dev-only reranker calibration
artifact passes. The Phase 6 `auto`/`hybrid_rrf` path remains the production
default, including exact-code routing, abstention, document scope and citation
provenance. No Phase 7 result is claimed as 10/10 or ready for Phase 8.

## Gates measured so far

| Gate | Result | Evidence |
|---|---|---|
| M0: freeze Phase 6 RC3 | PASS | `evaluation/results/phase7_baseline_*` |
| M1: offline provider contract | Unit/integration pass | `tests/test_phase7_*` |
| M2: hard-query route | CONDITIONAL | `.tmp/phase7-route-calibration.json` |
| M3: candidate Recall@40 | PASS | `.tmp/phase7-candidate-recall.json` |
| M4–M12: calibration, quality, load, staging, rollback | Pending | No release artifacts |

M0 used two full reruns from a clean worktree at commit `8e3a331`, the
historical RC3 report, and hashes for benchmark, corpus, index, calibration,
and the local BGE-M3 model snapshot. The two reruns reproduced test
Recall@5 `0.982906`, holdout Recall@5 `0.957265`, test MRR `0.808689`,
nDCG@5 `0.851988`, and negative FPR `0`. The earlier Phase 6 candidate with
a different logistic calibration is recorded as a *different-calibration*
rejected baseline, not silently substituted for RC3.

M3 measured Phase 6 candidate generation **before** reranking: Recall@40 was
`1.0` on 117 answerable test records and `0.991453` on 117 answerable holdout
records. Scope, provenance, and duplicate-result errors were zero. This is
candidate coverage, not reranked quality.

The first explainable route used top confidence and top-1/top-2 RRF margin,
fitted only on the dev split. It selected 100% of eligible hard queries but
also 89.3% of easy queries; the required easy unnecessary-rerank rate is at
most 20%. The generated dev set strongly couples difficulty with language
and template. Tuning a rule to those labels would not establish general
human-natural routing quality. M2 therefore remains conditional.

An exploratory dev-only reranker calibration with the local cross-encoder,
candidate generation at 40, and reranking the top 10 improved MRR from
`0.762336` to `0.788791` and nDCG@5 from `0.796642` to `0.816295` on this
generated dev split, with unchanged Recall@5 `0.912698` and negative FPR `0`.
It remains **conditional**: the route failed M2, dev Recall@5 is below the M4
`0.95` floor, and no test/holdout quality result has been claimed. CPU rerank
p95 over 79 selected dev requests was `10,844.58` ms, far over budget. The
exploration is at `.tmp/phase7-reranker-calibration-candidate.json`.

Potential sources of naturally worded UET questions, plus the evidence and
independent-review intake requirements, are recorded in
[`phase7_human_natural_sources.md`](phase7_human_natural_sources.md). This is
not yet a reviewed challenge set.

`evaluation/validate_phase7.py` is a fail-closed final gate. It requires the
passing route and reranker calibration, paired test/holdout quality,
50-case adversarial/security evidence, Phase 4/5 grounding regression,
resource headroom, rollback, staging, and a clean tree. Its current output is
`conditional`; missing reports are not filled with placeholder PASS values.

## Provider and performance limits

`OfflineCrossEncoderReranker` requires an explicit local model snapshot,
revision, and SHA-256 of its contents. It uses a process-wide singleton,
bounded one-worker queue, batch scoring, token/input limits, timeout, and a
circuit breaker. An invalid score, model hash, timeout, or queue-full event
causes a Phase 6 fused-ranking fallback. The reranker cannot introduce a
candidate outside the Phase 6 candidate set; provenance is checked again
before results leave the retriever.
Raw cross-encoder logits are retained only as internal `reranker_score`
evidence. The public retrieval `score` remains the Phase 6 fused score, so
grounding does not mistake an uncalibrated logit for factual confidence.

The offline CPU smoke test for `BAAI/bge-reranker-v2-m3` succeeded, but its
warm inference latency was about 702 ms for 10 candidates, 1,349 ms for 20,
and 2,686 ms for 40. Model load/first request was about 13.4 s. These are
single smoke observations, not p95 measurements. Reranking all 40 candidates
already exceeds the proposed 1,000 ms hard-query p95 budget on this CPU;
the total request also includes Phase 6 retrieval. The policy supports a
dev-fitted rerank subset (up to 40) while candidate generation remains fixed
at 40, but no smaller subset is authorized for release until quality and
latency are measured together. A GPU/stronger deployment profile may be
required.

## Activation contract

`build_phase7_retriever(...)` reads `RERANKER_ENABLED=false` by default.
Only `RERANKER_MODE=hard_only` is supported. Enabling additionally requires
`RERANKER_MODEL`, `RERANKER_MODEL_REVISION`, `RERANKER_MODEL_SHA256`,
`RERANKER_TOKENIZER_REVISION`, `RERANKER_MODEL_DIR`, and
`RERANKER_CALIBRATION`; resource options include `RERANKER_TIMEOUT_MS`,
`RERANKER_BATCH_SIZE`, `RERANKER_QUEUE_LIMIT`, and
`RERANKER_CANDIDATE_CAP=40`. `RERANKER_DEVICE=cpu` is the default; an explicit
`cuda` or `cuda:N` device is supported but requires a calibration artifact
bound to that device and a separate GPU performance run. The calibration must bind the exact model
identity, index, Phase 6 calibration and dev benchmark hashes. Any activation
error leaves the Phase 6 retriever running and records a path-free rejection
reason. The service's answer cache includes the Phase 7 model/policy
fingerprint when the feature is active, so rollback cannot reuse a reranked
answer under the Phase 6 cache key.

No passing Phase 7 reranker calibration artifact exists yet, so the feature
flag must stay off in deployment. Next: obtain a human-natural dev set for
hard-query routing, calibrate score/margin on dev only, compare quality on
locked test/holdout with paired statistics, then run negative, grounding,
performance, rollback, staging and clean-release gates.
