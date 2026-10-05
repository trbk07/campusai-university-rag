"""Summarize active-cycle and newly proposed P7-03 split/stratum coverage."""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "evaluation/results/phase7-completion-20261004"
OUT = TASK / "p7-03_gap_report.json"
MANIFEST = TASK / "p7-03_artifact_manifest-v2.json"
LEDGER = TASK / "completion_task_ledger.json"
CONFIG = ROOT / "configs/phase7_release_cycle.json"
SPLIT = TASK / "p7-03_f0_split_proposal.json"
DECISIONS = TASK / "p7-03_semantic_exposure_decisions.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if OUT.exists() or MANIFEST.exists():
        raise FileExistsError("gap report already exists; use a new evidence revision")
    active = json.loads(CONFIG.read_text(encoding="utf-8"))
    bench = ROOT / active["benchmark_dir"]
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
    summaries = {}
    group_sets = {}
    split_rows = {}
    for name in ("dev", "test", "holdout"):
        path = bench / f"human_retrieval_{name}.jsonl"
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        split_rows[name] = rows
        tag_counts = Counter(tag for row in rows for tag in row.get("tags", []) if isinstance(tag, str))
        groups = {str(row[field]) for row in rows for field in ("source_group", "paraphrase_group")
                  if row.get(field) not in (None, "")}
        group_sets[name] = groups
        summaries[name] = {
            "path": path.relative_to(ROOT).as_posix(), "sha256": sha(path), "reviewed_rows": len(rows),
            "answerable": sum(row.get("answerable") is True for row in rows),
            "unanswerable": sum(row.get("answerable") is False for row in rows),
            "easy": sum(row.get("difficulty") == "easy" for row in rows),
            "medium": sum(row.get("difficulty") == "medium" for row in rows),
            "hard": sum(row.get("difficulty") == "hard" for row in rows),
            "tag_counts": dict(sorted(tag_counts.items())),
            "unique_source_or_paraphrase_groups": len(groups),
            "candidate_new_group_records": 0,
        }
    cross_split_leaks = {}
    for left, right in (("dev", "test"), ("dev", "holdout"), ("test", "holdout")):
        cross_split_leaks[f"{left}:{right}"] = sorted(group_sets[left] & group_sets[right])
    missing_minima = {
        "dev_records": max(0, 120 - summaries["dev"]["reviewed_rows"]),
        "test_records": max(0, 130 - summaries["test"]["reviewed_rows"]),
        "holdout_records": max(0, 150 - summaries["holdout"]["reviewed_rows"]),
        "dev_answerable_positive_floor_30": max(0, 30 - summaries["dev"]["answerable"]),
        "test_answerable_positive_floor_32": max(0, 32 - summaries["test"]["answerable"]),
        "holdout_answerable_positive_floor_37": max(0, 37 - summaries["holdout"]["answerable"]),
        "dev_unanswerable_floor_30": max(0, 30 - summaries["dev"]["unanswerable"]),
        "test_unanswerable_floor_32": max(0, 32 - summaries["test"]["unanswerable"]),
        "holdout_unanswerable_floor_37": max(0, 37 - summaries["holdout"]["unanswerable"]),
    }
    proposed_counts = split["eligible_connected_group_counts"]
    report = {
        "schema_version": 1, "task": "P7-03.3", "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "GAP_COUNTS_RECORDED_F0_STRATA_REMAINS_BLOCKED", "release_eligible": False,
        "active_cycle": {key: active[key] for key in ("benchmark_dir", "results_dir", "index_dir")},
        "current_reviewed_question_records": summaries,
        "current_split_group_intersections": {key: len(value) for key, value in cross_split_leaks.items()},
        "current_split_cross_group_leak_count": sum(len(value) for value in cross_split_leaks.values()),
        "current_question_record_minimum_gaps": missing_minima,
        "candidate_new_source_group_plan": {
            "source_rows": decisions["candidate_rows"], "connected_groups": decisions["connected_groups"],
            "eligible_groups_by_proposed_split": proposed_counts,
            "eligible_test_group_floor_10_met": proposed_counts["test"] >= 10,
            "eligible_holdout_group_floor_10_met": proposed_counts["holdout"] >= 10,
            "new_question_records_by_split": {"dev": 0, "test": 0, "holdout": 0},
        },
        "unresolved_strata": {
            "ambiguous_test": summaries["test"]["tag_counts"].get("ambiguous", 0),
            "ambiguous_holdout": summaries["holdout"]["tag_counts"].get("ambiguous", 0),
            "contextual_test": summaries["test"]["tag_counts"].get("contextual", 0),
            "contextual_holdout": summaries["holdout"]["tag_counts"].get("contextual", 0),
            "scoped_year_semester_test_holdout": "not evidenced in active split tags; inspect source-backed item availability before release freeze",
            "new_source_group_strata": "not generated; no records from the 42 reviewed source groups are allocated in this active dataset",
        },
        "criteria": {"minimum_rows": {"dev": 120, "test": 130, "holdout": 150},
                     "positive_ratio": 0.25, "primary_holdout_connected_groups_minimum": 10},
        "inputs": [{"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path)}
                   for path in [CONFIG, SPLIT, DECISIONS]],
        "limitations": [
            "The active r18 M1 dataset already has reviewed records and group-level split assignments; these are reported separately from the new P7-03 source groups.",
            "Current M1 row/answerability minima do not establish new-group semantic freshness or every M2/M4/S3/S4 stratum.",
            "No held-out per-qid outcome/answer fields were read by this report builder; it reads only question metadata and tags.",
        ],
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    prior_manifest = TASK / "p7-03_artifact_manifest.json"
    prior = json.loads(prior_manifest.read_text(encoding="utf-8"))
    all_artifacts = prior["artifacts"] + [{"path": OUT.relative_to(ROOT).as_posix(), "sha256": sha(OUT), "bytes": OUT.stat().st_size}]
    manifest = {"schema_version": 1, "task": "P7-03", "status": "P7-03_REVIEW_AND_GAP_ARTIFACTS_HASHED; F0_NOT_FROZEN",
                "created_at": datetime.now(timezone.utc).isoformat(), "release_eligible": False,
                "supersedes_manifest": {"path": prior_manifest.relative_to(ROOT).as_posix(), "sha256": sha(prior_manifest)},
                "artifacts": all_artifacts,
                "inputs": prior["inputs"] + [{"path": OUT.relative_to(ROOT).as_posix(), "sha256": sha(OUT)}]}
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "question_counts": {k: v["reviewed_rows"] for k, v in summaries.items()},
                      "candidate_groups": proposed_counts, "manifest": MANIFEST.relative_to(ROOT).as_posix()}, indent=2))
    return int(report["current_split_cross_group_leak_count"] > 0 or any(missing_minima.values()))


if __name__ == "__main__":
    raise SystemExit(main())
