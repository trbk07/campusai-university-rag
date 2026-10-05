# Phase 7 M6 result: r15

Measured 2026-10-03 against frozen benchmark `phase7-dev-extension-20261003-r12`.
This is a source-bound summary of the M6 result; the full per-query artifacts remain
in the local `evaluation/results/phase7-source-context-20261003-r15/` directory.

| Binding | SHA-256 / value |
|---|---|
| Commit | `b6672cc6731aa899dbf891450dde420ee5f7248b` |
| Source | `a5bb97b23f265c381af3968fa48156ba4d606433d1da6470cbfcbc05687af382` |
| Runtime | `82cc3a73c6f926ab8902324436f45c033411bd716941b6bfbbf8d566494b0839` |
| Index manifest | `9952da0f42bde725d08c6a676ca260e70ac12313fa33c401ca6a387a90419f38` |
| Phase 7 calibration | `f7b1bd95809c2b09536e4fc131c5a2bd7ebc718646e0400c45f9ae11cf834827` |
| Model identity | `05f7d1cd2bd8618524cf04c9b40fdc7c88ee007c3e9523e3f7eebe2e6e2ede3e` |
| Quality report status | `conditional` |

| Split | Records | Recall@5 drop | MRR relative delta | nDCG@5 relative delta | Negative FPR |
|---|---:|---:|---:|---:|---:|
| test | 130 | 0.384615 | -41.9202% | -41.2199% | 0.0000 |
| holdout | 130 | 0.350427 | -33.7634% | -34.6031% | 0.0000 |
| human_test | 60 | 0.155556 | -16.8919% | -16.0863% | 0.0000 |
| human_holdout | 60 | 0.155556 | -14.2949% | -16.5398% | 0.0000 |

All four cohorts recorded zero provenance, scope, citation, and duplicate-result
violations. The failing gates are `quality_test_gate`, `statistical_significance_test_gate`,
`quality_holdout_gate`, `quality_human_test_gate`,
`statistical_significance_human_test_gate`, and `quality_human_holdout_gate`.

The quality workflow stopped at retrieval comparison, before paired answer
collection. No M6 Gemini answer calls were made. The held-out policy freeze is
retained; r15 must not be retuned. M7 remains gated. Use dev-only data for policy
work, then create a new reviewed benchmark cycle before another held-out study.
