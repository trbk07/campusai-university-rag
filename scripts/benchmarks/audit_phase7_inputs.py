"""Inventory Phase 7 artifacts and record proven exposure without relabeling authors."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import subprocess

from evaluation.common.release_artifacts import read_json, sha256, source_identity, write_json, verify_index_files
from evaluation.reranker.reranker_release_gates import default_args, validate
from scripts.benchmarks.prepare_human_candidates import load_rows
from evaluation.benchmarks.connected_groups import normalized_question

ROOT = Path(__file__).resolve().parents[2]


def audit(index_dir: Path, results_dir: Path, benchmark_dir: Path) -> tuple[dict, dict]:
    args = default_args(results_dir)
    args.index_dir, args.benchmark_dir, args.through = index_dir, benchmark_dir, "M0"
    baseline = validate(args)
    paths = set(results_dir.glob("*.json"))
    paths.update(path for path in (ROOT / ".release/reranker/studies").rglob("*.json")
                 if path.name in {"attempt.json", "summary.json", "reranker_route_freeze.json", "reranker_policy_freeze.json"})
    paths.update(index_dir.rglob("manifest.json"))
    paths.update(benchmark_dir.glob("*.jsonl"))
    paths = {path for path in paths if path.name not in {"phase7_evidence_inventory.json", "phase7_exposure_registry.json"}}
    inventory = [{"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size,
                  "classification": "research" if ".release" in path.parts else "index" if path.is_relative_to(index_dir)
                                    else "dataset" if path.is_relative_to(benchmark_dir) else "versioned_report"}
                 for path in sorted(paths)]
    study = ROOT / ".release/reranker/studies/loop3-fixed-policy-natural-dev-v1/student_natural_queries-quality.json"
    known = read_json(study) if study.is_file() else {}
    observations = known.get("observations", [])
    observed_qids = {row["qid"]: row for row in observations}
    natural = benchmark_dir / "student_natural_queries.jsonl"
    verified_study = bool(known and known.get("dataset_sha256") == sha256(natural)
                          and known.get("evaluation_split") == "dev"
                          and len(observed_qids) == len(observations))
    lineage = read_json(benchmark_dir / "human_candidate_lineage.json")
    families = lineage["connected_groups"]
    records = load_rows(benchmark_dir / "human_candidate_pool.jsonl")
    entries = []
    for row in records:
        qid = "human-" + row["candidate_id"]
        observation = observed_qids.get(row.get("source_record_id"), {})
        # Qids may be reused by another dataset. Identity alone is not proof
        # that this question was evaluated; the recorded text must also match.
        proven = bool(verified_study and isinstance(observation.get("question"), str)
                      and normalized_question(row["question"])
                      == normalized_question(observation["question"]))
        entries.append({"qid": qid, "source_record_id": row.get("source_record_id"), "connected_group": families[qid],
                        "status": "known_exposed_dev" if proven else "unknown_pending_history_audit",
                        "purpose": "prior_dev_quality_evaluation" if proven else "exposure_audit_only",
                        "study": study.relative_to(ROOT).as_posix() if proven else None,
                        "study_sha256": sha256(study) if proven else None,
                        "authorship_inferred": False, "heldout_eligible": False})
    # Do not erase a later source-bound audit that proved additional exposure.
    # Retaining known, ineligible records cannot promote anything to held-out.
    existing_path = benchmark_dir / "phase7_exposure_registry.json"
    existing = read_json(existing_path) if existing_path.is_file() else {}
    previous = existing.get("records", [])
    preserved = bool(existing.get("status") == "pass"
                     and existing.get("dataset_sha256") == sha256(benchmark_dir / "human_candidate_pool.jsonl")
                     and existing.get("lineage_sha256") == sha256(benchmark_dir / "human_candidate_lineage.json")
                     and existing.get("index_sha256") == baseline["index_sha256"]
                     and isinstance(previous, list) and len(previous) == len(entries)
                     and all(isinstance(item, dict) and isinstance(item.get("qid"), str)
                             and str(item.get("status", "")).startswith("known_exposed")
                             and item.get("heldout_eligible") is False
                             and item.get("connected_group") == families.get(item["qid"])
                             for item in previous)
                     and {item["qid"] for item in previous} == {item["qid"] for item in entries})
    if preserved:
        entries = previous
    exposed_groups = {row["connected_group"] for row in entries if row["status"].startswith("known_exposed")}
    for entry in entries:
        entry["group_known_exposed"] = entry["connected_group"] in exposed_groups
    registry = {"schema_version": 1, "phase": 7, "status": "pending_complete_history_audit",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "dataset_sha256": sha256(benchmark_dir / "human_candidate_pool.jsonl"),
                "lineage_sha256": sha256(benchmark_dir / "human_candidate_lineage.json"),
                "index_sha256": baseline["index_sha256"],
                "verified_prior_study": verified_study, "records": entries,
                "counts": dict(Counter(entry["status"] for entry in entries)),
                "known_exposed_groups": len(exposed_groups), "heldout_policy": "unknown or exposed groups cannot become new held-out"}
    if preserved:
        registry = existing
    report = {"schema_version": 1, "phase": 7, "task": "P7-01", "status": "pass" if baseline["status"] == "pass" else "blocked",
              "created_at": datetime.now(timezone.utc).isoformat(), **source_identity(ROOT),
              "git_status": subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True).splitlines(),
              "plan_tracked": bool(subprocess.check_output(["git", "ls-files", "--", "plan.md"], cwd=ROOT, text=True).strip()),
              "baseline": {"gate": baseline["gates"]["M0"], "index_sha256": baseline["index_sha256"],
                           "physical_index_valid": verify_index_files(index_dir)},
              "artifacts": inventory, "exposure_registry_status": registry["status"],
              "runtime_target": "local RTX 4060; public acceptance deferred by project owner"}
    return report, registry


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index-dir", type=Path, default=ROOT / ".tmp/hybrid-index")
    parser.add_argument("--results-dir", type=Path, default=ROOT / "evaluation/results")
    parser.add_argument("--benchmark-dir", type=Path, default=ROOT / "data/benchmark")
    args = parser.parse_args(argv)
    report, exposure = audit(args.index_dir.resolve(), args.results_dir.resolve(), args.benchmark_dir.resolve())
    write_json(args.results_dir / "phase7_evidence_inventory.json", report)
    write_json(args.benchmark_dir / "phase7_exposure_registry.json", exposure)
    print({"M0": report["baseline"]["gate"]["status"], "artifacts": len(report["artifacts"]), "exposure": exposure["counts"]})
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
