"""Measure gold coverage in Phase 6 candidates before reranker evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from campusai.retrieval.contracts import validate_result
from campusai.retrieval.hybrid import HybridRetriever
from evaluation.phase6_schema import load_jsonl
from campusai.retrieval.calibration import RetrievalPolicy
from evaluation.release_artifacts import require_previous_gates, sha256, source_identity


def evaluate_split(rows: list[dict], retriever: HybridRetriever,
                   doc_ids: list[str], cap: int) -> dict:
    answerable = [row for row in rows if row["answerable"]]
    hits = 0
    failures = []
    provenance_errors = 0
    scope_errors = 0
    duplicates = 0
    for row in rows:
        scope = row.get("doc_ids", doc_ids)
        results = retriever.search(row["question"], doc_ids=scope,
                                   filters=row.get("filters"), top_k=cap, mode="auto")
        if len({(item.doc_id, item.chunk_id) for item in results}) != len(results):
            duplicates += 1
        for item in results:
            valid, _ = validate_result(item)
            provenance_errors += not valid or not item.metadata.get("page_range")
            scope_errors += item.doc_id not in scope or any(
                str(item.metadata.get(key, "")).casefold() != str(value).casefold()
                for key, value in (row.get("filters") or {}).items())
        if row["answerable"]:
            gold = {(item["doc_id"], item["chunk_id"]) for item in row["gold_evidence"]}
            found = any((item.doc_id, item.chunk_id) in gold for item in results)
            hits += found
            if not found:
                failures.append({"qid": row["qid"], "query": row["question"],
                                 "expected_evidence": sorted(list(gold)),
                                 "candidate_ids": [(item.doc_id, item.chunk_id) for item in results]})
    return {"records": len(rows), "answerable": len(answerable), "candidate_cap": cap,
            "candidate_recall": hits / len(answerable) if answerable else 0.0,
            "candidate_misses": failures, "provenance_errors": provenance_errors,
            "scope_errors": scope_errors, "duplicate_result_sets": duplicates}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/phase6-index"))
    parser.add_argument("--benchmark-dir", type=Path, default=Path("data/benchmark"))
    parser.add_argument("--output", type=Path, default=Path("evaluation/results/candidate_coverage.json"))
    parser.add_argument("--dev-cap-experiment", action="store_true")
    parser.add_argument("--results-dir", type=Path, default=Path("evaluation/results"))
    parser.add_argument("--phase6-calibration", type=Path, default=Path("evaluation/results/phase6_retrieval_calibration.json"))
    parser.add_argument("--exploratory", action="store_true")
    args = parser.parse_args()
    if not args.exploratory:
        require_previous_gates("M2", args.results_dir, index_dir=args.index_dir, benchmark_dir=args.benchmark_dir)
    policy = RetrievalPolicy.from_report(args.phase6_calibration, expected_mode="hybrid_rrf")
    manifest = args.index_dir / "manifest.json"
    index = json.loads(manifest.read_text(encoding="utf-8"))
    doc_ids = list(index["documents"])
    report = {"schema_version": 1, "phase": 7,
              "index_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
              "candidate_generation": {"mode": "auto", "rrf_k": 3,
                                       "weights": [1.0, 1.2], "release_cap": 40},
              "phase6_calibration_sha256": sha256(args.phase6_calibration),
              **source_identity(Path(__file__).resolve().parents[1]), "splits": {}}
    splits = ("dev", "test", "holdout") if args.dev_cap_experiment else ("test", "holdout")
    if not args.exploratory:
        splits += ("human_dev", "human_test", "human_holdout")
    for split in splits:
        source = args.benchmark_dir / (f"human_retrieval_{split.removeprefix('human_')}.jsonl" if split.startswith("human_") else f"phase6_retrieval_{split}.jsonl")
        rows = load_jsonl(source)
        caps = (10, 20, 40, 60) if split == "dev" and args.dev_cap_experiment else (40,)
        report["splits"][split] = {"benchmark_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                                   "caps": {}}
        for cap in caps:
            retriever = HybridRetriever(args.index_dir, query_cache_size=0, candidate_limit=cap, policies={"hybrid_rrf": policy})
            report["splits"][split]["caps"][str(cap)] = evaluate_split(rows, retriever, doc_ids, cap)
    test = report["splits"]["test"]["caps"]["40"]
    holdout = report["splits"]["holdout"]["caps"]["40"]
    errors = []
    if test["candidate_recall"] < .99:
        errors.append("test_candidate_recall_below_0.99")
    if holdout["candidate_recall"] < .97:
        errors.append("holdout_candidate_recall_below_0.97")
    if any(part["caps"]["40"][key] for part in report["splits"].values() if "40" in part["caps"]
           for key in ("provenance_errors", "scope_errors", "duplicate_result_sets")):
        errors.append("candidate_provenance_or_scope")
    for split in ("human_dev", "human_test", "human_holdout"):
        if not args.exploratory and report["splits"][split]["caps"]["40"]["candidate_recall"] < .95:
            errors.append(f"{split}_candidate_recall_below_0.95")
    report["status"] = "pass" if not errors and not args.exploratory else "conditional"
    report["errors"] = errors
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "errors": errors,
                      "test_recall_at_40": test["candidate_recall"],
                      "holdout_recall_at_40": holdout["candidate_recall"]}, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
