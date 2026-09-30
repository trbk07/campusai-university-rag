"""Evaluate reviewed human questions separately from generated regression data."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from campusai.retrieval.calibration import RetrievalPolicy
from campusai.retrieval.hybrid import HybridRetriever
from campusai.retrieval.dense_index import DenseIndex
from evaluation.metrics import recall_at_k, reciprocal_rank
from evaluation.phase6_human_schema import load_human_challenge
from evaluation.retrieval_failure_cases import failure_cases
from evaluation.run_phase6_release import _bootstrap, _run_mode


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=Path("data/benchmark/phase6_human_natural.jsonl"))
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/phase6-index"))
    parser.add_argument("--calibration", type=Path, default=Path("evaluation/results/phase6_retrieval_calibration.json"))
    parser.add_argument("--output", type=Path, default=Path("evaluation/results/phase6_human_natural_report.json"))
    parser.add_argument("--failures", type=Path, default=Path("evaluation/results/phase6_failure_cases_human.json"))
    args = parser.parse_args()
    manifest = json.loads((args.index_dir / "manifest.json").read_text(encoding="utf-8"))
    doc_ids = list(manifest["documents"])
    evidence_ids = set()
    for doc_id in doc_ids:
        dense = DenseIndex.load(args.index_dir / doc_id / "dense.json")
        evidence_ids.update((doc_id, item["chunk_id"]) for item in dense.items)
    rows = load_human_challenge(args.benchmark, evidence_ids)
    regression_queries = {
        " ".join(json.loads(line)["question"].casefold().split())
        for split in ("dev", "test", "holdout")
        for line in Path(f"data/benchmark/phase6_retrieval_{split}.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    if any(" ".join(row["question"].casefold().split()) in regression_queries for row in rows):
        raise SystemExit("human challenge contains a generated regression query")
    policy = RetrievalPolicy.from_report(args.calibration, expected_mode="hybrid_rrf")
    if policy.confidence_model.kind != "logistic":
        raise SystemExit("human challenge requires a fitted confidence model")
    retriever = HybridRetriever(args.index_dir, query_cache_size=0, policies={"hybrid_rrf": policy})
    reports = {}
    outputs = {}
    traces = {}
    for mode in ("bm25", "dense", "hybrid_rrf", "auto"):
        reports[mode], outputs[mode], traces[mode] = _run_mode(rows, retriever, doc_ids, mode)
    primary = reports["auto"]
    primary_outputs = outputs["auto"]
    hard = [row for row in rows if row["answerable"] and row["difficulty"] == "hard"]
    exact = [row for row in rows if row["answerable"] and "exact_code" in row["challenge_tags"]]
    hard_recall = sum(recall_at_k(primary_outputs[row["qid"]], row["gold_evidence"], 5) for row in hard) / len(hard) if hard else None
    exact_recall = sum(recall_at_k(primary_outputs[row["qid"]], row["gold_evidence"], 5) for row in exact) / len(exact) if exact else None
    by_id = {trace["query_id"]: trace for trace in traces["auto"]}
    routes = [row for row in rows if row.get("expected_route")]
    routing_accuracy = sum(by_id[row["qid"]]["route"] == row["expected_route"] for row in routes) / len(routes) if routes else None
    def segment_stats(group):
        positive = [row for row in group if row["answerable"]]
        negative = [row for row in group if not row["answerable"]]
        return {"n": len(group), "answerable_n": len(positive), "negative_n": len(negative),
                "answerable_recall_at_5": (sum(recall_at_k(primary_outputs[row["qid"]], row["gold_evidence"], 5)
                                               for row in positive) / len(positive) if positive else None),
                "answerable_mrr": (sum(reciprocal_rank(primary_outputs[row["qid"]], row["gold_evidence"])
                                       for row in positive) / len(positive) if positive else None),
                "negative_false_positive_rate": (sum(bool(primary_outputs[row["qid"]]) for row in negative)
                                                 / len(negative) if negative else None)}
    segments = {tag: segment_stats([row for row in rows if tag in row.get("challenge_tags", [])])
                for tag in sorted({tag for row in rows for tag in row.get("challenge_tags", [])})}
    language_segments = {language: segment_stats([row for row in rows if row["language"] == language])
                         for language in sorted({row["language"] for row in rows})}
    difficulty_segments = {difficulty: segment_stats([row for row in rows if row["difficulty"] == difficulty])
                           for difficulty in sorted({row["difficulty"] for row in rows})}
    category_segments = {category: segment_stats([row for row in rows if row["category"] == category])
                         for category in sorted({row["category"] for row in rows})}
    positive_rows = [row for row in rows if row["answerable"]]
    paired = {}
    for mode in ("bm25", "dense"):
        primary_hits = [recall_at_k(primary_outputs[row["qid"]], row["gold_evidence"], 5) for row in positive_rows]
        baseline_hits = [recall_at_k(outputs[mode][row["qid"]], row["gold_evidence"], 5) for row in positive_rows]
        paired[f"auto_vs_{mode}"] = _bootstrap(primary_hits, baseline_hits)
    failures = failure_cases(rows, primary_outputs, traces["auto"], policy.threshold,
                             family="human_natural", split="human_natural")
    errors = []
    if primary["quality"]["answerable_recall"]["5"] < .92:
        errors.append("human_recall_at_5")
    if hard_recall is None or hard_recall < .88:
        errors.append("hard_recall_at_5")
    if exact_recall is None or exact_recall < .99:
        errors.append("exact_code_recall_at_5")
    if primary["negative"]["false_positive_rate"] > .05:
        errors.append("negative_fpr")
    if primary["provenance_loss_rate"] or primary["filter_leakage"]:
        errors.append("provenance_or_filter_leakage")
    if any(value["ci95"][0] <= 0 for value in paired.values()):
        errors.append("paired_improvement_not_positive")
    report = {"schema_version": 1, "phase": 6, "benchmark_family": "human_natural",
              "status": "pass" if not errors else "fail", "errors": errors,
              "benchmark_sha256": sha(args.benchmark), "calibration_sha256": sha(args.calibration),
              "index_sha256": sha(args.index_dir / "manifest.json"),
              "environment": {"python": platform.python_version(), "platform": platform.platform()},
              "human_natural": {"modes": reports, "hard_answerable_recall_at_5": hard_recall,
                                "exact_code_recall_at_5": exact_recall, "routing_accuracy": routing_accuracy,
                                "tag_segments": segments, "language_segments": language_segments,
                                "difficulty_segments": difficulty_segments,
                                "category_segments": category_segments, "paired_bootstrap": paired,
                                "failure_count": len(failures)}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.failures.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.failures.write_text(json.dumps(failures, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "errors": errors,
                      "answerable_recall_at_5": primary["quality"]["answerable_recall"]["5"],
                      "negative_fpr": primary["negative"]["false_positive_rate"],
                      "failure_count": len(failures)}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
