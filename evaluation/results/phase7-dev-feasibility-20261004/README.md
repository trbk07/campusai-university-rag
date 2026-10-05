# Phase 7 dev feasibility study — 2026-10-04

This is conditional dev research, not release acceptance. The r18 benchmark,
failed M2 report, consumed test/holdout and release selector are unchanged.
No new test/holdout was opened or created for this study. See the authoritative
[roadmap](../../../plan.md) and [joint result](joint_dev_feasibility.json).

## Measured findings

The two-feature query-operation router now distinguishes single lookups from
multiple requested outputs. The serialized grammar version is v3; v2 artifacts
are rejected. Normal fast retrieval now prioritizes complete course names in
explicit table subject columns without calling a cross-encoder. Source scope
requires local support for graduation-grade and grade-registration relationships.
There are no qids, gold labels, difficulty labels or fixed document identities
in these serving changes.

| Actual GPU cap-10 experiment | Positive Recall@5 | Negative FPR | Evidence policy |
|---|---:|---:|---|
| Before normal fast-table priority, 478 dev | 0.669841 | 2/163 | score; infeasible |
| After fast-table priority, 478 dev | 0.980952 | 2/163 | score; infeasible |
| After relationship scope, 478 dev | 0.980952 | 1/163 | score; feasible, returns baseline quality |
| Audited exposed-dev probe, 491 dev | 0.980952 | 1/176 | v1 probability; fitted and grouped OOF feasible |

The probe reuses 13 already exposed r12 dev-only questions, with their existing
owner-directed AI origin and reconstructed scoped absence proofs. These cover
fee waiver, examination schedules and teaching rooms in three connected
template families. [Provenance](exposed_dev_probe/provenance.json) binds the
exact parent data and authorization; these records are not fresh heldout.
The primary r18 dev alone has only one scored no-evidence example and cannot
fit the required three-class probability policy; the failed class audit is
retained. No evidence schema change was applied.

On the probe, 150 requests were actually scored with BGE-reranker-v2-m3,
revision `1427fd652930e4ba29e8149678df786c240d8825`, FP16 CUDA:0, length 512,
batch 8, cap 10 and `body_table_window`. Classes are 10 absent / 15 partial /
125 sufficient. Fitted and five-fold grouped OOF Recall@5 are 309/315 and FPR
1/176. Routing hard recall is 124/126 and easy unnecessary rate 15/168,
also reproduced in grouped OOF. No inference errors occurred; measured rerank
p95 is 163.18 ms. This single cap does not substitute for the required five-cap
sweep, M6 quality uplift, end-to-end latency, capacity or staging acceptance.

The final regression suite passed 763 tests, skipped two opt-in live LLM tests,
and reached 89.51% coverage. Raw JUnit and coverage are in `verification/`.
The skips are not counted as live LLM evidence. The dev-comparison hook was
updated to forward the new table option, with a regression test checking
restoration of the hook. This post-measurement script change does not rebind
earlier model observations; their original source snapshot remains archived.

## Exact-byte archive and reproduction

`archive_manifest.json` binds four gzip archives to the original raw JSON SHA-256
and byte lengths. Compression copies binary bytes, without JSON reserialization.
All 157,799,250 restored raw bytes were hash-checked. Original large JSON files
remain locally available and are ignored only in this directory. Restore with
Python `gzip.open(archive, 'rb')` and `shutil.copyfileobj` to the declared
`restored_path`, then verify its SHA-256 before use.

`measured_source.zip` and its manifest contain the exact physical source and
runtime description of the final experiments. This is a historical worktree
snapshot, including pre-existing uncommitted helper code, not a clean release
commit. The local credential config is excluded. The source archive SHA and
each member hash are recorded. Reproduction helpers are stored as `.py.txt`
under `reproduction/` to avoid changing the evaluated source identity. Copy
them into `.tmp` before running with `PYTHONPATH=.;src`; never overwrite
accepted evidence with an exploratory output. Use separate output paths for
new experiments. Existing raw reports bind exact dev/index/model/calibration
hashes, so restoring different source or data cannot qualify them for release.

Actual collection commands used the offline GPU interpreter with
`HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`:

```powershell
.tmp\phase7-gpu-runtime\Scripts\python.exe -m evaluation.reranker.calibrate_hard_query_route --dev evaluation/results/phase7-dev-feasibility-20261004/exposed_dev_probe/human_retrieval_dev.jsonl --index-dir .tmp/hybrid-index --phase6-calibration evaluation/results/hybrid_retrieval_calibration.json --exploratory --route-policy probability --output evaluation/results/phase7-dev-feasibility-20261004/route_exposed_dev_probe.json
.tmp\phase7-gpu-runtime\Scripts\python.exe -m evaluation.reranker.calibrate_reranker_scores --dev evaluation/results/phase7-dev-feasibility-20261004/exposed_dev_probe/human_retrieval_dev.jsonl --index-dir .tmp/hybrid-index --phase6-calibration evaluation/results/hybrid_retrieval_calibration.json --route-calibration evaluation/results/phase7-dev-feasibility-20261004/route_exposed_dev_probe.json --model-dir .tmp/models/1427fd652930e4ba29e8149678df786c240d8825 --device cuda:0 --dtype float16 --rerank-cap 10 --input-format body_table_window --evidence-policy probability --exploratory --output evaluation/results/phase7-dev-feasibility-20261004/cap10_probability_exposed_dev_probe.json
```

The CLI refuses a route artifact fitted on the other dev file. That provenance
rejection was resolved by collecting and fitting the actual 491-row route
before collecting its probability run; no report hashes were substituted.
Exploratory CLIs return exit 1 and status `conditional` even when dev thresholds
are feasible. That is expected, not a release PASS.

## Successor preparation

`successor_source_fact_audit.json` retains an unlabelled audit of unused text
triples corroborated by explicit credit columns in frozen source tables.
Twenty-four triples connect to only 15 subject groups, fewer than the minimum
10 positive groups in each future test/holdout even before dev allocation.
Exact name/code history matching alone does not prove semantic non-exposure.
These are proposals, not approved benchmark records or an exposure registry.
Additional independent source facts and full history audit are required.

The current release readiness remains conditional with M2 failed and no 10/10
score. After source review/commit, prepare enough independently eligible
source-fact families, carry the exposed dev probe forward as dev only, freeze
a new benchmark and measure M0–M12/S1–S6 in order with exact physical bindings.
