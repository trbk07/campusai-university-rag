# Evidence storage for Phase 6/7/8

Cleanup on 2026-10-13 removed 4.302 GiB across 16,146 files: the redundant
GPU virtual environment, disposable caches, completed Chat upload packets and
verified historical materializations. The active `.venv` retains identical
Torch/functorch/torchgen files and CUDA works. Source/config/runtime identity
and current quality-review bindings are unchanged. Model/index snapshots,
compressed raw evidence, baseline artifacts and `plan.md` remain available.
See [the deletion and verification record](../../evaluation/results/storage-cleanup-20261013.json).
Restore a removed historical input with `manage_artifacts restore <logical-path>`
before using a legacy script that opens that path directly. Completed Chat
upload links refer to restorable historical inputs; they need not stay unpacked.

Git contains source, configs, reviewed benchmark JSONL and gold references,
canonical summaries, regression cases, manifests and hash bindings.
`plan.md` remains the tracked roadmap. Raw observations and physical indexes
are required evidence, but their bytes are stored separately from Git.

```text
evaluation/results/             canonical summaries, historical manifests
evaluation/artifacts/           artifact catalog and model/index manifests
evaluation/raw/                 new raw collectors (ignored)
evaluation/exploratory/         temporary studies (ignored)
.local_artifacts/objects/       compressed artifacts addressed by raw SHA256
.local_artifacts/resolved/      disposable verified materializations
.local_artifacts/models/        future offline model snapshots
.local_artifacts/indexes/       future physical indexes
.local_artifacts/hf_cache/      future download cache
.local_artifacts/experiment_runs/
.local_artifacts/load_tests/
.local_artifacts/profiler/
```

Historical `.tmp` index/model paths and `.release` study paths remain valid.
They are ignored and retained because frozen receipts bind them. Moving or
renaming an active index requires a separate provenance update. Retrieval,
model inference, ranking, benchmark splits and release thresholds are unchanged.

`evaluation/artifacts/manifest.json` maps the original logical path to exact
raw SHA256, raw size, compressed SHA256/size and an artifact-store-relative URI.
Identical raw files share one object; gzip preserves the original CRLF and JSON
bytes. No frozen report or hash is rewritten. Small `.storage-summary.json`
files preserve scalar metrics and describe omitted arrays with JSON pointers
and record counts. They are explicitly `view_only` and `gate_eligible: false`.

Phase 7 shared JSON/hash IO, supplemental raw references, receipt enumeration,
and the Phase 6 release validator resolve absent logical paths from this catalog.
They verify the compressed object and decompressed bytes before reading them.
Missing/corrupt blobs, mismatched report hashes, corrupt materializations and
path traversal fail closed. A summary cannot supply missing observations.
Existing explicit local files continue to be checked against the consuming
report's hash bindings, as before.

For a fresh clone, obtain a copy of `.local_artifacts/objects/` through your
chosen storage/backup channel. This task has not uploaded the bundle anywhere.
Set `CAMPUSAI_ARTIFACT_ROOT` to a downloaded artifact directory to use a store
outside the checkout. The root must contain `objects/`. Copying Git alone is
insufficient to recompute historical raw observations; validators reject their
absence. Live LLM/staging observations are restorable from recorded bytes, not
claimed to be deterministically reproducible by running a provider again.

The 2026-10-12 publication also catalogs Phase 7 intermediate runs and Phase 8
full preflights, predictions, Chat prompt packets and runtime execution records.
Their original files remain local and Git-ignored. Current compact metrics,
review decisions, benchmark versions used by regression tests and source remain
in Git. Restore referenced files before running historical evidence-dependent
tests or collectors; `restore` copies exact bytes without contacting Gemini.
Neither a missing blob nor a compact summary counts as a passing gate. The
Phase 8 live cohort remains incomplete after three successes and HTTP 503.

```powershell
# Verify every raw object without materializing gigabytes into the checkout.
.venv/Scripts/python.exe -m scripts.dev.manage_artifacts verify

# Hydrate an original path for scripts that open ZIP/PDF/gzip files directly.
.venv/Scripts/python.exe -m scripts.dev.manage_artifacts restore evaluation/results/phase7-completion-20261004/p7-03_successor_source_index.zip

# Restore all historical paths only when a legacy reproduction requires them.
.venv/Scripts/python.exe -m scripts.dev.manage_artifacts restore

# Audit workspace/history and check the prospective Git index before committing.
.venv/Scripts/python.exe -m scripts.dev.audit_storage --output .tmp/storage-audit.json
.venv/Scripts/python.exe -m scripts.dev.check_git_artifacts
```

Restored files remain ignored. PDFs needed for normal ingestion have been
materialized locally at their original corpus paths; their Git tracking is
removed. The artifact catalog retains their exact bindings and deduplicates
the archived copies. `resolved/` is a disposable cache, never the backup copy.

For new phases, collect raw output under ignored raw/study directories, commit
a small summary plus a raw hash/reference, and retain the underlying artifact
bundle. The migration tool defaults to a dry run; `migrate --apply` archives and
verifies tracked legacy payloads, persists the catalog, then removes tracking
and original generated payloads. It does not rewrite Git history. Run
`make storage-check` after staging, and `make storage-verify` before release.
The index check rejects weights, raw dumps, serialized indexes and files over
5 MiB. An exposure-history metadata snapshot in the benchmark is allowed up to
10 MiB; it contains historical question references needed for leakage review.

Physical runtime identities are recorded in `runtime-manifests.json`. One
pre-existing naming issue was found: the frozen smoke report calls the local
reranker BGE, while its config identifies an mMiniLM-derived architecture.
The exact accepted snapshot hash is retained; replacing it by downloading the
report's model label would change behavior. Resolve that naming/provenance
issue separately before making a fresh upstream model reproducibility claim.

The complete size audit, removed-path list, history inventory, test results and
safe history-cleanup proposal are in
[`storage_audit_20261005.md`](storage_audit_20261005.md).
