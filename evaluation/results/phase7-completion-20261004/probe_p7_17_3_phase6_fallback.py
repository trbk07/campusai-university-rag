"""Compare Phase 7 transient-fault fallback with active Phase 6 outputs on dev rows."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "evaluation/results/phase7-completion-20261004"
OUT = TASK / "p7-17-3-current-phase6-fallback-v2.json"


def digest(value) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main() -> int:
    from campusai.retrieval.calibration import RetrievalPolicy
    from campusai.retrieval.cross_encoder_provider import ModelIdentity, RerankerUnavailable
    from campusai.retrieval.hybrid import HybridRetriever
    from campusai.retrieval.rerank_policy import Phase7Policy
    from evaluation.common.release_artifacts import sha256, source_identity, write_json

    if OUT.exists():
        raise FileExistsError(OUT)
    active = json.loads((ROOT / "configs/phase7_release_cycle.json").read_text(encoding="utf-8"))
    bench = ROOT / active["benchmark_dir"]
    results = ROOT / active["results_dir"]
    index = ROOT / active["index_dir"]
    phase6_path = results / "hybrid_retrieval_calibration.json"
    dev_path = bench / "human_retrieval_dev.jsonl"
    rows = [json.loads(line) for line in dev_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    before = source_identity(ROOT)
    policy6 = RetrievalPolicy.from_report(phase6_path, expected_mode="hybrid_rrf")
    smoke = json.loads((TASK / "p7-07-cuda-snapshot-smoke.json").read_text(encoding="utf-8"))
    identity = ModelIdentity(**smoke["model_identity"])
    manifest = index / "manifest.json"

    class TimeoutProvider:
        ready = True
        model_identity = identity

        def __init__(self):
            self.calls = 0

        def score(self, query, candidates):
            self.calls += 1
            raise RerankerUnavailable("reranker_timeout")

        def close(self):
            return None

    provider = TimeoutProvider()
    policy7 = Phase7Policy(
        "p7-17-3-diagnostic", identity.fingerprint, sha256(manifest), sha256(phase6_path), sha256(dev_path),
        0.0, 0.0, 1.0, 100.0, candidate_cap=40, rerank_candidate_cap=40,
    )
    baseline_retriever = HybridRetriever(index, query_cache_size=0, policies={"hybrid_rrf": policy6})
    fault_retriever = HybridRetriever(index, query_cache_size=0, policies={"hybrid_rrf": policy6},
                                      phase7_provider=provider, phase7_policy=policy7, phase7_enabled=True)
    seen_groups = set()
    selected_rows = []
    for row in rows:
        group = row.get("source_group") or row.get("paraphrase_group") or row["qid"]
        if group in seen_groups:
            continue
        seen_groups.add(group)
        selected_rows.append(row)
        if len(selected_rows) == 20:
            break
    observations = []
    checks = {"eligible_dev_group_sample": len(selected_rows) == 20}
    try:
        for row in selected_rows:
            query = row["question"]
            doc_ids = row.get("doc_ids") or None
            filters = row.get("filters") or None
            baseline = [item.to_dict() for item in baseline_retriever.search(
                query, doc_ids=doc_ids, filters=filters, top_k=5, mode="auto")]
            baseline_hash = digest(baseline)
            attempts = []
            for _ in range(2):
                calls_before = provider.calls
                actual = [item.to_dict() for item in fault_retriever.search_phase7(
                    query, doc_ids=doc_ids, filters=filters, top_k=5)]
                calls_after = provider.calls
                trace = fault_retriever.last_trace
                attempts.append({"output_sha256": digest(actual), "equals_phase6": actual == baseline,
                                 "fault_injected": calls_after > calls_before,
                                 "provider_calls_delta": calls_after - calls_before,
                                 "rerank_selected": trace.rerank_selected,
                                 "rerank_fallback": trace.rerank_fallback,
                                 "rerank_reason": trace.rerank_reason,
                                 "retrieval_trace_sha256": digest(trace.to_dict())})
                if calls_after > calls_before:
                    checks["failure_reason_preserved"] = checks.get("failure_reason_preserved", True) and trace.rerank_reason == "reranker_timeout"
                else:
                    checks["no_inference_on_bypass_or_easy_routes"] = checks.get("no_inference_on_bypass_or_easy_routes", True) and trace.rerank_reason != "reranker_timeout"
            observations.append({"qid": row["qid"], "dev_source_group": row.get("source_group"),
                                 "question_sha256": hashlib.sha256(query.encode("utf-8")).hexdigest(),
                                 "baseline_output_sha256": baseline_hash, "baseline_count": len(baseline),
                                 "attempts": attempts})
        checks["all_fallback_outputs_exactly_match_phase6"] = all(
            attempt["equals_phase6"] for obs in observations for attempt in obs["attempts"])
        checks["all_injected_faults_report_transient_timeout"] = all(
            attempt["rerank_reason"] == "reranker_timeout" and attempt["provider_calls_delta"] == 1
            for obs in observations for attempt in obs["attempts"] if attempt["fault_injected"])
        injected = sum(attempt["fault_injected"] for obs in observations for attempt in obs["attempts"])
        checks["multiple_real_index_timeout_fallbacks_observed"] = injected >= 10
        checks["followup_retries_remain_phase6_identical"] = all(
            obs["attempts"][0]["output_sha256"] == obs["attempts"][1]["output_sha256"]
            for obs in observations)
    finally:
        baseline_retriever.close() if hasattr(baseline_retriever, "close") else None
        fault_retriever.close() if hasattr(fault_retriever, "close") else None
        provider.close()
    after = source_identity(ROOT)
    report = {
        "schema_version": 1, "task": "P7-17.3", "status": "PASS_DEV_REAL_INDEX_PHASE6_FALLBACK" if all(checks.values()) else "FAIL",
        "release_eligible": False, "scope": "real active r18 index and Phase 6 calibration; 20 dev source groups; injected transient provider timeout",
        "recorded_at": datetime.now(timezone.utc).isoformat(), "source_identity_before": before,
        "source_identity_after": after, "source_stable": before == after,
        "active_cycle": {"benchmark_dir": active["benchmark_dir"], "results_dir": active["results_dir"],
                         "index_dir": active["index_dir"]},
        "bindings": {"dev_sha256": sha256(dev_path), "index_manifest_sha256": sha256(manifest),
                     "phase6_calibration_sha256": sha256(phase6_path),
                     "model_identity_sha256": identity.fingerprint},
        "sample_count": len(observations), "provider_calls": provider.calls,
        "injected_timeout_attempts": sum(attempt["fault_injected"] for obs in observations for attempt in obs["attempts"]),
        "checks": checks, "observations": observations,
        "limitations": [
            "Dev-only; the provider is a deterministic timeout test double and does not exercise CUDA/native failure recovery.",
            "Does not establish held-out equivalence, permanent-failure shutdown, permits, rollback, or M9 acceptance.",
            "Per-query output bodies are omitted; exact byte-semantic output hashes and equality flags are retained.",
        ],
    }
    write_json(OUT, report)
    print(json.dumps({"status": report["status"], "sample_count": report["sample_count"],
                      "provider_calls": report["provider_calls"], "checks": checks,
                      "source_stable": report["source_stable"], "report": OUT.as_posix()}, indent=2))
    return int(not all(checks.values()) or not report["source_stable"])


if __name__ == "__main__":
    raise SystemExit(main())
