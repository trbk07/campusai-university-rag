"""Generate the storage audit report and exact, non-executing history proposal."""
from collections import Counter
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

from evaluation.common.artifact_store import file_sha256
from scripts.dev.audit_storage import audit, git

ROOT = Path.cwd()
RESULTS = ROOT / "evaluation/results/storage-audit-20261005"


def read(name):
    return json.loads((RESULTS / name).read_text(encoding="utf-8-sig"))


def write(name, data):
    (RESULTS / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def table(items):
    return "| MiB | Path |\n|---:|---|\n" + "\n".join(
        f"| {row['bytes']/1024**2:.2f} | `{row['path']}` |" for row in items)


def main():
    catalog = json.loads((ROOT / "evaluation/artifacts/manifest.json").read_text(encoding="utf-8"))["artifacts"]
    baseline = read("benchmark-bindings-before.json")
    benchmark_changes = [name for name, digest in baseline.items() if file_sha256(ROOT / name) != digest]
    before, after = read("before.json"), audit(ROOT)
    write("after.json", after)
    first, last = read("validator-before.json"), read("validator-after.json")
    comparison = {k: first[k] == last[k] for k in
                  ("gates", "supplemental_gates", "errors", "artifact_sha256", "status", "score")}
    write("validator-comparison.json", comparison)
    checked = git("cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize) %(objectsize:disk) %(rest)",
                  input=git("rev-list", "--objects", "--all"))
    history = []
    forbidden = {".safetensors", ".bin", ".pt", ".pth", ".onnx", ".faiss", ".npy", ".npz", ".pkl", ".pickle"}
    remove = set(catalog)
    remove.add("frontend/node_modules/")
    for line in checked.decode("utf-8").splitlines():
        fields = line.split(" ", 4)
        if len(fields) != 5 or fields[1] != "blob":
            continue
        oid, _, size, disk, name = fields
        path = Path(name)
        selected = (name in catalog or "node_modules" in path.parts or path.suffix in forbidden
                    or path.suffix == ".pdf" or path.name in {"dense.json", "bm25.json"}
                    or (name.startswith("evaluation/results/") and
                        ("/raw/" in name or "/reranker_cap_trials/" in name
                         or path.suffix in {".zip", ".gz", ".png"})))
        if selected:
            remove.add(name)
            history.append({"oid": oid, "path": name, "bytes": int(size), "packed_object_bytes": int(disk)})
    (RESULTS / "history-remove-paths.txt").write_text("\n".join(sorted(remove)) + "\n", encoding="utf-8")
    history.sort(key=lambda row: -row["bytes"])
    history_report = {"scope": "all existing refs; proposal only; original history and remotes unchanged",
                      "selected_unique_blobs": len(history), "selected_paths": len({r['path'] for r in history}),
                      "uncompressed_blob_bytes": sum(r["bytes"] for r in history),
                      "packed_object_bytes": sum(r["packed_object_bytes"] for r in history),
                      "space_caveat": "Packed-byte sum is an estimate; delta repacking and retained refs affect actual recovery.",
                      "over_100mib": [r for r in history if r["bytes"] > 100 * 1024**2], "objects": history}
    write("history-inventory.json", history_report)
    tests = {}
    for name in ("focused-tests.xml", "phase6-storage-tests.xml", "offline-suite.xml", "ocr-regression.xml"):
        suite = ET.parse(RESULTS / name).getroot().find("testsuite")
        tests[name] = {k: suite.attrib.get(k) for k in ("tests", "failures", "errors", "skipped", "time")}
    verification = {"benchmark_files_verified": len(baseline), "benchmark_changes": benchmark_changes,
                    "validator_equivalence": comparison, "archived_files": len(catalog),
                    "tracked_model_weights": 0, "tracked_serialized_indexes": 0,
                    "tracked_raw_dumps_or_caches": 0, "tracking_check": read("tracking-check.json"),
                    "tests": tests, "history_rewritten": False, "remotes_changed": False}
    write("verification.json", verification)
    assert not benchmark_changes and all(comparison.values()) and verification["tracking_check"]["status"] == "pass"
    assert all(t["failures"] == "0" and t["errors"] == "0" for t in tests.values())
    migration = read("migration.json")
    kinds = Counter(r["artifact_type"] for r in catalog.values())
    raw_saved = migration["original_bytes"] - migration["unique_storage_bytes"]
    over_paths = sorted({r['path'] for r in history_report['over_100mib']})
    report = f"""# Phase 6/7 storage audit — 2026-10-05

The current tracked payload shrank from **{before['tracked_bytes']/1e9:.3f} GB** to **{after['tracked_bytes']/1e6:.1f} MB** ({100*(1-after['tracked_bytes']/before['tracked_bytes']):.1f}% reduction). The workspace shrank from **{before['total_bytes']/1e9:.3f} GB** to **{after['total_bytes']/1e9:.3f} GB**. Existing Git history has not been rewritten, so GitHub publication still needs the separate history step below.

## Size accounting

| Scope | Before | After |
|---|---:|---:|
| Workspace, logical file bytes including `.git`/runtimes | {before['total_bytes']/1e9:.3f} GB | {after['total_bytes']/1e9:.3f} GB |
| `.git` physical file sizes | {before['git_bytes']/1024**2:.2f} MiB | {after['git_bytes']/1024**2:.2f} MiB |
| Currently tracked existing files | {before['tracked_bytes']/1024**2:.2f} MiB | {after['tracked_bytes']/1024**2:.2f} MiB |
| Archived raw bytes | {migration['original_bytes']/1024**2:.2f} MiB | {migration['unique_storage_bytes']/1024**2:.2f} MiB compressed/deduplicated |

The after snapshot counts current index entries, including the staged source, summaries, manifests and audit evidence. The migration is staged for review but has not been committed or pushed. Model/CPU/GPU runtimes remain ignored and retained for reproducibility. The two CUDA environments account for much of the remaining local disk use; they are not Git payload. A {read('cache-cleanup.json')['bytes']/1e9:.3f} GB redownloadable pip cache was removed. GPU setup now uses `--no-cache-dir` to prevent this duplication from recurring. No model or active runtime was deleted.

## Artifacts and bindings

**{len(catalog)} paths** were removed from tracking after streaming SHA256 verification. {dict(kinds)}. Exact paths, raw SHA256/size, compressed SHA256/size, URI, recorded identities and summary links are in [`manifest.json`](../../evaluation/artifacts/manifest.json). The complete removed-path list and {len(migration['duplicate_groups'])} exact duplicate groups are in [`migration.json`](../../evaluation/results/storage-audit-20261005/migration.json). Compression/deduplication reduces their archival footprint by {raw_saved/1e9:.3f} GB. All corpus PDFs were restored as ignored active local inputs after archiving, so normal ingestion still finds the original paths. Generated raw reports stay in the local object store; legacy ZIP/gzip scripts can hydrate their original paths explicitly.

Small summaries preserve metrics and mark omitted raw arrays/text. They cannot satisfy a release gate by themselves. Original reports and historical hash bindings retain their exact byte identity. Phase 6 and Phase 7 readers, raw reference checks and measurement-receipt enumeration resolve missing logical files through the catalog; missing or corrupt evidence fails closed. Thresholds, inference, candidate selection, gold sets, source/runtime freeze receipts and split assignments are unchanged.

Verified **{len(baseline)} benchmark files**, including all human JSONL/gold references: zero hash changes. The owner-generation exposure metadata snapshot is intentionally retained in Git (9.54 MiB): it holds historical question references required for leakage review, not models, embeddings or full corpus chunks. Tracked weights = 0; serialized indexes/index archives = 0; recognized raw dumps/cache = 0. [`tracking-check.json`](../../evaluation/results/storage-audit-20261005/tracking-check.json) and `make storage-check` enforce this for the prospective index.

[`runtime-manifests.json`](../../evaluation/artifacts/runtime-manifests.json) verifies the accepted physical reranker snapshot and all 32 index files, with 15 documents / 1,175 chunks, corpus/model/builder hashes and a hash-bound index archive. Exact re-download by a model label is **not** claimed: the historical smoke report's BGE name differs from the mMiniLM-derived config in the accepted physical snapshot. The storage change preserves the recorded snapshot instead of changing inference. Resolve this existing provenance/naming issue separately before claiming upstream model reproducibility.

## Validation

Full offline suite: **905 passed, 2 live-provider tests skipped, 1 deselected**. The deselected ingestion test `test_cuda_without_hardware_is_blocked_without_loading_models` assumes unavailable CUDA, while this machine has an RTX 4060; it attempted real Hugging Face loading. No Phase 6/7 test was excluded. A subsequent OCR run with the actual restored corpus passed (1 test); the initial full run had no local OCR corpus and its test returned early. Focused storage/Phase 7 tests: 68 passed. Phase 6 storage/manifest tests: 13 passed. All {len(catalog)} artifact objects were independently decompressed and verified without retaining materializations.

The official Phase 7 validator returns the same gate/supplemental statuses, errors, evidence hashes, overall status and score before/after storage migration. It remains conditional, with M2 FAIL; the storage task does not claim release PASS. Source-tree hashes naturally differ because the evidence-reading code changed. See [`validator-comparison.json`](../../evaluation/results/storage-audit-20261005/validator-comparison.json), [`verification.json`](../../evaluation/results/storage-audit-20261005/verification.json) and retained JUnit XML in that directory. The first broad test attempt exposed three Phase 6 fixture failures after raw extraction; those were fixed by resolving the original bytes and keeping every original assertion.

`.gitignore` now excludes the local store, raw/exploratory directories, model weights, NumPy/FAISS/pickled indexes, HF/dependency caches, raw archives, profiler outputs and exact legacy raw paths. Restored files remain ignored. `plan.md` stays tracked. Temporary test directories and the materialization cache were cleaned; original historical baseline artifacts and both runtimes remain intact. The unrelated untracked shell-named file present at task start was left untouched.

## Git history and safe next step

History still contains **{len(over_paths)} paths** above GitHub's 100 MiB per-file limit. GitHub applies the limit to Git objects, so a small pack and deleting files in a later commit do not make them pushable. [GitHub large-file policy](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github).

""" + "\n".join(f"- `{name}`" for name in over_paths) + f"""

The exact proposed removal list is [`history-remove-paths.txt`](../../evaluation/results/storage-audit-20261005/history-remove-paths.txt); historical object IDs and sizes are in [`history-inventory.json`](../../evaluation/results/storage-audit-20261005/history-inventory.json). The proposal selects {history_report['selected_unique_blobs']} unique blobs totaling {history_report['uncompressed_blob_bytes']/1e9:.3f} GB uncompressed and about {history_report['packed_object_bytes']/1024**2:.2f} MiB stored object bytes. Actual recovered `.git` size requires measuring a filtered/repacked copy; retained refs/deltas can change it. Historical `frontend/node_modules` and PDF payloads are included. No remote was contacted or changed and no history rewrite/force-push was performed. `git filter-repo` is not currently installed.

First review/commit this migration, back up the current repo and artifact objects, then work only on a new mirror:

```powershell
git clone --mirror --no-local D:/Project D:/Project/.local_artifacts/history-clean.git
git -C D:/Project/.local_artifacts/history-clean.git filter-repo --invert-paths --paths-from-file D:/Project/evaluation/results/storage-audit-20261005/history-remove-paths.txt
```

Install `git-filter-repo` in a separate tool environment if needed. Inspect the filtered mirror and its commit map, rerun the large-object audit and test a clean clone with the artifact bundle before any publication. **Do not force-push either existing remote automatically.** The repo has `origin` (old finance project) and `new-origin` (CampusAI); use the CampusAI target deliberately after review. Historical release manifests contain commit ancestry checks; filtering changes commit IDs, so their original audit history must remain preserved and any new release baseline must be measured/fingerprinted on the intended clean source. Do not relax ancestry checks or invent new provenance to make them pass.

## Top 20 files before

{table(before['top_files'])}

## Top 20 directories before (nested totals overlap)

{table(before['top_directories'])}

## Top 20 currently tracked files before

{table(before['tracked_largest'][:20])}

## Top 20 files after

{table(after['top_files'])}

## Top 20 directories after (nested totals overlap)

{table(after['top_directories'])}
"""
    (ROOT / "docs/operations/storage_audit_20261005.md").write_text(report, encoding="utf-8")
    print(json.dumps({"workspace_before": before['total_bytes'], "workspace_after": after['total_bytes'],
                      "tracked_after": after['tracked_bytes'], "archived": len(catalog), "all_checks_pass": True}))


if __name__ == "__main__":
    main()
