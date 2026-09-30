"""Recompute Phase 3 retrieval evidence without consuming Phase 6 reports.

The existing Phase 6 benchmark may be supplied as a diagnostic input, but a
Phase 3 release requires independently reviewed Phase 3 split files.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import platform
from pathlib import Path
import statistics
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from campusai.retrieval.hybrid import HybridRetriever
from campusai.retrieval.calibration import RetrievalPolicy
from evaluation.metrics import recall_at_k, reciprocal_rank


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_splits(directory: Path, *, require_review: bool = True) -> tuple[dict[str, list[dict]], list[str]]:
    errors: list[str] = []
    rows_by_split: dict[str, list[dict]] = {}
    seen_ids: set[str] = set()
    seen_queries: set[str] = set()
    groups: dict[tuple[str, str], set[str]] = defaultdict(set)
    for split in ("dev", "test", "holdout"):
        path = directory / f"phase3_retrieval_{split}.jsonl"
        if not path.is_file():
            errors.append(f"missing_{split}_benchmark")
            rows_by_split[split] = []
            continue
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        rows_by_split[split] = rows
        for row in rows:
            qid = row.get("qid")
            query = " ".join(str(row.get("question", "")).casefold().split())
            if not qid or qid in seen_ids:
                errors.append("duplicate_or_missing_id")
            if not query or query in seen_queries:
                errors.append("duplicate_or_missing_query")
            seen_ids.add(qid)
            seen_queries.add(query)
            if row.get("split") != split:
                errors.append("split_mismatch")
            evidence = row.get("gold_evidence")
            if not isinstance(row.get("answerable"), bool) or not isinstance(evidence, list):
                errors.append("invalid_answerability_or_evidence")
                continue
            if bool(evidence) != row["answerable"]:
                errors.append("answerability_evidence_mismatch")
            if row["answerable"] and any(not isinstance(item, dict) or not item.get("chunk_id") or not item.get("doc_id") for item in evidence):
                errors.append("invalid_gold_evidence")
            if not row["answerable"] and not row.get("negative_class"):
                errors.append("missing_negative_class")
            if require_review and (row.get("annotation_status") != "independently_reviewed" or not row.get("source_annotation")):
                errors.append("independent_annotation_review_missing")
            for field in ("source_group", "template_group"):
                if row.get(field):
                    groups[(field, str(row[field]))].add(split)
    all_rows = [row for rows in rows_by_split.values() for row in rows]
    if len(all_rows) < 400:
        errors.append("benchmark_below_400")
    if sum(not row.get("answerable", True) for row in all_rows) < 40:
        errors.append("negative_below_40")
    if any(len(splits) > 1 for splits in groups.values()):
        errors.append("source_or_template_leakage")
    if any(not rows_by_split[split] for split in ("dev", "test", "holdout")):
        errors.append("empty_split")
    return rows_by_split, sorted(set(errors))


def index_metadata(index_dir: Path) -> tuple[list[str], dict, set[tuple[str, str]]]:
    manifest_path = index_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    doc_ids = list(manifest["documents"])
    evidence_ids: set[tuple[str, str]] = set()
    for doc_id in doc_ids:
        dense_path = index_dir / doc_id / "dense.json"
        bm25_path = index_dir / doc_id / "bm25.json"
        if not dense_path.is_file() or not bm25_path.is_file():
            raise ValueError(f"incomplete index for {doc_id}")
        dense = json.loads(dense_path.read_text(encoding="utf-8"))
        evidence_ids.update((doc_id, item["chunk_id"]) for item in dense["items"])
    return doc_ids, manifest, evidence_ids


def evaluate(rows: list[dict], retriever: HybridRetriever, doc_ids: list[str], mode: str) -> tuple[dict, dict[str, tuple[float, float]]]:
    latency: list[float] = []
    reasons: Counter[str] = Counter()
    per_query: dict[str, tuple[float, float]] = {}
    negative_count = false_positives = 0
    positives = 0
    for row in rows:
        started = time.perf_counter()
        results = retriever.search(row["question"], doc_ids, filters=row.get("filters"), top_k=5, mode=mode)
        latency.append((time.perf_counter() - started) * 1000)
        trace = retriever.last_trace
        if not results:
            reasons[trace.abstention_reason or "missing_reason"] += 1
        if row["answerable"]:
            positives += 1
            per_query[row["qid"]] = (recall_at_k(results, row["gold_evidence"], 5), reciprocal_rank(results, row["gold_evidence"]))
        else:
            negative_count += 1
            false_positives += bool(results)
    recall = statistics.mean(value[0] for value in per_query.values()) if positives else 0.0
    mrr = statistics.mean(value[1] for value in per_query.values()) if positives else 0.0
    warm = sorted(latency[1:] or latency)
    percentile = lambda p: round(warm[min(len(warm) - 1, int((len(warm) - 1) * p))], 3) if warm else None
    breakdown = {}
    for field in ("category", "language", "difficulty", "query_type"):
        groups = defaultdict(list)
        for row in rows:
            if row["answerable"]:
                groups[str(row.get(field, "unknown"))].append(per_query[row["qid"]])
        breakdown[field] = {name: {"n": len(values),
                                   "recall_at_5": round(statistics.mean(value[0] for value in values), 6),
                                   "mrr": round(statistics.mean(value[1] for value in values), 6)}
                            for name, values in groups.items()}
    return ({"records": len(rows), "answerable": positives, "negative": negative_count,
             "answerable_recall_at_5": round(recall, 6), "answerable_mrr": round(mrr, 6),
             "negative_fpr": round(false_positives / negative_count, 6) if negative_count else None,
             "abstention_reasons": dict(reasons),
             "breakdown": breakdown,
             "latency_ms": {"cold": round(latency[0], 3) if latency else None,
                            "p50": percentile(.50), "p95": percentile(.95), "p99": percentile(.99)}}, per_query)


def evidence_errors(name: str, value: dict, index_hash: str) -> list[str]:
    errors = []
    if value.get("status") != "pass" or value.get("index_sha256") != index_hash:
        errors.append(f"invalid_{name}")
    if name == "phase3_performance.json":
        for key, maximum in (("warm_p50_ms", 150), ("warm_p95_ms", 500),
                             ("warm_p99_ms", 1000), ("restart_load_ms", 2000)):
            if not isinstance(value.get(key), (int, float)) or value[key] > maximum:
                errors.append(f"performance_{key}")
        if value.get("error_count") != 0 or value.get("timeout_count") != 0:
            errors.append("performance_errors")
    elif name == "phase3_persistence.json":
        if value.get("restart_pass") is not True or value.get("corruption_fail_closed") is not True:
            errors.append("persistence_failure")
        score_diff = value.get("score_max_abs_diff")
        if value.get("same_result_ids") is not True or not isinstance(score_diff, (int, float)) or score_diff > 1e-6:
            errors.append("persistence_result_mismatch")
    elif name == "phase3_statistical_report.json":
        if value.get("paired_query_count", 0) < 100 or not value.get("recall_delta_ci_95"):
            errors.append("statistical_evidence_missing")
        if value.get("repeatability_pass") is not True:
            errors.append("statistical_repeatability_failure")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-dir", type=Path, default=Path("data/benchmark"))
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/phase3-clean/phase3-index"))
    parser.add_argument("--calibration", type=Path, default=Path("evaluation/results/phase3_calibration.json"))
    parser.add_argument("--output", type=Path, default=Path("evaluation/results/phase3_retrieval_release.json"))
    parser.add_argument("--allow-draft", action="store_true", help="Diagnostic only; the release remains conditional")
    args = parser.parse_args()
    rows, errors = load_splits(args.benchmark_dir, require_review=not args.allow_draft)
    if args.allow_draft:
        errors.append("draft_unreviewed")
    if errors and not args.allow_draft:
        print(json.dumps({"status": "conditional", "errors": errors}))
        return 1
    doc_ids, manifest, evidence_ids = index_metadata(args.index_dir)
    all_rows = [row for split_rows in rows.values() for row in split_rows]
    if len(doc_ids) < 8:
        errors.append("indexed_documents_below_8")
    if len(evidence_ids) < 100:
        errors.append("indexed_chunks_below_100")
    if any((item["doc_id"], item["chunk_id"]) not in evidence_ids for row in all_rows for item in row["gold_evidence"]):
        errors.append("gold_evidence_missing_from_index")
    referenced_docs = {item["doc_id"] for row in all_rows for item in row["gold_evidence"]}
    if len(referenced_docs) < 8:
        errors.append("gold_evidence_documents_below_8")
    for split in ("test", "holdout"):
        if sum(not row["answerable"] for row in rows[split]) < 10:
            errors.append(f"{split}_negative_below_10")
    calibration = json.loads(args.calibration.read_text(encoding="utf-8"))
    policy = None
    if isinstance(calibration.get("result"), dict) and isinstance(calibration["result"].get("threshold"), (int, float)):
        policy = RetrievalPolicy.from_report(args.calibration, expected_mode="hybrid_rrf")
    else:
        errors.append("calibration_no_feasible_threshold")
    index_hash = sha(args.index_dir / "manifest.json")
    corpus_path = args.benchmark_dir / "phase3_corpus_manifest.json"
    corpus = json.loads(corpus_path.read_text(encoding="utf-8")) if corpus_path.is_file() else {}
    if corpus.get("index_manifest_sha256") != index_hash or corpus.get("documents") != len(doc_ids) or corpus.get("chunks") != len(evidence_ids):
        errors.append("corpus_manifest_mismatch")
    dev_hash = sha(args.benchmark_dir / "phase3_retrieval_dev.jsonl")
    if calibration.get("index_sha256") != index_hash or calibration.get("benchmark_sha256") != dev_hash:
        errors.append("calibration_provenance_mismatch")
    if calibration.get("calibration_split") not in ("dev", "calibration") or calibration.get("holdout_used") is not False:
        errors.append("calibration_split_not_locked")
    if calibration.get("status") != "pass" or calibration.get("annotation_status") != "independently_reviewed":
        errors.append("calibration_not_release_eligible")
    retriever = HybridRetriever(args.index_dir, query_cache_size=0,
                                policies={"hybrid_rrf": policy} if policy else {})
    measured: dict[str, dict] = {}
    for split in ("test", "holdout"):
        for mode in ("dense", "hybrid_rrf", "auto"):
            measured[f"{split}:{mode}"], _ = evaluate(rows[split], retriever, doc_ids, mode)
    test = measured["test:auto"]
    holdout = measured["holdout:auto"]
    for name, result, minimum in (("test", test, .93), ("holdout", holdout, .90)):
        if result["answerable_recall_at_5"] < minimum:
            errors.append(f"{name}_recall_below_target")
        if result["answerable_mrr"] < .75:
            errors.append(f"{name}_mrr_below_target")
        if result["negative_fpr"] is None or result["negative_fpr"] > .01:
            errors.append(f"{name}_negative_fpr_above_target")
        if result["latency_ms"]["p95"] > 500:
            errors.append(f"{name}_p95_above_target")
        if result["latency_ms"]["p50"] > 150:
            errors.append(f"{name}_p50_above_target")
        if result["latency_ms"]["p99"] > 1000:
            errors.append(f"{name}_p99_above_target")
    if measured["test:dense"]["answerable_recall_at_5"] < .85:
        errors.append("dense_recall_below_target")
    for split, minimum in (("test", .93), ("holdout", .90)):
        hybrid = measured[f"{split}:hybrid_rrf"]
        if hybrid["answerable_recall_at_5"] < minimum:
            errors.append(f"{split}_hybrid_recall_below_target")
        if hybrid["answerable_mrr"] < .75:
            errors.append(f"{split}_hybrid_mrr_below_target")
        if hybrid["negative_fpr"] is None or hybrid["negative_fpr"] > .01:
            errors.append(f"{split}_hybrid_negative_fpr_above_target")
    # Release status needs independently generated reliability and statistical
    # evidence. Retrieval quality alone cannot award a Phase 3 score.
    evidence = {}
    for name in ("phase3_performance.json", "phase3_persistence.json", "phase3_statistical_report.json"):
        path = args.output.parent / name
        if not path.is_file():
            errors.append(f"missing_{name}")
            continue
        value = json.loads(path.read_text(encoding="utf-8"))
        evidence[name] = {"sha256": sha(path), "status": value.get("status")}
        errors.extend(evidence_errors(name, value, index_hash))
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip())
    if dirty:
        errors.append("working_tree_dirty")
    report = {"schema_version": 2, "phase": 3, "status": "pass" if not errors else "conditional",
              "score": None, "target_score": 9.5, "errors": sorted(set(errors)),
              "benchmark_count": len(all_rows), "split_counts": {key: len(value) for key, value in rows.items()},
              "corpus": {"indexed_documents": len(doc_ids), "indexed_chunks": len(evidence_ids),
                         "index_sha256": index_hash, "corpus_sha256": sha(corpus_path) if corpus_path.is_file() else None,
                         "corpus_hash": corpus.get("corpus_hash"), "model": manifest.get("model_name"),
                         "model_revision": manifest.get("model_revision")},
              "benchmark_sha256": {split: sha(args.benchmark_dir / f"phase3_retrieval_{split}.jsonl") for split in rows},
              "calibration_sha256": sha(args.calibration), "threshold_provenance": calibration,
              "metrics": measured, "supporting_evidence": evidence,
              "environment": {"python": platform.python_version(), "platform": platform.platform()},
              "commit": commit, "working_tree_clean": not dirty}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "errors": report["errors"], "test": test, "holdout": holdout}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
