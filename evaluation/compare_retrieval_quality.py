"""Paired, deterministic held-out retrieval comparison with per-query evidence."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import random
import statistics

from evaluation.release_artifacts import require_previous_gates, sha256, source_identity, write_json


def _relevant(item: dict, gold: list[dict]) -> bool:
    return any(item.get("doc_id") == evidence.get("doc_id")
               and item.get("chunk_id") == evidence.get("chunk_id")
               and (item.get("page") == evidence["page"] if "page" in evidence
                    else item.get("page") in evidence.get("pages", [item.get("page")]))
               for evidence in gold)


def query_metrics(row: dict, results: list[dict]) -> dict:
    gold = row["gold_evidence"]
    relevant = [_relevant(item, gold) for item in results]
    ideal = sum(1 / math.log2(rank + 2) for rank in range(min(5, len(gold))))
    return {**{f"recall{k}": float(any(relevant[:k])) for k in (1, 3, 5, 10)},
            "mrr": next((1 / rank for rank, hit in enumerate(relevant, 1) if hit), 0.0),
            "ndcg5": sum(float(hit) / math.log2(rank + 2) for rank, hit in enumerate(relevant[:5]))
                     / ideal if ideal else 0.0,
            "evidence_precision": sum(relevant[:5]) / min(5, len(results)) if results else 0.0,
            "abstained": not bool(results)}


def paired_bootstrap(deltas: list[float], *, resamples: int = 10000, seed: int = 7) -> dict:
    if not deltas or resamples < 10000 or any(not math.isfinite(value) for value in deltas):
        raise ValueError("paired bootstrap needs finite paired observations and >=10000 resamples")
    rng = random.Random(seed)
    n = len(deltas)
    samples = sorted(sum(deltas[rng.randrange(n)] for _ in range(n)) / n for _ in range(resamples))
    lower, upper = samples[int(.025 * resamples)], samples[min(resamples - 1, int(.975 * resamples))]
    return {"bootstrap_resamples": resamples, "seed": seed, "paired_n": n,
            "mean_delta": statistics.mean(deltas), "ci95": [lower, upper],
            "significant": lower > 0 or upper < 0,
            "win_tie_loss": {"win": sum(value > 1e-12 for value in deltas),
                             "tie": sum(abs(value) <= 1e-12 for value in deltas),
                             "loss": sum(value < -1e-12 for value in deltas)}}


def compare_split(rows: list[dict], baseline: dict[str, list[dict]],
                  reranked: dict[str, list[dict]], evidence: dict[tuple[str, str], dict],
                  doc_ids: list[str], *, seed: int = 7) -> dict:
    qids = [row["qid"] for row in rows]
    if len(qids) != len(set(qids)) or set(qids) != set(baseline) or set(qids) != set(reranked):
        raise ValueError("paired outputs must have exactly the benchmark qids")
    positive = [row for row in rows if row["answerable"]]
    negative = [row for row in rows if not row["answerable"]]
    if not positive or not negative:
        raise ValueError("held-out comparison requires positive and negative records")
    per_query = []
    violations = Counter({"provenance_leakage": 0, "scope_leakage": 0, "invalid_citation": 0,
                          "duplicate_results": 0})
    for row in rows:
        qid = row["qid"]
        before, after = baseline[qid], reranked[qid]
        for outputs in (before, after):
            keys = [(item.get("doc_id"), item.get("chunk_id")) for item in outputs]
            violations["duplicate_results"] += len(keys) - len(set(keys))
            for item in outputs:
                frozen = evidence.get((item.get("doc_id"), item.get("chunk_id")))
                valid = bool(frozen and item.get("page") == frozen.get("page")
                             and item.get("content") == frozen.get("content"))
                violations["provenance_leakage"] += not valid
                violations["invalid_citation"] += not valid or type(item.get("page")) is not int
                scope = row.get("doc_ids", doc_ids)
                violations["scope_leakage"] += item.get("doc_id") not in scope or any(
                    str(item.get("metadata", {}).get(key, "")).casefold() != str(value).casefold()
                    for key, value in (row.get("filters") or {}).items())
        base_metrics, rerank_metrics = query_metrics(row, before), query_metrics(row, after)
        delta = {key: rerank_metrics[key] - base_metrics[key]
                 for key in ("recall1", "recall3", "recall5", "recall10", "mrr", "ndcg5")}
        per_query.append({"qid": qid, "answerable": row["answerable"], "question": row["question"],
                          "baseline": base_metrics, "phase7": rerank_metrics, "delta": delta,
                          "baseline_evidence": before, "phase7_evidence": after})
    aggregate = {}
    for name in ("baseline", "phase7"):
        metrics = {key: statistics.mean(item[name][key] for item in per_query if item["answerable"])
                   for key in ("recall1", "recall3", "recall5", "recall10", "mrr", "ndcg5", "evidence_precision")}
        metrics["negative_fpr"] = sum(bool((baseline if name == "baseline" else reranked)[row["qid"]])
                                       for row in negative) / len(negative)
        abstained = [item for item in per_query if item[name]["abstained"]]
        correct = sum(not item["answerable"] for item in abstained)
        metrics["abstention_precision"] = correct / len(abstained) if abstained else 0.0
        metrics["abstention_recall"] = correct / len(negative)
        aggregate[name] = metrics
    base, current = aggregate["baseline"], aggregate["phase7"]
    stats = {metric: paired_bootstrap([item["delta"][metric] for item in per_query if item["answerable"]],
                                     seed=seed) for metric in ("mrr", "ndcg5", "recall5")}
    relative = lambda metric: (current[metric] - base[metric]) / base[metric] if base[metric] else 0.0
    return {"records": len(rows), "answerable": len(positive), "negative": len(negative), **aggregate,
            "mrr_improvement_relative": relative("mrr"), "ndcg5_improvement_relative": relative("ndcg5"),
            "recall5_drop_absolute": base["recall5"] - current["recall5"],
            "negative_fpr": current["negative_fpr"], **dict(violations),
            "paired_statistics": stats, "per_query": per_query,
            "regression_qids": [item["qid"] for item in per_query if any(value < -1e-12 for value in item["delta"].values())],
            "improvement_qids": [item["qid"] for item in per_query if any(value > 1e-12 for value in item["delta"].values())]}


def quality_errors(report: dict) -> list[str]:
    errors = []
    for split in ("test", "holdout", "human_test", "human_holdout"):
        metrics = report.get(split, {})
        test = split.endswith("test")
        if (metrics.get("records", 0) <= 0 or metrics.get("answerable", 0) <= 0 or metrics.get("negative", 0) <= 0
                or metrics.get("recall5_drop_absolute", 1) > (1e-12 if test else .005 + 1e-12)
                or metrics.get("mrr_improvement_relative", -1) < (.03 - 1e-12 if test else -1e-12)
                or metrics.get("ndcg5_improvement_relative", -1) < (.03 - 1e-12 if test else -1e-12)
                or metrics.get("negative_fpr", 1) > .01
                or any(metrics.get(key, 1) != 0 for key in ("provenance_leakage", "scope_leakage", "invalid_citation", "duplicate_results"))):
            errors.append(f"quality_{split}_gate")
        if test and metrics.get("paired_statistics", {}).get("mrr", {}).get("ci95", [-1])[0] <= 0:
            errors.append(f"statistical_significance_{split}_gate")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/phase6-index"))
    parser.add_argument("--benchmark-dir", type=Path, default=Path("data/benchmark"))
    parser.add_argument("--results-dir", type=Path, default=Path("evaluation/results"))
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    require_previous_gates("M6", args.results_dir, index_dir=args.index_dir, benchmark_dir=args.benchmark_dir)
    from campusai.retrieval.reranker_activation import build_phase7_retriever
    from campusai.retrieval.hybrid import HybridRetriever
    from campusai.retrieval.calibration import RetrievalPolicy
    from evaluation.freeze_human_benchmark import frozen_evidence
    phase6_path = args.results_dir / "phase6_retrieval_calibration.json"
    phase6 = RetrievalPolicy.from_report(phase6_path, expected_mode="hybrid_rrf")
    retriever = build_phase7_retriever(args.index_dir, phase6_path, args.benchmark_dir / "human_retrieval_dev.jsonl")
    if not retriever.phase7_enabled:
        raise ValueError("Phase 7 activation rejected")
    baseline = HybridRetriever(args.index_dir, query_cache_size=0, policies={"hybrid_rrf": phase6})
    retriever.query_cache_size = 0
    docs = json.loads((args.index_dir / "manifest.json").read_text(encoding="utf-8"))["documents"]
    evidence = frozen_evidence(args.index_dir)
    report = {"schema_version": 2, "phase": 7, **source_identity(Path(__file__).resolve().parents[1]),
              "index_sha256": sha256(args.index_dir / "manifest.json"),
              "calibration_sha256": sha256(args.results_dir / "reranker_score_calibration.json"),
              "phase6_calibration_sha256": sha256(phase6_path),
              "model_identity_sha256": retriever.phase7_provider.model_identity.fingerprint,
              "benchmark_sha256": {}}
    try:
        for split, filename in {"test": "phase6_retrieval_test.jsonl", "holdout": "phase6_retrieval_holdout.jsonl",
                                "human_test": "human_retrieval_test.jsonl", "human_holdout": "human_retrieval_holdout.jsonl"}.items():
            path = args.benchmark_dir / filename
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            before, after = {}, {}
            for row in rows:
                kwargs = {"doc_ids": row.get("doc_ids", docs), "filters": row.get("filters"), "top_k": 10}
                before[row["qid"]] = [item.to_dict() for item in baseline.search(row["question"], mode="auto", **kwargs)]
                after[row["qid"]] = [item.to_dict() for item in retriever.search(row["question"], mode="phase7", **kwargs)]
            report[split] = compare_split(rows, before, after, evidence, docs, seed=args.seed)
            report["benchmark_sha256"][split] = sha256(path)
    finally:
        retriever.phase7_provider.close()
    report["errors"] = quality_errors(report)
    report["status"] = "pass" if not report["errors"] else "conditional"
    write_json(args.results_dir / "retrieval_quality_comparison.json", report)
    cases = args.results_dir / "retrieval_ranking_regressions.jsonl"
    cases.write_text("".join(json.dumps({"split": split, **row}, ensure_ascii=False) + "\n"
                              for split in ("test", "holdout", "human_test", "human_holdout")
                              for row in report[split]["per_query"] if row["qid"] in report[split]["regression_qids"]), encoding="utf-8")
    lines = ["# Phase 7 paired quality comparison", "", f"Status: **{report['status']}**", "",
             "| Split | Recall@5 delta | MRR relative delta | nDCG@5 relative delta | MRR 95% CI |", "|---|---:|---:|---:|---|"]
    for split in ("test", "holdout", "human_test", "human_holdout"):
        part = report[split]
        lines.append(f"| {split} | {-part['recall5_drop_absolute']:.6f} | {part['mrr_improvement_relative']:.4%} | "
                     f"{part['ndcg5_improvement_relative']:.4%} | {part['paired_statistics']['mrr']['ci95']} |")
    (args.results_dir / "retrieval_quality_comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "errors": report["errors"]}, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
