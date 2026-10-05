"""Record an explicit owner confirmation of existing data and export its audit.

This changes review/authorship metadata only. It does not approve exposure,
assign new splits, freeze a benchmark or produce a release verdict.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import uuid

from evaluation.benchmarks.owner_review import confirm_existing, confirmed_row, confirmation_audit, load_confirmation
from evaluation.common.release_artifacts import sha256


def record(dataset: Path, benchmark_dir: Path, owner_statement: str) -> dict:
    if dataset.parent.resolve() != benchmark_dir.resolve():
        raise ValueError("dataset must be in the bound benchmark directory")
    audit_path = dataset.with_name(dataset.stem + "_review_audit.jsonl")
    if audit_path.exists():
        raise ValueError("review audit exists; use a new cycle")
    initial = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    for split in ("dev", "test", "holdout"):
        path = dataset.parent / f"human_retrieval_{split}.jsonl"
        if path.exists():
            previous = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            if previous != [row for row in initial if row["split"] == split]:
                raise ValueError("existing split does not match the owner-confirmed source")
    confirmation = confirm_existing(dataset, benchmark_dir, owner_statement=owner_statement)
    confirmation, sources = load_confirmation(benchmark_dir)
    rows = [confirmed_row(row, confirmation) for row in sources]
    audit = confirmation_audit(confirmation, sources)
    audit_bytes = "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in audit).encode("utf-8")
    if sha256(dataset) != confirmation["source_snapshot"]["sha256"]:
        raise ValueError("dataset changed while recording owner confirmation")
    destinations = {dataset: rows}
    for split in ("dev", "test", "holdout"):
        path = dataset.parent / f"human_retrieval_{split}.jsonl"
        if path.exists():
            previous = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            if previous != [row for row in sources if row["split"] == split]:
                raise ValueError("existing split does not match the owner-confirmed source")
            destinations[path] = [row for row in rows if row["split"] == split]
    with audit_path.open("xb") as stream:
        stream.write(audit_bytes)
    for path, records in destinations.items():
        payload = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records).encode("utf-8")
        temporary = path.with_name(path.name + ".owner-" + uuid.uuid4().hex)
        try:
            temporary.write_bytes(payload)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    return {"status": "owner_confirmation_recorded", "records": len(rows), "review_mode": "owner_self_review",
            "confirmation_sha256": sha256(benchmark_dir / "phase7_owner_confirmation.json"),
            "dataset_sha256": sha256(dataset), "review_audit_sha256": sha256(audit_path),
            "exposure_history_confirmed": False, "benchmark_frozen": False}


def refresh_export(dataset: Path, benchmark_dir: Path) -> dict:
    """Apply only declared schema normalization to an already confirmed export."""
    confirmation, sources = load_confirmation(benchmark_dir)
    expected = [confirmed_row(row, confirmation) for row in sources]
    current = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(current) != len(expected):
        raise ValueError("owner-confirmed export coverage changed")
    for actual, wanted, source in zip(current, expected, sources):
        legacy = {**wanted, "expected_behavior": source["expected_behavior"]}
        legacy.pop("review_schema_normalization", None)
        if actual != wanted and actual != legacy:
            raise ValueError("owner-confirmed export changed outside declared schema normalization")
    destinations = {dataset: expected, dataset.with_name(dataset.stem + "_review_audit.jsonl"):
                    confirmation_audit(confirmation, sources)}
    for split in ("dev", "test", "holdout"):
        path = dataset.parent / f"human_retrieval_{split}.jsonl"
        if path.exists():
            existing = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            if existing != [row for row in current if row["split"] == split]:
                raise ValueError("owner-confirmed split changed")
            destinations[path] = [row for row in expected if row["split"] == split]
    for path, records in destinations.items():
        payload = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records).encode("utf-8")
        if path.read_bytes() != payload:
            temporary = path.with_name(path.name + ".owner-" + uuid.uuid4().hex)
            try:
                temporary.write_bytes(payload)
                os.replace(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)
    return {"status": "owner_confirmed_export_refreshed", "records": len(expected), "benchmark_frozen": False}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path("data/benchmark/human_retrieval.jsonl"))
    parser.add_argument("--benchmark-dir", type=Path, default=Path("data/benchmark"))
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--owner-statement", help="actual owner confirmation supplied in this session")
    action.add_argument("--refresh-export", action="store_true", help="apply declared schema normalization to an existing confirmed export")
    args = parser.parse_args(argv)
    try:
        result = refresh_export(args.dataset, args.benchmark_dir) if args.refresh_export else record(
            args.dataset, args.benchmark_dir, args.owner_statement)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        print(json.dumps({"status": "blocked", "error": str(error)}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
