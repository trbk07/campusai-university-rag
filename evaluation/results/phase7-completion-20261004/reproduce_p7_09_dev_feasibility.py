"""Score the validated 889-row dev candidate pool with the real frozen model.

Fits diagnostics on dev only. No test/holdout data is read or written.
"""
from __future__ import annotations

from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "evaluation/results/phase7-completion-20261004"
DEV = TASK / "p7-02-dev-replay/human_retrieval_dev.jsonl"
INDEX = ROOT / ".tmp/phase7-source-b-restored-p701"
MODEL_REPORT = TASK / "p7-07-cuda-snapshot-smoke.json"
CALIBRATION = TASK / "p7-05-phase6-dev-calibration-expanded-index.json"
CANDIDATE_RAW = TASK / "p7-05-candidate-dev-expanded/named_curriculum_rows.json.gz"
RAW_OUT = TASK / "p7-09-reranker-dev-raw.json"
REPORT_OUT = TASK / "p7-09-dev-feasibility.json"


def main() -> int:
    from campusai.retrieval.cross_encoder_provider import (
        ModelIdentity, OfflineCrossEncoderReranker, RerankCandidate, snapshot_sha256,
    )
    from evaluation.common.release_artifacts import sha256, source_identity, write_json
    from evaluation.reranker.optimize_reranker_dev import fit, rank_fusion, summarize

    rows = [json.loads(line) for line in DEV.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != 889 or any(row.get("split") != "dev" for row in rows):
        raise ValueError("P7-09 feasibility study is restricted to the validated 889-row dev split")
    if RAW_OUT.exists() or REPORT_OUT.exists():
        raise FileExistsError("preserve existing P7-09 run; choose new task output names")
    candidate_part = gzip.open(CANDIDATE_RAW, "rt", encoding="utf-8")
    with candidate_part:
        prior = json.load(candidate_part)
    pools = prior["outputs"]
    if set(pools) != {row["qid"] for row in rows}:
        raise ValueError("candidate pool does not pair the complete dev packet")
    smoke = json.loads(MODEL_REPORT.read_text(encoding="utf-8"))
    identity = ModelIdentity(**smoke["model_identity"])
    model_dir = ROOT / ".tmp/phase7-models" / identity.model_revision
    if (identity.device != "cuda" or snapshot_sha256(model_dir) != identity.model_sha256
            or sha256(INDEX / "manifest.json") != "40a3e711298fdb66cdd906b19ad84ab9565dd43badfed7caed4eef81a671bec6"):
        raise ValueError("P7-09 model/index identity mismatch")
    if json.loads(CALIBRATION.read_text(encoding="utf-8")).get("index_sha256") != sha256(INDEX / "manifest.json"):
        raise ValueError("dev calibration evidence is not bound to the expanded index")
    before = source_identity(ROOT)
    provider = OfflineCrossEncoderReranker(identity, model_dir, timeout_ms=60000,
                                             candidate_cap=40, score_cache_size=0)
    observations = []
    try:
        provider.warm_up()
        for number, row in enumerate(rows, 1):
            pool = pools[row["qid"]]
            candidates = [RerankCandidate(item["chunk_id"], item["doc_id"], item["chunk_id"],
                item["page"], item["content"], int(item["rank"]), float(item.get("fusion_score") or 0.0))
                for item in pool]
            started = time.perf_counter()
            ranked = provider.score(row["question"], candidates) if candidates else []
            scores = {item.chunk_id: item.reranker_score for item in ranked}
            observations.append({"qid": row["qid"], "baseline": pool[:5], "pool": pool,
                "scores": scores, "latency_ms": (time.perf_counter() - started) * 1000})
            if number % 50 == 0:
                print(f"scored {number}/{len(rows)}", flush=True)
        provider.drain()
    finally:
        provider.close()
        provider.drain()
    after = source_identity(ROOT)
    raw = {"schema_version": 1, "release_eligible": False, "calibration_split": "dev",
        "test_used": False, "holdout_used": False, "source_identity_before": before,
        "source_identity_after": after, "source_sha256": after["source_sha256"],
        "runtime_sha256": after["runtime_sha256"], "model_identity": identity.to_dict(),
        "model_identity_sha256": identity.fingerprint,
        "dev_sha256": sha256(DEV), "index_sha256": sha256(INDEX / "manifest.json"),
        "phase6_calibration_sha256": sha256(CALIBRATION), "input_candidate_raw_sha256": sha256(CANDIDATE_RAW),
        "input_candidate_pool_status": prior.get("status"), "observations": observations}
    write_json(RAW_OUT, raw)
    fitted = fit(rows, observations, evidence_signals=("top_logit",), rank_weights=(0., .1, .25, .5, .75, 1.))
    selected = fitted["selected"]
    outputs = {}
    for row, obs in zip(rows, observations, strict=True):
        pool, scores = obs["pool"], obs["scores"]
        top_scores = sorted((scores[item["chunk_id"]] for item in pool[:selected["cap"]]), reverse=True)
        signal = (-float("inf") if not top_scores else top_scores[0])
        outputs[row["qid"]] = rank_fusion(pool, scores, selected["rank_weight"], selected["cap"] )[:5] \
            if signal >= selected["evidence_threshold"] else []
    fitted["baseline_all_gold_coverage5"] = summarize(
        rows, {row["qid"]: pools[row["qid"]][:5] for row in rows}
    )["all_gold_coverage5"]
    positives = [row for row in rows if row["answerable"]]
    fitted["selected_all_gold_coverage5"] = (sum(
        {(gold["doc_id"], gold["chunk_id"]) for gold in row["gold_evidence"]} <=
        {(item["doc_id"], item["chunk_id"]) for item in outputs[row["qid"]]}
        for row in positives) / len(positives))
    report = {"schema_version": 1, "task": "P7-09", "status": "diagnostic",
        "release_eligible": False, "purpose": "dev-only real-model reranking feasibility and threshold/rank-fusion study",
        "started_at": datetime.now(timezone.utc).isoformat(), "source_stable": before == after,
        "source_identity": after, "model_identity": identity.to_dict(),
        "model_identity_sha256": identity.fingerprint, "model_snapshot_sha256": identity.model_sha256,
        "dev_path": DEV.relative_to(ROOT).as_posix(), "dev_sha256": sha256(DEV),
        "dev_records": len(rows), "answerable": sum(row["answerable"] for row in rows),
        "negative": sum(not row["answerable"] for row in rows),
        "candidate_input_sha256": sha256(CANDIDATE_RAW), "index_sha256": sha256(INDEX / "manifest.json"),
        "index_manifest_sha256": sha256(INDEX / "manifest.json"),
        "raw_scores_path": RAW_OUT.relative_to(ROOT).as_posix(), "raw_scores_sha256": sha256(RAW_OUT),
        "model_scored_queries": len(observations), "empty_candidate_queries": sum(not x["pool"] for x in observations),
        "mean_model_scoring_latency_ms": sum(x["latency_ms"] for x in observations) / len(observations),
        "fitted": fitted,
        "limitations": [
            "All 889 observations are dev-only, including inherited/previously exposed questions; they cannot support held-out acceptance.",
            "The M2 all-gold floor, route calibration, complete grouped uncertainty and semantic-review acceptance remain separate gates.",
            "The dev Phase 6 calibration fit is recorded as FAIL; this ranking feasibility study uses candidate generation independent of the answer-acceptance threshold.",
            "This result does not change the active r18 M2 FAIL or create a successor freeze."
        ]}
    write_json(REPORT_OUT, report)
    print(json.dumps({"status": report["status"], "baseline": fitted["baseline"],
        "selected": fitted["selected"], "feasible": fitted["feasible"],
        "baseline_all_gold_coverage5": fitted["baseline_all_gold_coverage5"],
        "selected_all_gold_coverage5": fitted["selected_all_gold_coverage5"],
        "trials": len(fitted["trials"]), "raw": RAW_OUT.as_posix()}, ensure_ascii=False, indent=2))
    return int(not report["source_stable"])


if __name__ == "__main__":
    raise SystemExit(main())
