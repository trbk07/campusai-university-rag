"""Bind prior candidate observations to their exact owner-confirmed input bytes."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

from evaluation.benchmarks.freeze_human_benchmark import assign_grouped_splits
from evaluation.benchmarks.owner_review import load_confirmation
from evaluation.common.release_artifacts import read_json, sha256, write_json
from scripts.benchmarks.prepare_human_candidates import load_rows


def record_exposure(benchmark: Path, report_path: Path, archive_dir: Path, index: Path) -> dict:
    _, sources = load_confirmation(benchmark)
    report = read_json(report_path)
    if report.get("index_sha256") != sha256(index / "manifest.json"):
        raise ValueError("prior candidate observations do not bind this index")
    observations = {}
    for split in ("dev", "test", "holdout"):
        rows = [row for row in sources if row["split"] == split]
        original_bytes = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n"
                                 for row in rows).encode("utf-8")
        part = report["splits"]["human_" + split]
        dataset_hash = hashlib.sha256(original_bytes).hexdigest()
        pairs = part["caps"]["40"]["per_query"]
        if (part.get("benchmark_sha256") != dataset_hash or not isinstance(pairs, list)
                or any(not isinstance(pair, dict) or not isinstance(pair.get("qid"), str) for pair in pairs)
                or len(pairs) != len(rows) or len({pair["qid"] for pair in pairs}) != len(pairs)
                or {pair["qid"] for pair in pairs} != {row["qid"] for row in rows}):
            raise ValueError("prior candidate observations changed or reused qids from another dataset: " + split)
        for pair in pairs:
            if not isinstance(pair.get("candidates"), list):
                raise ValueError("missing raw candidate observations")
            observations[pair["qid"]] = {"split": split, "dataset_sha256": dataset_hash,
                                         "candidate_observation_sha256": hashlib.sha256(json.dumps(
                                             pair, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()).hexdigest()}
    registry_path = benchmark / "phase7_exposure_registry.json"
    registry = read_json(registry_path)
    entries = registry["records"]
    lineage = benchmark / "human_candidate_lineage.json"
    source_groups = read_json(lineage)["connected_groups"]
    if (registry.get("dataset_sha256") != sha256(benchmark / "human_candidate_pool.jsonl")
            or registry.get("lineage_sha256") != sha256(lineage)
            or registry.get("index_sha256") != sha256(index / "manifest.json")
            or len(entries) != len(observations) or len({entry["qid"] for entry in entries}) != len(entries)
            or {entry["qid"] for entry in entries} != set(observations)
            or any(entry["connected_group"] != source_groups.get(entry["qid"]) for entry in entries)):
        raise ValueError("prior exposure does not bind the current source registry")
    archive_dir.mkdir(parents=True, exist_ok=True)
    report_hash = sha256(report_path)
    archived = archive_dir / (report_hash + ".json")
    if archived.exists():
        if sha256(archived) != report_hash:
            raise ValueError("prior raw report archive changed")
    else:
        shutil.copyfile(report_path, archived)
        if sha256(archived) != report_hash:
            raise ValueError("prior report changed while archiving")
    for entry in entries:
        observed = observations[entry["qid"]]
        if not str(entry["status"]).startswith("known_exposed"):
            entry.update(status="known_exposed_" + observed["split"], purpose="prior_candidate_coverage_observation",
                         study=archived.as_posix(), study_sha256=report_hash)
        entry["prior_candidate_exposure"] = {**observed, "report_sha256": report_hash,
                                              "raw_archive": archived.as_posix(),
                                              "exposure_time_unknown": True}
        entry.update(heldout_eligible=False, group_known_exposed=True)
    registry.update(status="pass", audit_recorded_at=datetime.now(timezone.utc).isoformat(),
                    audit_scope="proven prior exposure; no unexposed or historical timestamp claim",
                    counts=dict(Counter(entry["status"] for entry in entries)),
                    known_exposed_groups=len({entry["connected_group"] for entry in entries}))
    write_json(registry_path, registry)
    return {"status": "pass", "records": len(entries), "exposure": registry["counts"],
            "heldout_eligible_records": 0, "report_sha256": report_hash}


def quarantine(benchmark: Path) -> dict:
    """Preserve the old allocation and move proven exposed groups to research/dev."""
    dataset = benchmark / "human_retrieval.jsonl"
    registry = read_json(benchmark / "phase7_exposure_registry.json")
    rows = load_rows(dataset)
    histories = {entry["qid"]: entry for entry in registry["records"]}
    assigned = assign_grouped_splits(rows, histories)
    archive = benchmark / "owner_confirmed_inputs" / (sha256(dataset) + ".pre_quarantine.jsonl")
    if not archive.exists():
        with archive.open("xb") as stream:
            stream.write(dataset.read_bytes())
    elif sha256(archive) != sha256(dataset):
        raise ValueError("previous allocation archive changed")
    for path, records in [(dataset, assigned)] + [(benchmark / f"human_retrieval_{split}.jsonl",
                                                   [row for row in assigned if row["split"] == split])
                                                  for split in ("dev", "test", "holdout")]:
        path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records), encoding="utf-8")
    return {"split_counts": dict(Counter(row["split"] for row in assigned)), "benchmark_frozen": False}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-dir", type=Path, default=Path("data/benchmark"))
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/hybrid-index"))
    parser.add_argument("--report", type=Path, default=Path("evaluation/results/candidate_coverage.json"))
    parser.add_argument("--archive-dir", type=Path, default=Path(".release/reranker/archive/prior-candidate-coverage"))
    parser.add_argument("--quarantine-to-dev", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = record_exposure(args.benchmark_dir, args.report, args.archive_dir, args.index_dir)
        if args.quarantine_to_dev:
            result.update(quarantine(args.benchmark_dir))
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        print(json.dumps({"status": "blocked", "error": str(error)}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
