"""Check transient failure recovery on the active index using a local provider double."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "evaluation/results/phase7-completion-20261004"
OUT = TASK / "p7-17-4-current-transient-recovery.json"


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def main() -> int:
    from campusai.retrieval.calibration import RetrievalPolicy
    from campusai.retrieval.cross_encoder_provider import ModelIdentity, RerankCandidate, RerankedCandidate, RerankerUnavailable
    from campusai.retrieval.hybrid import HybridRetriever
    from campusai.retrieval.rerank_policy import Phase7Policy
    from evaluation.common.release_artifacts import sha256, source_identity, write_json

    if OUT.exists():
        raise FileExistsError(OUT)
    active = json.loads((ROOT / "configs/phase7_release_cycle.json").read_text(encoding="utf-8"))
    bench, results, index = (ROOT / active[key] for key in ("benchmark_dir", "results_dir", "index_dir"))
    phase6_path, dev_path = results / "hybrid_retrieval_calibration.json", bench / "human_retrieval_dev.jsonl"
    rows = [json.loads(line) for line in dev_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    smoke = json.loads((TASK / "p7-07-cuda-snapshot-smoke.json").read_text(encoding="utf-8"))
    identity = ModelIdentity(**smoke["model_identity"])
    before = source_identity(ROOT)
    policy6 = RetrievalPolicy.from_report(phase6_path, expected_mode="hybrid_rrf")
    manifest = index / "manifest.json"

    class RecoveringProvider:
        ready = True
        model_identity = identity
        calls = 0
        closed = False

        def score(self, query: str, candidates: list[RerankCandidate]):
            self.calls += 1
            if self.calls == 1:
                raise RerankerUnavailable("reranker_timeout")
            return [RerankedCandidate(item.candidate_id, item.doc_id, item.chunk_id, item.page,
                                      item.original_rank, item.original_rrf_score, 1.0 / rank,
                                      rank, identity) for rank, item in enumerate(candidates, 1)]

        def close(self):
            self.closed = True

    provider = RecoveringProvider()
    policy7 = Phase7Policy("p7-17-4-diagnostic", identity.fingerprint, sha256(manifest), sha256(phase6_path),
                           sha256(dev_path), 0, 0, 1, 100, candidate_cap=40, rerank_candidate_cap=40)
    baseline_retriever = HybridRetriever(index, query_cache_size=0, policies={"hybrid_rrf": policy6})
    reranker = HybridRetriever(index, query_cache_size=0, policies={"hybrid_rrf": policy6},
                               phase7_provider=provider, phase7_policy=policy7, phase7_enabled=True)
    try:
        selected = None
        for row in rows:
            baseline = [result.to_dict() for result in baseline_retriever.search(
                row["question"], doc_ids=row.get("doc_ids") or None,
                filters=row.get("filters") or None, top_k=5, mode="auto")]
            after_baseline = [result.to_dict() for result in reranker.search_phase7(
                row["question"], doc_ids=row.get("doc_ids") or None,
                filters=row.get("filters") or None, top_k=5)]
            first_trace = reranker.last_trace
            if provider.calls == 1:
                selected = (row, baseline, after_baseline, first_trace)
                break
        if selected is None:
            raise RuntimeError("no dev query selected the injected provider")
        row, baseline, first_output, first_trace = selected
        second_output = [result.to_dict() for result in reranker.search_phase7(
            row["question"], doc_ids=row.get("doc_ids") or None,
            filters=row.get("filters") or None, top_k=5)]
        second_trace = reranker.last_trace
        checks = {
            "first_transient_timeout_falls_back_exactly_to_phase6": first_output == baseline and first_trace.rerank_reason == "reranker_timeout",
            "transient_timeout_does_not_disable_admission": reranker.phase7_enabled and not provider.closed,
            "next_call_recovers_and_applies_reranking": second_trace.rerank_applied is True and second_trace.rerank_reason != "reranker_timeout",
            "recovery_uses_second_provider_call": provider.calls == 2,
            "second_call_has_provenance_and_valid_order": len(second_output) == len(set(x["chunk_id"] for x in second_output)) and all(x["rank"] == n for n,x in enumerate(second_output,1)),
        }
        observation = {"qid": row["qid"], "source_group": row.get("source_group"),
                       "question_sha256": hashlib.sha256(row["question"].encode("utf-8")).hexdigest(),
                       "phase6_output_sha256": digest(baseline), "first_output_sha256": digest(first_output),
                       "second_output_sha256": digest(second_output), "first_reason": first_trace.rerank_reason,
                       "second_reason": second_trace.rerank_reason,
                       "first_rerank_applied": first_trace.rerank_applied,
                       "second_rerank_applied": second_trace.rerank_applied}
    finally:
        provider.close()
    after = source_identity(ROOT)
    report = {"schema_version": 1, "task": "P7-17.4", "status": "PASS_DEV_TRANSIENT_RECOVERY" if all(checks.values()) else "FAIL",
              "release_eligible": False, "scope": "active r18 index/Phase 6 calibration, one dev query; one injected timeout followed by local provider success",
              "recorded_at": datetime.now(timezone.utc).isoformat(), "source_identity_before": before,
              "source_identity_after": after, "source_stable": before == after,
              "bindings": {"dev_sha256": sha256(dev_path), "index_manifest_sha256": sha256(manifest),
                           "phase6_calibration_sha256": sha256(phase6_path), "model_identity_sha256": identity.fingerprint},
              "provider_calls": provider.calls, "checks": checks, "observation": observation,
              "limitations": ["The reranker is a local test double; no real CUDA/native provider was faulted or recovered.",
                              "Permanent-failure close/admission checks are in the linked controlled fault matrix; this report checks transient recovery only.",
                              "Does not establish M9 acceptance or target-runtime permits/resources."]}
    write_json(OUT, report)
    print(json.dumps({"status": report["status"], "checks": checks,
                      "source_stable": report["source_stable"], "report": OUT.as_posix()}, indent=2))
    return int(not all(checks.values()) or not report["source_stable"])


if __name__ == "__main__":
    raise SystemExit(main())
