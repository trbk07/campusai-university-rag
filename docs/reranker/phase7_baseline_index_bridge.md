# Phase 7 baseline and expanded-index protocol

Status: design before F1; validator integration and expanded-baseline qualification remain open. This document grants no release PASS.

The historical RC3 baseline uses ten documents and commit `8e3a331838fbccaa16b4dd00381b9ed4738e958f`. The successor uses fifteen documents and the current retrieval implementation. Their index and calibration hashes differ. One hash cannot describe both measurements.

The historical baseline remains immutable. Two actual clean-worktree CPU8 reruns now reproduce every stable historical metric, both evaluator reports PASS, the freeze tool PASS, and the unmodified release validator PASS through M0 on the original index. Test/holdout Recall@5 remain 115/117 and 112/117, with FPR zero. Test p95 values are 358.006ms and 351.188ms. See [historical proof](../../evaluation/results/phase7-completion-20261004/p7-10-historical-two-reruns-20261007-v3.json) and [validator](../../evaluation/results/phase7-completion-20261004/p7-10-historical-m0-validator-20261007-v3.json).

The expanded baseline must qualify separately before any bridge is accepted:

1. Verify both physical index manifests and every original document file. All original BM25/dense bytes and manifest entries must be preserved; added sources need their existing source-review lineage. Losing or changing an original file fails the bridge.
2. Preserve the original calibration bytes. Bind the expanded calibration separately and disclose implementation/ordering changes; do not describe changed baseline outputs as historical reproduction.
3. Measure the current expanded baseline on the exact consumed historical generated regression inputs, with per-request evidence/traces and actual pinned dense-model revision/device. Fresh successor human test/holdout are excluded from this qualification.
4. Retain the original quality floors for the expanded baseline: generated test Recall@5 at least .98, holdout at least .95, FPR zero on both. Two complete reports must be deterministic in stable metrics and pass the existing evaluator, including its performance and contract checks. Preserve failed attempts.
5. Record the historical proof and expanded proof as distinct objects in a versioned bridge manifest. Bind reference/reruns/index/calibrations/source/runtime/model/benchmarks/physical-preservation/source-review hashes. Unsafe paths, missing raw evidence, or mismatched identities fail closed.
6. Before F1, implement and test explicit validator support. M0 must validate the original proof unchanged plus the complete bridge. M1 onward must bind the expanded release index and current baseline calibration. M6 paired baseline observations must come from the exact same frozen expanded implementation/index/request scope as Phase 7.
7. Bind the bridge protocol hash into F1 and the final release manifest. A historical M0 PASS cannot be copied onto the successor without these checks. Generated historical regressions remain disclosed as consumed regressions; fresh human primary sets remain the acceptance population.

No validator threshold is changed by this design. No report is overwritten. The successor selector and fresh human primary inputs remain untouched. If expanded qualification fails, retain the original historical PASS and keep the successor blocked.
