"""Replay real Phase 7 candidate generation and CUDA reranking on dev only.

Uses the full 889-row dev packet and the named-curriculum source-link behavior
whose P7-05 all-gold candidate coverage was 99.6%. Does not read test/holdout.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import time

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "evaluation/results/phase7-completion-20261004"
DEV = TASK / "p7-02-dev-replay/human_retrieval_dev.jsonl"
INDEX = ROOT / ".tmp/phase7-source-b-restored-p701"
MODEL_REPORT = TASK / "p7-07-cuda-snapshot-smoke.json"
CALIBRATION = TASK / "p7-05-phase6-dev-calibration-expanded-index.json"
RAW_OUT = TASK / "p7-09-full-dev-reranker-raw-v2.json"
REPORT_OUT = TASK / "p7-09-full-dev-feasibility-v2.json"


def main() -> int:
    from campusai.rag.context import benchmark_retrieval_request
    from campusai.retrieval.cross_encoder_provider import (
        ModelIdentity, OfflineCrossEncoderReranker, RerankCandidate, snapshot_sha256,
    )
    from campusai.retrieval.hybrid import HybridRetriever
    import campusai.retrieval.table_links as table_links
    from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence
    from evaluation.common.release_artifacts import sha256, source_identity, write_json
    from evaluation.reranker.optimize_reranker_dev import fit, summarize

    rows = [json.loads(line) for line in DEV.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != 889 or any(row.get("split") != "dev" for row in rows):
        raise ValueError("P7-09 replay is restricted to the validated 889-row dev split")
    if RAW_OUT.exists() or REPORT_OUT.exists():
        raise FileExistsError("preserve existing P7-09 full-dev run; choose new output names")
    smoke = json.loads(MODEL_REPORT.read_text(encoding="utf-8"))
    identity = ModelIdentity(**smoke["model_identity"])
    model_dir = ROOT / ".tmp/phase7-models" / identity.model_revision
    if (identity.device != "cuda" or snapshot_sha256(model_dir) != identity.model_sha256
            or sha256(INDEX / "manifest.json") != "40a3e711298fdb66cdd906b19ad84ab9565dd43badfed7caed4eef81a671bec6"):
        raise ValueError("P7-09 model/index identity mismatch")
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    if calibration.get("index_sha256") != sha256(INDEX / "manifest.json"):
        raise ValueError("dev calibration evidence is not bound to the expanded index")

    evidence = frozen_evidence(INDEX)
    documents = sorted({doc_id for doc_id, _chunk_id in evidence})
    before = source_identity(ROOT)
    retriever = HybridRetriever(INDEX, query_cache_size=0, candidate_limit=40)
    retriever._ensure_loaded(documents)
    for _bm25, dense in retriever._indexes.values():
        if dense is not None:
            dense.device = "cpu"

    # Match the P7-05 candidate-coverage experiment: named curriculum table
    # links are enabled while Phase 6 acceptance thresholds are bypassed.
    original_linked_table_sources = table_links.linked_table_sources
    def linked_with_named_curriculum(query, records, cap, *, include_named_curriculum=False,
                                     named_exact_only=False):
        return original_linked_table_sources(query, records, cap,
            include_named_curriculum=include_named_curriculum,
            named_exact_only=named_exact_only)
    table_links.linked_table_sources = linked_with_named_curriculum

    provider = OfflineCrossEncoderReranker(identity, model_dir, timeout_ms=60000,
        candidate_cap=40, score_cache_size=0)
    observations = []
    retrieval_errors = []
    try:
        provider.warm_up()
        for number, row in enumerate(rows, 1):
            pool = retriever.generate_candidates(
                **benchmark_retrieval_request(row, documents), top_k=40, mode="auto")
            pool_dicts = [item.to_dict() for item in pool]
            candidates = [RerankCandidate(item.chunk_id, item.doc_id, item.chunk_id,
                item.page, item.content, int(item.rank), float(item.fusion_score or 0.0))
                for item in pool]
            started = time.perf_counter()
            ranked = provider.score(row["question"], candidates) if candidates else []
            latency_ms = (time.perf_counter() - started) * 1000
            scores = {item.chunk_id: item.reranker_score for item in ranked}
            observations.append({"qid": row["qid"], "baseline": pool_dicts[:5],
                "pool": pool_dicts, "scores": scores, "latency_ms": latency_ms})
            if number % 50 == 0:
                print(f"replayed {number}/{len(rows)}; candidates={sum(len(x['pool']) for x in observations)}",
                      flush=True)
        provider.drain()
    except Exception as exc:
        retrieval_errors.append({"type": type(exc).__name__, "message": str(exc)[:500]})
        raise
    finally:
        provider.close()
        provider.drain()
        table_links.linked_table_sources = original_linked_table_sources
    after = source_identity(ROOT)

    base_outputs = {obs["qid"]: obs["baseline"] for obs in observations}
    base_metrics = summarize(rows, base_outputs)
    raw = {"schema_version": 1, "release_eligible": False,
        "calibration_split": "dev", "test_used": False, "holdout_used": False,
        "source_identity_before": before, "source_identity_after": after,
        "source_sha256": after["source_sha256"], "runtime_sha256": after["runtime_sha256"],
        "model_identity": identity.to_dict(), "model_identity_sha256": identity.fingerprint,
        "dev_sha256": sha256(DEV), "index_sha256": sha256(INDEX / "manifest.json"),
        "phase6_calibration_sha256": sha256(CALIBRATION),
        "candidate_generation": "HybridRetriever.generate_candidates(mode=auto, top_k=40), named curriculum linkage enabled, Phase 6 acceptance threshold bypassed per P7-05 candidate coverage contract",
        "query_embedding_device": "cpu", "model_scoring_device": identity.device,
        "input_candidate_pool_status": "full-dev-replay", "observations": observations,
        "retrieval_errors": retrieval_errors}
    write_json(RAW_OUT, raw)
    fitted = fit(rows, observations, evidence_signals=("top_logit",),
                 rank_weights=(0., .1, .25, .5, .75, 1.))
    positives = [row for row in rows if row["answerable"]]
    report = {"schema_version": 1, "task": "P7-09", "status": "diagnostic",
        "release_eligible": False,
        "purpose": "full-packet dev feasibility using actual Phase 7 candidate generation and frozen CUDA reranker",
        "source_stable": before == after, "source_identity": after,
        "model_identity": identity.to_dict(), "model_identity_sha256": identity.fingerprint,
        "model_snapshot_sha256": identity.model_sha256,
        "dev_path": DEV.relative_to(ROOT).as_posix(), "dev_sha256": sha256(DEV),
        "dev_records": len(rows), "answerable": len(positives),
        "negative": sum(not row["answerable"] for row in rows),
        "candidate_generation": raw["candidate_generation"],
        "candidate_input_sha256": sha256(RAW_OUT), "index_sha256": sha256(INDEX / "manifest.json"),
        "index_manifest_sha256": sha256(INDEX / "manifest.json"),
        "raw_scores_path": RAW_OUT.relative_to(ROOT).as_posix(),
        "raw_scores_sha256": sha256(RAW_OUT), "queries_scored": len(observations),
        "candidate_counts": {"total": sum(len(obs["pool"]) for obs in observations),
            "empty_queries": sum(not obs["pool"] for obs in observations),
            "mean_per_query": statistics.mean(len(obs["pool"]) for obs in observations),
            "max_per_query": max(len(obs["pool"]) for obs in observations)},
        "baseline": base_metrics,
        "scoring_latency_ms": {"mean": statistics.mean(obs["latency_ms"] for obs in observations),
            "p95": sorted(obs["latency_ms"] for obs in observations)[int(.95 * (len(observations)-1))],
            "scope": "provider score call only; does not include retrieval, HTTP, RAG or LLM"},
        "fitted": fitted,
        "limitations": [
            "All observations are dev-only; no test or holdout was used.",
            "Named table-linkage P7-05 candidate generation bypasses acceptance thresholds and is candidate evidence, not answer acceptance.",
            "Expanded-index Phase 6 calibration fit status is FAIL; its report has no accepted threshold.",
            "No grouped OOF, full route/input/table/dtype/batch ablations, paired answer/LLM outcomes, or same-config resource/HTTP measurements are established.",
            "This diagnostic does not alter official r18 M2 FAIL or establish release readiness."
        ]}
    write_json(REPORT_OUT, report)
    print(json.dumps({"status": report["status"], "source_stable": report["source_stable"],
        "baseline": base_metrics, "candidate_counts": report["candidate_counts"],
        "selected": fitted["selected"], "feasible": fitted["feasible"],
        "trials": len(fitted["trials"]), "raw": RAW_OUT.as_posix()}, ensure_ascii=False, indent=2))
    return int(not report["source_stable"] or bool(retrieval_errors))


if __name__ == "__main__":
    raise SystemExit(main())
