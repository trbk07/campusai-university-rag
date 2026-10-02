# Phase 7 AI research: measured limitations

This work adds the 480-row natural-input dataset described in
`data/benchmark/README.md`, plus a separate 159-question frozen-PDF real-model
research probe. Neither is an independently reviewed human benchmark or a
passing Phase 7 release artifact. Future uploaded PDFs and their answers remain
unknown; source files are evaluation fixtures, not application knowledge.

The first probe ran locally on the RTX 4060 Laptop GPU with the pinned
BAAI/bge-reranker-v2-m3 snapshot, offline, float32. Raw artifacts are in
`.release/reranker/studies/ai-gpu-v1`, including the dev freeze, five cap trials,
paired per-query outputs, actual latency samples and resource gauges.
It fitted dev only and froze before held-out evaluation. This probe used the
159-question set, **not** the later 480 natural inputs.

Results expose real quality problems beyond the missing human sign-off:

- Dev Phase 6 any-gold Recall@5: 0.8367; MRR (top-five calibration): 0.6412.
- Dev unsupported-query false-positive rate: 7/8, or 0.875. Reranking preserves
  Phase 6 fallback, so no score/margin threshold can fix that baseline rate.
  All five score fits correctly reported infeasible. No policy was promoted.
- Dev route hard recall: 0.5455; easy unnecessary reranking: 0.2727. This fails
  the 0.95/0.20 route target. Do not label the chosen diagnostic route passing.
- Ungated shadow ranking at cap 20 raised dev Recall@5 to 0.8776 and MRR to
  0.7048. These are exploratory dev results and do not establish held-out
  significance or satisfy the unsupported-query gate.
- Actual dev rerank-only p95 ranged from 361 ms (cap 8) to 675 ms (cap 20).
  End-to-end dev p95 for the conservative diagnostic policy was 944 ms.
- GPU peak allocated/reserved memory: approximately 2.47/2.74 GB.

The 100-request concurrency-5 profile triggered real timeouts and circuit
rollback; p95 was 1,396 ms. The first concurrency-20 profile inherited that
rollback and measured Phase 6 fallback, **not active reranker capacity**. It is
not eligible to prove reranker performance. The runner now closes/drains and
creates a fresh provider before each profile, recording start state and any
rollback during the profile. A new attempt is required to remeasure with this
fix. Old raw evidence is preserved rather than overwritten.

The curated 159-question source also corrects an AI annotation mistake for
collective-contribution awards: the source requires no course below D, not C+,
and Excellent training plus an eligible role. The old study remains bound to
its original dataset; its metrics measured evidence retrieval, not answer-text
accuracy. This illustrates why AI-authored labels need independent review.

Next measurements should use the natural inputs unchanged, with explicit
upload/conversation/selection scope. Inspect abstention and full multi-evidence
coverage, not just one matching chunk. Fix and calibrate on dev, then freeze a
new study before examining its held-out data. Keep failed evidence and the
independent human M1 gate visible; these findings do not justify a 10/10 score.
