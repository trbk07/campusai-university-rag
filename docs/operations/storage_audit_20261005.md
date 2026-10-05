# Phase 6/7 storage audit — 2026-10-05

The current tracked payload shrank from **2.862 GB** to **137.8 MB** (95.2% reduction). The workspace shrank from **20.387 GB** to **15.386 GB**. Existing Git history has not been rewritten, so GitHub publication still needs the separate history step below.

## Size accounting

| Scope | Before | After |
|---|---:|---:|
| Workspace, logical file bytes including `.git`/runtimes | 20.387 GB | 15.386 GB |
| `.git` physical file sizes | 291.60 MiB | 292.28 MiB |
| Currently tracked existing files | 2729.21 MiB | 131.41 MiB |
| Archived raw bytes | 2601.77 MiB | 279.57 MiB compressed/deduplicated |

The after snapshot counts current index entries, including the staged source, summaries, manifests and audit evidence. The migration is staged for review but has not been committed or pushed. Model/CPU/GPU runtimes remain ignored and retained for reproducibility. The two CUDA environments account for much of the remaining local disk use; they are not Git payload. A 2.623 GB redownloadable pip cache was removed. GPU setup now uses `--no-cache-dir` to prevent this duplication from recurring. No model or active runtime was deleted.

## Artifacts and bindings

**327 paths** were removed from tracking after streaming SHA256 verification. {'corpus_source': 22, 'full_evaluation_observations': 85, 'raw_evidence': 179, 'reproduction_archive': 12, 'index_archive': 5, 'source_visual_evidence': 24}. Exact paths, raw SHA256/size, compressed SHA256/size, URI, recorded identities and summary links are in [`manifest.json`](../../evaluation/artifacts/manifest.json). The complete removed-path list and 18 exact duplicate groups are in [`migration.json`](../../evaluation/results/storage-audit-20261005/migration.json). Compression/deduplication reduces their archival footprint by 2.435 GB. All corpus PDFs were restored as ignored active local inputs after archiving, so normal ingestion still finds the original paths. Generated raw reports stay in the local object store; legacy ZIP/gzip scripts can hydrate their original paths explicitly.

Small summaries preserve metrics and mark omitted raw arrays/text. They cannot satisfy a release gate by themselves. Original reports and historical hash bindings retain their exact byte identity. Phase 6 and Phase 7 readers, raw reference checks and measurement-receipt enumeration resolve missing logical files through the catalog; missing or corrupt evidence fails closed. Thresholds, inference, candidate selection, gold sets, source/runtime freeze receipts and split assignments are unchanged.

Verified **660 benchmark files**, including all human JSONL/gold references: zero hash changes. The owner-generation exposure metadata snapshot is intentionally retained in Git (9.54 MiB): it holds historical question references required for leakage review, not models, embeddings or full corpus chunks. Tracked weights = 0; serialized indexes/index archives = 0; recognized raw dumps/cache = 0. [`tracking-check.json`](../../evaluation/results/storage-audit-20261005/tracking-check.json) and `make storage-check` enforce this for the prospective index.

[`runtime-manifests.json`](../../evaluation/artifacts/runtime-manifests.json) verifies the accepted physical reranker snapshot and all 32 index files, with 15 documents / 1,175 chunks, corpus/model/builder hashes and a hash-bound index archive. Exact re-download by a model label is **not** claimed: the historical smoke report's BGE name differs from the mMiniLM-derived config in the accepted physical snapshot. The storage change preserves the recorded snapshot instead of changing inference. Resolve this existing provenance/naming issue separately before claiming upstream model reproducibility.

## Validation

Full offline suite: **905 passed, 2 live-provider tests skipped, 1 deselected**. The deselected ingestion test `test_cuda_without_hardware_is_blocked_without_loading_models` assumes unavailable CUDA, while this machine has an RTX 4060; it attempted real Hugging Face loading. No Phase 6/7 test was excluded. A subsequent OCR run with the actual restored corpus passed (1 test); the initial full run had no local OCR corpus and its test returned early. Focused storage/Phase 7 tests: 68 passed. Phase 6 storage/manifest tests: 13 passed. All 327 artifact objects were independently decompressed and verified without retaining materializations.

The official Phase 7 validator returns the same gate/supplemental statuses, errors, evidence hashes, overall status and score before/after storage migration. It remains conditional, with M2 FAIL; the storage task does not claim release PASS. Source-tree hashes naturally differ because the evidence-reading code changed. See [`validator-comparison.json`](../../evaluation/results/storage-audit-20261005/validator-comparison.json), [`verification.json`](../../evaluation/results/storage-audit-20261005/verification.json) and retained JUnit XML in that directory. The first broad test attempt exposed three Phase 6 fixture failures after raw extraction; those were fixed by resolving the original bytes and keeping every original assertion.

`.gitignore` now excludes the local store, raw/exploratory directories, model weights, NumPy/FAISS/pickled indexes, HF/dependency caches, raw archives, profiler outputs and exact legacy raw paths. Restored files remain ignored. `plan.md` stays tracked. Temporary test directories and the materialization cache were cleaned; original historical baseline artifacts and both runtimes remain intact. The unrelated untracked shell-named file present at task start was left untouched.

## Git history and safe next step

History still contains **10 paths** above GitHub's 100 MiB per-file limit. GitHub applies the limit to Git objects, so a small pack and deleting files in a later commit do not make them pushable. [GitHub large-file policy](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github).

- `evaluation/results/candidate_coverage.json`
- `evaluation/results/phase7-completion-20261004/p7-09-full-dev-reranker-raw-v2.json`
- `evaluation/results/phase7-completion-20261004/p7-09-reranker-dev-raw.json`
- `evaluation/results/phase7-completion-20261004/p7-09_successor_dev_baseline_report-v3.json`
- `evaluation/results/phase7-completion-20261004/p7-09_successor_dev_baseline_report-v4.json`
- `evaluation/results/phase7-completion-20261004/p7-09_successor_dev_baseline_report.json`
- `evaluation/results/phase7-source-context-20261003-r15/candidate_coverage.json`
- `evaluation/results/phase7-source-context-20261003-r16/candidate_coverage.json`
- `evaluation/results/phase7-source-context-20261003-r17/candidate_coverage.json`
- `evaluation/results/phase7-source-context-20261004-r18/candidate_coverage.json`

The exact proposed removal list is [`history-remove-paths.txt`](../../evaluation/results/storage-audit-20261005/history-remove-paths.txt); historical object IDs and sizes are in [`history-inventory.json`](../../evaluation/results/storage-audit-20261005/history-inventory.json). The proposal selects 5449 unique blobs totaling 3.351 GB uncompressed and about 281.77 MiB stored object bytes. Actual recovered `.git` size requires measuring a filtered/repacked copy; retained refs/deltas can change it. Historical `frontend/node_modules` and PDF payloads are included. No remote was contacted or changed and no history rewrite/force-push was performed. `git filter-repo` is not currently installed.

First review/commit this migration, back up the current repo and artifact objects, then work only on a new mirror:

```powershell
git clone --mirror --no-local D:/Project D:/Project/.local_artifacts/history-clean.git
git -C D:/Project/.local_artifacts/history-clean.git filter-repo --invert-paths --paths-from-file D:/Project/evaluation/results/storage-audit-20261005/history-remove-paths.txt
```

Install `git-filter-repo` in a separate tool environment if needed. Inspect the filtered mirror and its commit map, rerun the large-object audit and test a clean clone with the artifact bundle before any publication. **Do not force-push either existing remote automatically.** The repo has `origin` (old finance project) and `new-origin` (CampusAI); use the CampusAI target deliberately after review. Historical release manifests contain commit ancestry checks; filtering changes commit IDs, so their original audit history must remain preserved and any new release baseline must be measured/fingerprinted on the intended clean source. Do not relax ancestry checks or invent new provenance to make them pass.

## Top 20 files before

| MiB | Path |
|---:|---|
| 2501.65 | `.tmp/pip-cache/http-v2/c/2/4/f/5/c24f5e603cd2d3a5a4816cb1d623c6864c1ad521057b03775d32d98d.body` |
| 1011.32 | `.tmp/phase7-gpu-runtime/Lib/site-packages/torch/lib/torch_cuda.dll` |
| 1011.32 | `.venv/Lib/site-packages/torch/lib/torch_cuda.dll` |
| 583.59 | `.tmp/phase7-loop-snapshots/Alibaba-NLP--gte-multilingual-reranker-base/8215cf04918ba6f7b6a62bb44238ce2953d8831c/model.safetensors` |
| 507.18 | `.tmp/phase7-gpu-runtime/Lib/site-packages/torch/lib/cublasLt64_12.dll` |
| 507.18 | `.venv/Lib/site-packages/torch/lib/cublasLt64_12.dll` |
| 490.12 | `.tmp/phase7-gpu-runtime/Lib/site-packages/torch/lib/cudnn_engines_precompiled64_9.dll` |
| 490.12 | `.venv/Lib/site-packages/torch/lib/cudnn_engines_precompiled64_9.dll` |
| 448.79 | `.tmp/hf-download/models--cross-encoder--mmarco-mMiniLMv2-L12-H384-v1/snapshots/1427fd652930e4ba29e8149678df786c240d8825/model.safetensors` |
| 448.79 | `.tmp/models/1427fd652930e4ba29e8149678df786c240d8825/model.safetensors` |
| 448.79 | `.tmp/phase7-models/1427fd652930e4ba29e8149678df786c240d8825/model.safetensors` |
| 448.79 | `.tmp/phase7-finetune-prototype/model.safetensors` |
| 291.82 | `.tmp/phase7-gpu-runtime/Lib/site-packages/torch/lib/torch_cpu.dll` |
| 291.82 | `.venv/Lib/site-packages/torch/lib/torch_cpu.dll` |
| 274.32 | `.tmp/phase7-gpu-runtime/Lib/site-packages/torch/lib/cusparse64_12.dll` |
| 274.32 | `.venv/Lib/site-packages/torch/lib/cusparse64_12.dll` |
| 269.36 | `.tmp/phase7-gpu-runtime/Lib/site-packages/torch/lib/cudnn_adv64_9.dll` |
| 269.36 | `.venv/Lib/site-packages/torch/lib/cudnn_adv64_9.dll` |
| 267.44 | `evaluation/results/phase7-source-context-20261004-r18/candidate_coverage.json` |
| 264.50 | `.tmp/phase7-gpu-runtime/Lib/site-packages/torch/lib/cufft64_11.dll` |

## Top 20 directories before (nested totals overlap)

| MiB | Path |
|---:|---|
| 10117.40 | `.tmp` |
| 4849.32 | `.venv` |
| 4846.72 | `.venv/Lib/site-packages` |
| 4846.72 | `.venv/Lib` |
| 4069.96 | `.tmp/phase7-gpu-runtime` |
| 4068.97 | `.tmp/phase7-gpu-runtime/Lib/site-packages` |
| 4068.97 | `.tmp/phase7-gpu-runtime/Lib` |
| 4052.62 | `.tmp/phase7-gpu-runtime/Lib/site-packages/torch` |
| 4021.85 | `.venv/Lib/site-packages/torch` |
| 3900.70 | `.tmp/phase7-gpu-runtime/Lib/site-packages/torch/lib` |
| 3900.70 | `.venv/Lib/site-packages/torch/lib` |
| 2574.34 | `evaluation` |
| 2570.86 | `evaluation/results` |
| 2501.83 | `.tmp/pip-cache/http-v2` |
| 2501.83 | `.tmp/pip-cache` |
| 2501.65 | `.tmp/pip-cache/http-v2/c/2/4/f/5` |
| 2501.65 | `.tmp/pip-cache/http-v2/c/2/4/f` |
| 2501.65 | `.tmp/pip-cache/http-v2/c/2/4` |
| 2501.65 | `.tmp/pip-cache/http-v2/c/2` |
| 2501.65 | `.tmp/pip-cache/http-v2/c` |

## Top 20 currently tracked files before

| MiB | Path |
|---:|---|
| 267.44 | `evaluation/results/phase7-source-context-20261004-r18/candidate_coverage.json` |
| 201.84 | `evaluation/results/phase7-completion-20261004/p7-09-full-dev-reranker-raw-v2.json` |
| 201.84 | `evaluation/results/phase7-completion-20261004/p7-09-reranker-dev-raw.json` |
| 161.42 | `evaluation/results/phase7-source-context-20261003-r16/candidate_coverage.json` |
| 161.42 | `evaluation/results/phase7-source-context-20261003-r17/candidate_coverage.json` |
| 159.69 | `evaluation/results/phase7-completion-20261004/p7-09_successor_dev_baseline_report-v3.json` |
| 159.63 | `evaluation/results/phase7-completion-20261004/p7-09_successor_dev_baseline_report-v4.json` |
| 159.56 | `evaluation/results/phase7-completion-20261004/p7-09_successor_dev_baseline_report.json` |
| 158.28 | `evaluation/results/phase7-source-context-20261003-r15/candidate_coverage.json` |
| 126.98 | `evaluation/results/candidate_coverage.json` |
| 56.34 | `evaluation/results/phase7-completion-20261004/p7-09-nested-quality-recompute.json` |
| 52.54 | `evaluation/results/phase7-completion-20261004/p7-09-nested-joint-oof-v2.json` |
| 44.59 | `evaluation/results/phase7-source-context-20261003-r15/retrieval_quality_comparison.json` |
| 28.57 | `evaluation/results/phase7-source-context-20261003-r15/reranker_cap_trials/cap-20.json` |
| 28.57 | `evaluation/results/phase7-source-context-20261003-r14/reranker_cap_trials/cap-20.json` |
| 28.30 | `evaluation/results/phase7-source-context-20261003-r17/reranker_cap_trials/cap-20.json` |
| 25.31 | `evaluation/results/phase7-source-context-20261003-r14/reranker_cap_trials/cap-16.json` |
| 25.31 | `evaluation/results/phase7-source-context-20261003-r15/reranker_cap_trials/cap-16.json` |
| 25.16 | `evaluation/results/phase7-source-context-20261003-r17/reranker_cap_trials/cap-16.json` |
| 22.94 | `evaluation/results/phase7-completion-20261004/p7-09_successor_order_grouped_oof.json` |

## Top 20 files after

| MiB | Path |
|---:|---|
| 1011.32 | `.tmp/phase7-gpu-runtime/Lib/site-packages/torch/lib/torch_cuda.dll` |
| 1011.32 | `.venv/Lib/site-packages/torch/lib/torch_cuda.dll` |
| 583.59 | `.tmp/phase7-loop-snapshots/Alibaba-NLP--gte-multilingual-reranker-base/8215cf04918ba6f7b6a62bb44238ce2953d8831c/model.safetensors` |
| 507.18 | `.tmp/phase7-gpu-runtime/Lib/site-packages/torch/lib/cublasLt64_12.dll` |
| 507.18 | `.venv/Lib/site-packages/torch/lib/cublasLt64_12.dll` |
| 490.12 | `.tmp/phase7-gpu-runtime/Lib/site-packages/torch/lib/cudnn_engines_precompiled64_9.dll` |
| 490.12 | `.venv/Lib/site-packages/torch/lib/cudnn_engines_precompiled64_9.dll` |
| 448.79 | `.tmp/hf-download/models--cross-encoder--mmarco-mMiniLMv2-L12-H384-v1/snapshots/1427fd652930e4ba29e8149678df786c240d8825/model.safetensors` |
| 448.79 | `.tmp/models/1427fd652930e4ba29e8149678df786c240d8825/model.safetensors` |
| 448.79 | `.tmp/phase7-models/1427fd652930e4ba29e8149678df786c240d8825/model.safetensors` |
| 448.79 | `.tmp/phase7-finetune-prototype/model.safetensors` |
| 291.82 | `.tmp/phase7-gpu-runtime/Lib/site-packages/torch/lib/torch_cpu.dll` |
| 291.82 | `.venv/Lib/site-packages/torch/lib/torch_cpu.dll` |
| 274.32 | `.tmp/phase7-gpu-runtime/Lib/site-packages/torch/lib/cusparse64_12.dll` |
| 274.32 | `.venv/Lib/site-packages/torch/lib/cusparse64_12.dll` |
| 269.36 | `.tmp/phase7-gpu-runtime/Lib/site-packages/torch/lib/cudnn_adv64_9.dll` |
| 269.36 | `.venv/Lib/site-packages/torch/lib/cudnn_adv64_9.dll` |
| 264.50 | `.tmp/phase7-gpu-runtime/Lib/site-packages/torch/lib/cufft64_11.dll` |
| 264.50 | `.venv/Lib/site-packages/torch/lib/cufft64_11.dll` |
| 200.50 | `.git/objects/pack/pack-9c73bf04512a18a06d011e1b6b312ca26049796e.pack` |

## Top 20 directories after (nested totals overlap)

| MiB | Path |
|---:|---|
| 7615.57 | `.tmp` |
| 4849.33 | `.venv` |
| 4846.73 | `.venv/Lib/site-packages` |
| 4846.73 | `.venv/Lib` |
| 4069.96 | `.tmp/phase7-gpu-runtime` |
| 4068.97 | `.tmp/phase7-gpu-runtime/Lib/site-packages` |
| 4068.97 | `.tmp/phase7-gpu-runtime/Lib` |
| 4052.62 | `.tmp/phase7-gpu-runtime/Lib/site-packages/torch` |
| 4021.86 | `.venv/Lib/site-packages/torch` |
| 3900.70 | `.tmp/phase7-gpu-runtime/Lib/site-packages/torch/lib` |
| 3900.70 | `.venv/Lib/site-packages/torch/lib` |
| 1444.61 | `.release` |
| 1442.21 | `.release/reranker` |
| 1130.76 | `.release/reranker/studies` |
| 600.09 | `.tmp/phase7-loop-snapshots` |
| 600.03 | `.tmp/phase7-loop-snapshots/Alibaba-NLP--gte-multilingual-reranker-base/8215cf04918ba6f7b6a62bb44238ce2953d8831c` |
| 600.03 | `.tmp/phase7-loop-snapshots/Alibaba-NLP--gte-multilingual-reranker-base` |
| 469.93 | `.tmp/models/1427fd652930e4ba29e8149678df786c240d8825` |
| 469.93 | `.tmp/models` |
| 469.92 | `.tmp/hf-download` |
