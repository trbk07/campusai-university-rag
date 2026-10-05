"""Archive/verify/restore Phase 7 evidence without changing its original bytes."""
from __future__ import annotations

import argparse
import gzip
import json
import os
from pathlib import Path
import shutil
import subprocess

from evaluation.common.artifact_store import (
    ROOT, MANIFEST, entries, file_sha256, resolve_artifact, safe_relative, store_root,
)


def category(name: str, size: int) -> str | None:
    path = Path(name)
    if name.startswith("data/corpus/") and path.suffix == ".pdf":
        return "corpus_source"
    if not name.startswith("evaluation/results/") or "/storage-audit-" in name:
        return None
    if path.name.endswith(".storage-summary.json"):
        return None
    if path.suffix == ".zip":
        return "index_archive" if "index" in path.stem else "reproduction_archive"
    if path.suffix in {".png", ".jpg"}:
        return "source_visual_evidence"
    if ("/raw/" in name or "/reranker_cap_trials/" in name
            or path.suffix == ".gz" or path.stem.endswith("_raw") or "-raw" in path.stem):
        return "raw_evidence"
    if size > 1024**2 and path.suffix in {".json", ".jsonl"}:
        return "full_evaluation_observations"
    if path.name == "candidate_coverage.json" or path.name.endswith("-records.json"):
        return "full_evaluation_observations"
    if path.suffix == ".json" and not any(part in path.stem for part in ("manifest", "ledger", "protocol", "freeze")):
        data = json.loads((ROOT / name).read_text(encoding="utf-8-sig"))
        payload_keys = {"observations", "per_query", "outputs", "samples", "calibration_observations"}
        def raw_payload(value):
            if isinstance(value, dict):
                return any((k in payload_keys and isinstance(v, (dict, list)) and bool(v))
                           or raw_payload(v) for k, v in value.items())
            if isinstance(value, list):
                return any(raw_payload(v) for v in value)
            return False
        if raw_payload(data):
            return "full_evaluation_observations"
    return None


def compact(value, location: str = "", omitted: list | None = None):
    """Keep scalar metrics; explicitly describe omitted raw arrays/text."""
    if omitted is None:
        omitted = []
    if isinstance(value, dict):
        return {k: compact(v, location + "/" + k, omitted) for k, v in value.items()}
    if isinstance(value, list):
        if len(value) > 20 or len(json.dumps(value, ensure_ascii=False)) > 16384:
            omitted.append({"json_pointer": location, "records": len(value)})
            return {"raw_array_reference": location, "records": len(value)}
        return [compact(v, f"{location}/{i}", omitted) for i, v in enumerate(value)]
    if isinstance(value, str) and len(value) > 4096:
        omitted.append({"json_pointer": location, "chars": len(value)})
        return {"raw_text_reference": location, "chars": len(value)}
    return value


def archive(path: Path, kind: str) -> dict:
    name = path.relative_to(ROOT).as_posix()
    digest = file_sha256(path)
    relative = Path("objects") / digest[:2] / (digest + ".gz")
    target = store_root() / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        temporary = target.with_suffix(".tmp")
        try:
            with path.open("rb") as source, temporary.open("wb") as output:
                with gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0, compresslevel=6) as compressed:
                    shutil.copyfileobj(source, compressed)
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    # Verify by streaming decompression before removing a single source byte.
    import hashlib
    actual, count = hashlib.sha256(), 0
    with gzip.open(target, "rb") as source:
        for block in iter(lambda: source.read(1024**2), b""):
            actual.update(block)
            count += len(block)
    if actual.hexdigest() != digest or count != path.stat().st_size:
        raise ValueError("archive verification failed: " + name)
    record = {"artifact_type": kind, "identity": name, "version_or_revision": digest,
              "sha256": digest, "bytes": count, "local_or_external_uri": relative.as_posix(),
              "encoding": "gzip", "storage_sha256": file_sha256(target),
              "storage_bytes": target.stat().st_size,
              # Raw observations cannot be recreated without their historical
              # providers/reviews. Restore exact bytes from the artifact bundle.
              "reproducible": False, "restorable": True}
    if path.suffix == ".json" and kind == "full_evaluation_observations":
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        omitted = []
        summary = {"schema_version": 1, "view_only": True, "gate_eligible": False,
                   "raw_reference": {"path": path.name, "sha256": digest},
                   "summary": compact(data, omitted=omitted), "omitted_raw": omitted}
        sidecar = path.with_name(path.stem + ".storage-summary.json")
        sidecar.write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        record["canonical_summary"] = sidecar.relative_to(ROOT).as_posix()
        # Bind source/config identities only when actually recorded.
        if isinstance(data, dict):
            record["recorded_bindings"] = {k: v for k, v in data.items()
                                           if k.endswith("sha256") and isinstance(v, str)}
    return record


def migrate(apply: bool) -> None:
    names = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode("utf-8").split("\0")
    selected = {n: category(n, (ROOT / n).stat().st_size) for n in names if n and (ROOT / n).is_file()}
    selected = {n: kind for n, kind in selected.items() if kind}
    print(json.dumps({"selected_files": len(selected), "bytes": sum((ROOT / n).stat().st_size for n in selected)}))
    if not apply:
        return
    catalog = entries()
    for i, (name, kind) in enumerate(selected.items(), 1):
        catalog[name] = archive(ROOT / name, kind)
        if i % 25 == 0:
            print(f"verified {i}/{len(selected)}", flush=True)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps({"schema_version": 1, "artifacts": catalog}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ignore = ROOT / ".gitignore"
    content = ignore.read_text(encoding="utf-8")
    additions = ["/" + name for name in catalog if "/" + name not in content.splitlines()]
    if additions:
        with ignore.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write("\n# Exact legacy evidence paths, including restored copies. See evaluation/artifacts/manifest.json.\n")
            stream.write("\n".join(additions) + "\n")
    # The immutable binding catalog is durable before removing files/tracking.
    if selected:
        subprocess.run(["git", "rm", "--cached", "--quiet", "--pathspec-from-file=-", "--pathspec-file-nul"],
                       input=("\0".join(selected) + "\0").encode("utf-8"), cwd=ROOT, check=True)
    for name in selected:
        path = (ROOT / safe_relative(name)).resolve()
        if not path.is_relative_to(ROOT.resolve()):
            raise ValueError("cleanup target escapes repository")
        if file_sha256(path) != catalog[name]["sha256"]:
            raise ValueError("source changed during migration: " + name)
        path.unlink()
    duplicates = {}
    for name, record in catalog.items():
        duplicates.setdefault(record["sha256"], []).append(name)
    report = {"removed_from_tracking": list(catalog), "artifacts": len(catalog),
              "original_bytes": sum(r["bytes"] for r in catalog.values()),
              "unique_storage_bytes": sum(catalog[names[0]]["storage_bytes"] for names in duplicates.values()),
              "duplicate_groups": [names for names in duplicates.values() if len(names) > 1]}
    (ROOT / "evaluation/results/storage-audit-20261005/migration.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("migrate", "verify", "restore"))
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.command == "migrate":
        migrate(args.apply)
        return
    catalog = entries()
    selected = args.paths or list(catalog)
    for name in selected:
        if name not in catalog:
            raise ValueError("unregistered artifact: " + name)
        destination = ROOT / safe_relative(name)
        if args.command == "verify":
            record = catalog[name]
            blob = (store_root() / safe_relative(record["local_or_external_uri"])).resolve()
            if not blob.is_relative_to(store_root()) or file_sha256(blob) != record["storage_sha256"]:
                raise ValueError("stored hash mismatch: " + name)
            import hashlib
            digest, count = hashlib.sha256(), 0
            with gzip.open(blob, "rb") as stream:
                for block in iter(lambda: stream.read(1024**2), b""):
                    digest.update(block)
                    count += len(block)
            if digest.hexdigest() != record["sha256"] or count != record["bytes"]:
                raise ValueError("raw hash/size mismatch: " + name)
            continue
        source = resolve_artifact(destination)
        if file_sha256(source) != catalog[name]["sha256"]:
            raise ValueError("raw hash mismatch: " + name)
        if args.command == "restore" and not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
    print(json.dumps({"command": args.command, "verified_files": len(selected)}))


if __name__ == "__main__":
    main()
