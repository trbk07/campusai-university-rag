# Phase 7 continuation — 07/10/2026

Roadmap: [plan.md](../../plan.md). Execution order and acceptance requirements:
[P7-01–P7-20](phase7_completion_plan_20261004.md).

P7-01–05 and P7-07 were already DONE. Work resumed at P7-06. No additional
whole task or release gate is declared complete by the following component work.
The historical r18 result remains M0/M1/S1 PASS and M2 FAIL (3/19).

## Latest execution checkpoint

The second exact authorized pilot completed 8/8 calls. Original live answers fail quality (75% accuracy; 87.5% citation precision). The source-bound local replay after quote and credit-citation repairs passes four positive pairs at 100%; no new provider calls were made and this is not fresh final-policy acceptance. Both packet-specific permissions are exhausted. Source-headed credit arithmetic passes 110 tests and four real-source component cases; these bypass retrieval and do not establish multihop release acceptance.

The actual BGE source-context study is complete: nested MRR uplift -0.01887%, nDCG uplift +0.04387%; confidence limits include zero. An independent release-comparator audit matches metrics with zero provenance/scope/citation/duplicate violations. [Canonical summary](../../evaluation/results/phase7-completion-20261004/p7-09-source-context-bge-dev-20261007.json) binds the raw studies and exact v8 source archive. The failed policy is not promoted. Verified GTE inference on the same 829 dev inputs and actual baseline is complete: OOF MRR -0.09435%, independent metric audit PASS; policy not promoted. Its weights and custom implementation are bound to two pinned public upstream revisions. No heldout query was opened.

## Source review and dev revision

The analyst examined the frozen source bodies and direct code/name/credit table
rows for `human-candidate-0156` through `human-candidate-0180`. Nine original
golds are incomplete or point to unrelated/prerequisite content: 0156, 0157,
0163, 0164, 0165, 0177, 0178, 0179, 0180. The other sixteen are retained.
English translation/case variants in repeated rows are recorded without treating
them as conflicting credit values.

[Review decisions](../../data/benchmark/phase7_dev_gold_revision_20261007/review_decisions.json)
attribute the review to Codex under the existing owner-delegated authorization.
They do not claim manual owner review or independent human review.

The [revision manifest](../../data/benchmark/phase7_dev_gold_revision_20261007/packet/manifest.json)
binds all 829 dev rows, nine replacements, and a partial rubric of 50 claims for
25 questions. Questions, original authorship, scope and connected groups remain
unchanged. Every revision row is release-ineligible. Corrected rows have their
old approval cleared; the parent approval is retained in the source-review audit.
This separate research revision does not alter r19b F0, original labels, exposure,
or historical measurements. It requires explicit revision-lineage integration
before any future release use. The remaining 804 rows do not gain rubric approval.

Reproduction, from the repository root:

```powershell
.venv/Scripts/python.exe -m scripts.benchmarks.prepare_phase7_dev_gold_revision --parent-dev data/benchmark/phase7_review_cycles/phase7-successor-20261005-r19b/human_retrieval_dev.jsonl --index-dir .tmp/phase7-curated-source-20261005-v2/index --decisions data/benchmark/phase7_dev_gold_revision_20261007/review_decisions.json --output-dir data/benchmark/phase7_dev_gold_revision_20261007/packet --verify
```

To reproduce into a new directory, replace `--output-dir` with a nonexistent
directory and omit `--verify`. The command validates the physical index and
recomputes all output bytes. It neither invokes models nor reads held-out queries.

Validation: 96 tests passed across dev-revision, source-course-generation,
dev-inheritance and benchmark-integrity contracts. Evidence:
[`p7-06-dev-gold-revision-tests-20261007.xml`](../../evaluation/results/phase7-completion-20261004/p7-06-dev-gold-revision-tests-20261007.xml).

## Live provider contracts

The two required live integration tests passed with zero skips using
`gemini-3-flash-preview` at `generativelanguage.googleapis.com`. Only the fixed
synthetic OK and graduation fixtures were sent; no benchmark/corpus data were
transmitted. Evidence:
[`report.json`](../../evaluation/results/phase7-completion-20261004/p7-06-live-contracts-20261007/report.json).

Re-run in a new output directory (calls the configured provider):

```powershell
.venv/Scripts/python.exe -m scripts.benchmarks.check_phase7_live_provider --config configs/gemini.yaml --output-dir evaluation/results/phase7-completion-20261004/p7-06-live-contracts-NEW
```

The runner does not print credentials; it redacts the exact credential from the
saved test log/XML. These two calls do not establish benchmark quality, available
load quota, provider cost, paired Phase 6/7 acceptance, or S4/S5.

## Expanded dev rubric and prepared pilot

The [expanded source rubric](../../evaluation/results/phase7-completion-20261004/p7-06-dev-source-rubric-20261007.json)
contains 653 claims for all 473 positive dev questions, with all 829 qids mapped.
Its source checks cover 110 manually authored source/context decisions, 25
course-name/credit decisions, 324 curriculum template replays, 300 expanded-index
code-absence proofs, and 25 explicit source-course inputs. The original v1 rubric
keeps 45 historical negative labels inherited from F0. The subsequent
[v2 rubric](../../evaluation/results/phase7-completion-20261004/p7-06-dev-source-rubric-20261007-v2.json)
adds explicit decisions for each of those 45 dev negatives, based on the empty
conversation, scoped source searches and interpretation of policy near matches.
The [decisions](../../data/benchmark/phase7_dev_gold_revision_20261007/negative_review_decisions.json)
distinguish incomplete referents/personal facts from unavailable scholarship,
registration, grade replacement and graduation GPA rules. Master's admissions
GPA and programme-specific language outcomes cannot establish those unrelated
or universal rules. This is attributable delegated AI review, not an independent
human review or an exhaustive mechanical semantic-absence theorem.
Credit-only and semester-only questions
require only the requested field; combined queries require both. No held-out
queries or model answers were used to author claims.

Reproduction:

```powershell
.venv/Scripts/python.exe -m scripts.benchmarks.build_phase7_dev_rubric --output evaluation/results/phase7-completion-20261004/p7-06-dev-source-rubric-20261007.json --verify
```

Replay passed. The additional rubric/revision/grounding suite passed 27 tests,
zero failures/errors/skips:
[`p7-06-dev-rubric-tests-20261007.xml`](../../evaluation/results/phase7-completion-20261004/p7-06-dev-rubric-tests-20261007.xml).

The [prepared egress packet](../../evaluation/results/phase7-completion-20261004/p7-06-paired-pilot-egress-packet-20261007.json)
contains exactly eight prompts (35,321 characters) for four source-reviewed dev
questions and two arms. It replays historical baseline and cap-20 reranked
retrieval; it is a grounding diagnostic, not current serving-policy acceptance.
The collector uses no cache, no retries and a maximum of eight Gemini calls.
The owner explicitly authorized exactly this packet in chat, bound in
[`egress authorization`](../../evaluation/results/phase7-completion-20261004/p7-06-paired-pilot-egress-authorization-20261007.json).
The authorized run used all eight calls, without retries: seven completed with
usage reported; the eighth failed with `LLMRateLimitError` and unknown usage.
All eight public responses abstained. The INT2013 baseline response retains two
source-supported factual claims but was rejected by deterministic grounding;
two other completed responses were rejected for invalid citations. This pilot
does not pass answer quality or establish usable load quota. Preserve its
[`raw observations`](../../evaluation/results/phase7-completion-20261004/p7-06-paired-pilot-actual-20261007.json)
via the artifact catalog. The eight-call authorization is exhausted, not a
blanket permission for another packet or benchmark run.

## Confirmed model provenance defect

The [origin audit](../../evaluation/results/phase7-completion-20261004/p7-09-model-origin-audit-20261007/origin_report.json)
confirms that the historical snapshot's weight SHA256 matches
`cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` at
`1427fd652930e4ba29e8149678df786c240d8825`. The same revision returns HTTP 404
for `BAAI/bge-reranker-v2-m3`. Local config has hidden size 384 and 12 layers;
the official [BGE config](https://huggingface.co/BAAI/bge-reranker-v2-m3/blob/953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e/config.json)
has hidden size 1024 and 24 layers. Historical files and observations remain
immutable; their old BGE label cannot establish upstream BGE provenance.

A separate verified BGE download completed at revision
`953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`, under
`.local_artifacts/models/bge-reranker-v2-m3/`. The downloader checks pinned Git
blob hashes for small files and LFS SHA256 for weights, without sending a token
or project data. Its [receipt](../../evaluation/results/phase7-completion-20261004/p7-09-verified-bge-download-20261007.json)
is `PASS_PINNED_PUBLIC_FILE_HASHES`, covering all six files including the
2,271,071,852-byte weights. `verified_model_origin` rechecks exact file membership,
metadata, sizes and hashes before inference. New reports identify the actual
upstream model; historical labels and observations remain immutable.

## Official BGE dev studies and nested replay

The [canonical study summary v2](../../evaluation/results/phase7-completion-20261004/p7-09-reviewed-bge-studies-20261007-v2.json)
binds real `body_table_window`, `body` and `section_body` CUDA/FP16/batch8 inference on the
reviewed 829-row dev packet. Each study has 472 nonempty queries and 17,084 scored
pairs, one model load, zero score-cache hits and zero provider failures. Provider
counters include one warmup (473 calls). Other requests have empty pools. All
source sets remained stable and have exact digest-verified ZIP snapshots,
excluding the credential config.

Candidate-pool order differs from Phase 6 search order; native weight-zero
ranking is therefore not the measured Phase 6 control. Three connected-group
outer folds fit routing and choose ordering/cap/weight exclusively on training
rows. Baseline-priority weight zero preserves exact Phase 6 partial/empty
results; a pool missing baseline evidence causes an explicit Phase 6 fallback
(one dev query), with no fabricated scores.

| Input | OOF MRR uplift | OOF nDCG uplift | Absolute MRR CI95% |
|---|---:|---:|---|
| body_table_window | +0.057% | +0.164% | [-0.000294, 0.001713] |
| body | -0.038% | +0.147% | [-0.003115, 0.001502] |
| section_body | 0% | +0.066% | [-0.000531, 0.000531] |

All retain Recall@5 97.89% and negative FPR 1/356. Window/body improve all-gold@5
from 95.98% to 96.41%; section_body gives 96.19%.
New-source dev alone has 25 rows/11 groups and window/body MRR +0.90%,
not +3%. Group bootstrap uses 10,000 resamples and seed 20261007. The aggregate
router has hard recall 95.78% and easy excess rerank 15.09%; fold 1 hard recall
is only 85.42%. No input has the required uplift or positive lower MRR CI.
This subset replay does not establish same-cap GPU timing, serving equivalence,
three-class evidence support, paired answer quality or any release gate.

Replay either input without GPU/provider calls (set `<S>` to the corresponding
score-study directory and use a **new** `<O>` under `.release/reranker/studies`):

```powershell
.venv/Scripts/python.exe -m scripts.benchmarks.analyze_phase7_ranking_replay --dev data/benchmark/phase7_dev_gold_revision_20261007/packet/human_retrieval_dev.jsonl --scores <S>/raw_dev_scores.json.gz --score-report <S>/dev_ranking_report.json --inheritance data/benchmark/phase7_review_cycles/phase7-successor-20261005-r19b/phase7_dev_inheritance.json --output-dir <O>
.venv/Scripts/python.exe -m scripts.benchmarks.build_phase7_reviewed_dev_rubric --output evaluation/results/phase7-completion-20261004/p7-06-dev-source-rubric-20261007-v2.json --verify
```

`<S>` is `.release/reranker/studies/phase7-reviewed-dev-bge-official-20261007-v1`
or `.release/reranker/studies/phase7-reviewed-dev-bge-body-20261007-v1`
or `.release/reranker/studies/phase7-reviewed-dev-bge-section-body-20261007-v1`.
The artifact catalog contains the studies, nested replays, independent audits,
finite-grid ceilings and exact source snapshots. Shared JSON/hash and
gzip readers verify absent paths from the artifact store. Source ZIPs restore
the exact experiment code for an isolated reproduction checkout; never extract
an old source snapshot over the active worktree. To remeasure inference, use
`score_phase7_successor_dev` with the receipt/revision-manifest/candidate-report
arguments and common dev/index/calibration/F0/raw bindings in the score report,
changing only input format and absent study output directory.

Independent `compare_split` recomputation passes for every input with zero
provenance/scope/invalid-citation/duplicate errors. Its Python random generator
and the replay's NumPy generator produce slightly different finite Monte Carlo
CI endpoints, with the same zero-crossing conclusion. Label-aware finite-grid
MRR oracle ceilings are window +2.337%, body +2.421%, section +2.299%, all below
+3%. These bounds apply only to the tried pool/order/cap/weight grid; they do
not prove impossibility for another model, format or retrieval policy.

## Historical baseline algorithm drift

Current retrieval measured on the original 140-row Phase 6 dev gives 110/126
positive hits (87.30%), FPR 0/14, both on the original ten-document index and on
the expanded index restricted to that same original corpus scope. Full expanded
scope previously gave 109/126. These threshold-applicability reports are not M0
or historical retention PASS. Source changes include body-BM25, table links,
source/table/course priorities and query/source routing; unchanged numerical
RRF parameters do not establish an unchanged algorithm.

The exact source from Git commit `8e3a331838fbccaa16b4dd00381b9ed4738e958f`,
isolated from current CampusAI imports, reproduces historical dev 115/126
(91.27%), FPR 0/14 in the current GPU environment. Every archive member is
verified against the original Git blob before use. The first Windows archive
had CRLF conversions and was rejected before inference; the exact archive was
created with `git -c core.autocrlf=false archive`. Both attempts are retained.
This dev result identifies algorithm drift, not an official test/holdout rerun,
M0 PASS or a replacement production baseline.

```powershell
.tmp/phase7-gpu-runtime/Scripts/python.exe -m scripts.benchmarks.measure_frozen_phase6_dev --dev data/benchmark/hybrid_retrieval_dev.jsonl --index-dir .tmp/hybrid-index --calibration evaluation/results/hybrid_retrieval_calibration.json --source-zip .release/reranker/studies/phase6-frozen-8e3a331-source-exact-20261007.zip --output-dir .release/reranker/studies/phase7-phase6-frozen-source-recheck-NEW
```

The latest review/provenance/replay contract run passes 39 tests:
[`JUnit`](../../evaluation/results/phase7-completion-20261004/p7-06-09-review-and-replay-tests-20261007.xml).

## Environment checkpoint

Earlier automatic approval review quota exhaustion has recovered; reviewed
escalated commands execute again. Normal sandbox initialization still fails
(`helper_unknown_error: setup refresh had errors`), so commands continue through
the existing reviewed escalation mechanism.

Remaining P7-06 work: integrate correction lineage before a future release,
review the failed authorized pilot and repair the observed grounding/provider
issues before another concrete pilot. P7-08/P7-09 and all F1/held-out acceptance
dependencies remain open, including historical expanded-index baseline retention
and a jointly feasible dev configuration. Official model provenance is resolved
for the new snapshot. No additional whole task or gate is marked PASS.

## Route bottleneck and historical reruns

[Oracle diagnostic](../../evaluation/results/phase7-completion-20261004/p7-09-route-unrestricted-rank-ceiling-20261007.json) shows that even perfect cap20 ranking under the current two-feature OOF router reaches at most +2.1323% MRR. A gold-aware route constrained to the same easy20% budget has an optimistic +5.5214% ceiling; gold is only used for the ceiling and cannot enter deployed routing. Improve observable routing before further model fitting. New-source-dev theoretical nDCG maximum is +2.2388%, so this cohort cannot support a +3% nDCG claim.

The clean exact Phase 6 worktree reproduces all original primary quality metrics. The first CPU1 run fails p95; a CPU4 rerun passes the original release evaluator, with test Recall@5 98.29%, holdout 95.73%, FPR zero and exact pinned dense revision. A second independent CPU4 rerun is underway. Strict M0/index validation is unchanged; no historical PASS has been transferred to the expanded index. The broad offline Phase 7/grounding/provider/hybrid suite passes 603 tests. The new twelve-prompt final-policy packet is locked and awaiting exact authorization; zero calls have been sent.


Latest update: exact final-pilot authorization granted; three unique attempts failed, nine unattempted remain with no retry. Latest journal is p7-06-final-policy-pilot-actual-20261007-continuation-continuation.json. CPU8 historical run A PASS, B running. Utility route v1 actual MRR unchanged; route-potential v1 hard coverage FAIL, oracle potential below3%. Current canonical handoff supersedes earlier running/pending-permission notes.

<!-- Phase 7 authoritative checkpoint 2026-10-08 -->
Phase 7 core checkpoint 2026-10-08 (current): 6/20 tasks DONE; active r18 M0/M1/S1 PASS and M2 FAIL (3/19). Full offline regression: 1086 passed, 2 opt-in live tests skipped; fixed a hardware-dependent CUDA unit test. Current 829-dev remeasurement is complete. One existing fitted candidate was replayed without training, selection, new inference or provider calls: original F0-dev MRR +0.03822% and nDCG@5 +0.14820%, both below the unchanged +3% target, with zero provenance/scope/citation/duplicate violations. Stable pilot has one failed call and 11 unattempted; automatic approval review rejected continuation before execution. Expanded historical regression still fails the 98%/95% recall floors. F1 and successor primary test/holdout remain closed. Owner approved RELEASE-BLOCKED (direct reply: ?t duy?t?): the qualification cycle is closed, Phase 6 is retained and the tested candidate branch is stopped. This does not mark the remaining 14 tasks or failed release gates PASS. See [core blocker report](../../evaluation/results/phase7-completion-20261004/p7-core-blocker-report-20261008.json) and [task ledger](../../evaluation/results/phase7-completion-20261004/completion_task_ledger.json). No new model/router/gold/storage study, pilot continuation or phase expansion is authorized by this closure.
