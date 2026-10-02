"""Verify rollback using two independent service processes and cache namespaces."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from evaluation.common.release_artifacts import read_json, require_previous_gates, sha256, source_identity, write_json


def probe(args) -> dict:
    from campusai.retrieval.reranker_activation import build_phase7_retriever
    from campusai.retrieval.hybrid import HybridRetriever
    from campusai.retrieval.calibration import RetrievalPolicy
    from campusai.retrieval.canary_rollout import rollback_retriever
    from campusai.rag.cache import RAGAnswerCache, build_rag_cache_key
    from campusai.rag.grounding import GroundedAnswer
    phase6 = args.results_dir / "hybrid_retrieval_calibration.json"
    env = dict(os.environ)
    env["RERANKER_ENABLED"] = "true" if args.probe == "enabled" else "false"
    retriever = build_phase7_retriever(args.index_dir, phase6, args.benchmark_dir / "human_retrieval_dev.jsonl", environ=env)
    if args.probe == "enabled" and not retriever.phase7_enabled:
        raise ValueError("enabled rollback probe rejected activation")
    baseline = HybridRetriever(args.index_dir, policies={"hybrid_rrf": RetrievalPolicy.from_report(phase6)})
    docs = read_json(args.index_dir / "manifest.json")["documents"]
    rows = [json.loads(line) for line in (args.benchmark_dir / "human_retrieval_test.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    provider = retriever.phase7_provider
    calls = [0]
    if provider:
        class CountProvider:
            model_identity = provider.model_identity
            def score(self, query, candidates):
                calls[0] += 1
                return provider.score(query, candidates)
            def close(self):
                provider.close()
        retriever.phase7_provider = CountProvider()
    phase7_key = build_rag_cache_key(question="rollback probe", language="en", doc_ids=docs, filters=None,
                     top_k=5, mode="phase7", corpus_version=sha256(args.index_dir / "manifest.json"), model=None,
                     context_budget={"phase7_retrieval_fingerprint": retriever.phase7_cache_fingerprint})
    cache = RAGAnswerCache(str(args.cache_path))
    try:
        if args.probe == "enabled":
            for row in rows:
                if row["difficulty"] == "hard" and row["answerable"]:
                    retriever.search(row["question"], docs, top_k=5, mode="phase7")
            cache.put(phase7_key, GroundedAnswer("cached phase7 probe", abstained=True, reason="insufficient_evidence"))
        before = calls[0]
        rollback_retriever(retriever)
        actual, expected = {}, {}
        for row in rows:
            kwargs = {"doc_ids": row.get("doc_ids", docs), "filters": row.get("filters"), "top_k": 5}
            actual[row["qid"]] = [r.to_dict() for r in retriever.search(row["question"], mode="phase7", **kwargs)]
            expected[row["qid"]] = [r.to_dict() for r in baseline.search(row["question"], mode="auto", **kwargs)]
        phase6_key = build_rag_cache_key(question="rollback probe", language="en", doc_ids=docs, filters=None,
                     top_k=5, mode="auto", corpus_version=sha256(args.index_dir / "manifest.json"), model=None, context_budget={})
        return {"outputs": actual, "baseline": expected, "phase6_output_preserved": actual == expected,
                "new_reranker_calls": calls[0] - before, "reranker_calls_before_rollback": before,
                "phase7_cache_key": phase7_key, "phase6_cache_key": phase6_key,
                "reranked_cache_reused": cache.get(phase6_key) is not None, "pid": os.getpid()}
    finally:
        cache.close()
        if provider:
            provider.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/hybrid-index"))
    parser.add_argument("--benchmark-dir", type=Path, default=Path("data/benchmark"))
    parser.add_argument("--results-dir", type=Path, default=Path("evaluation/results"))
    parser.add_argument("--work-dir", type=Path, default=Path(".tmp/reranker-rollback"))
    parser.add_argument("--cache-path", type=Path, default=Path(".tmp/reranker-rollback/cache.sqlite"))
    parser.add_argument("--probe", choices=("enabled", "disabled"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.probe:
        args.cache_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(args.output, probe(args))
        return 0
    require_previous_gates("M10", args.results_dir, index_dir=args.index_dir, benchmark_dir=args.benchmark_dir)
    started = time.perf_counter()
    before_hash = sha256(args.index_dir / "manifest.json")
    args.work_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for mode in ("enabled", "disabled"):
        output = args.work_dir / f"{mode}.json"
        subprocess.run([sys.executable, "-m", "evaluation.reranker.verify_reranker_rollback", "--probe", mode,
                        "--index-dir", str(args.index_dir), "--benchmark-dir", str(args.benchmark_dir),
                        "--results-dir", str(args.results_dir), "--cache-path", str(args.cache_path),
                        "--output", str(output)], check=True)
        results.append(read_json(output))
    first, second = results
    elapsed = time.perf_counter() - started
    preserved = first["phase6_output_preserved"] and second["phase6_output_preserved"] and first["outputs"] == second["outputs"]
    passed = (elapsed <= 300 and preserved and first["new_reranker_calls"] == second["new_reranker_calls"] == 0
              and not first["reranked_cache_reused"] and not second["reranked_cache_reused"]
              and first["phase7_cache_key"] != second["phase6_cache_key"] and first["pid"] != second["pid"])
    smoke = read_json(args.results_dir / "model_snapshot_smoke.json")
    from evaluation.common.release_artifacts import policy_bindings
    write_json(args.results_dir / "reranker_rollback.json", {"status": "pass" if passed else "conditional",
               **policy_bindings(args.results_dir),
               **source_identity(Path(__file__).resolve().parents[2]), "index_sha256": before_hash,
               "phase6_calibration_sha256": sha256(args.results_dir / "hybrid_retrieval_calibration.json"),
               "calibration_sha256": sha256(args.results_dir / "reranker_score_calibration.json"),
               "model_identity_sha256": smoke["model_identity_sha256"], "completion_seconds": elapsed,
               "new_reranker_calls": first["new_reranker_calls"] + second["new_reranker_calls"],
               "phase6_output_preserved": preserved, "reranked_cache_reused": first["reranked_cache_reused"] or second["reranked_cache_reused"],
               "index_rebuilt": before_hash != sha256(args.index_dir / "manifest.json"),
               "service_restarted": first["pid"] != second["pid"], "probes": results})
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
