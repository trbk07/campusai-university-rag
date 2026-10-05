"""Controlled dev-only input-format ablation on the frozen full candidate pools."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "evaluation/results/phase7-completion-20261004"
DEV = TASK / "p7-02-dev-replay/human_retrieval_dev.jsonl"
RAW = TASK / "p7-09-full-dev-reranker-raw-v2.json"
MODEL_REPORT = TASK / "p7-07-cuda-snapshot-smoke.json"
FORMATS = ("body", "section_body", "table_text", "table_window", "body_table_window")
RUN = "v2"
REPORT_OUT = TASK / f"p7-09-input-format-ablation-{RUN}.json"


def main() -> int:
    from campusai.retrieval.cross_encoder_provider import (
        ModelIdentity, OfflineCrossEncoderReranker, RerankCandidate, snapshot_sha256,
    )
    from evaluation.common.release_artifacts import sha256, source_identity, write_json
    from evaluation.reranker.optimize_reranker_dev import rank_fusion, summarize

    rows = [json.loads(line) for line in DEV.read_text(encoding="utf-8").splitlines() if line.strip()]
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    if len(rows) != 889 or any(row.get("split") != "dev" for row in rows):
        raise ValueError("input ablation accepts exactly the dev-only packet")
    if raw.get("dev_sha256") != sha256(DEV) or raw.get("test_used") or raw.get("holdout_used"):
        raise ValueError("candidate pools do not bind the permitted dev packet")
    if {row["qid"] for row in rows} != {obs["qid"] for obs in raw["observations"]}:
        raise ValueError("candidate pools must cover all dev qids")
    smoke = json.loads(MODEL_REPORT.read_text(encoding="utf-8"))
    base_identity = ModelIdentity(**smoke["model_identity"])
    model_dir = ROOT / ".tmp/phase7-models" / base_identity.model_revision
    if snapshot_sha256(model_dir) != base_identity.model_sha256:
        raise ValueError("frozen model snapshot hash mismatch")
    if REPORT_OUT.exists() or any((TASK / f"p7-09-input-ablation-{RUN}-{fmt}.json.gz").exists() for fmt in FORMATS):
        raise FileExistsError("preserve previous input ablation artifacts")

    before = source_identity(ROOT)
    started_at = datetime.now(timezone.utc).isoformat()
    row_by_qid = {row["qid"]: row for row in rows}
    variants = {}
    for fmt in FORMATS:
        identity = replace(base_identity, input_format=fmt)
        provider = OfflineCrossEncoderReranker(identity, model_dir, timeout_ms=60000,
            candidate_cap=40, score_cache_size=0)
        observations = []
        started = time.perf_counter()
        try:
            provider.warm_up()
            for number, obs in enumerate(raw["observations"], 1):
                candidates = [RerankCandidate(item["chunk_id"], item["doc_id"], item["chunk_id"],
                    item["page"], item["content"], int(item["rank"]),
                    float(item.get("fusion_score") or 0.0)) for item in obs["pool"]]
                scores = provider.score(row_by_qid[obs["qid"]]["question"], candidates) if candidates else []
                observations.append({"qid": obs["qid"], "scores": {
                    result.chunk_id: result.reranker_score for result in scores}})
                if number % 100 == 0:
                    print(f"{fmt}: {number}/{len(raw['observations'])}", flush=True)
            provider.drain()
        finally:
            provider.close()
            provider.drain()
        raw_variant = {"schema_version": 1, "task": "P7-09", "format": fmt,
            "release_eligible": False, "calibration_split": "dev", "test_used": False,
            "holdout_used": False, "source_identity_before": before,
            "model_identity": identity.to_dict(), "model_identity_sha256": identity.fingerprint,
            "base_model_snapshot_sha256": base_identity.model_sha256,
            "dev_sha256": sha256(DEV), "candidate_raw_sha256": sha256(RAW),
            "index_sha256": raw["index_sha256"], "candidate_generation": raw["candidate_generation"],
            "observations": observations}
        out = TASK / f"p7-09-input-ablation-{RUN}-{fmt}.json.gz"
        with gzip.open(out, "wt", encoding="utf-8") as stream:
            json.dump(raw_variant, stream, ensure_ascii=False, allow_nan=False)
        outputs = {}
        score_map = {item["qid"]: item["scores"] for item in observations}
        by_qid = {item["qid"]: item for item in raw["observations"]}
        for cap in (8, 10, 12, 16, 20, 40):
            for weight in (0., .1, .25, .5, .75, 1.):
                outputs.clear()
                for row in rows:
                    pool = by_qid[row["qid"]]["pool"]
                    outputs[row["qid"]] = rank_fusion(pool, score_map[row["qid"]], weight, cap)[:5]
                metrics = summarize(rows, outputs)
                variants.setdefault(fmt, []).append({"cap": cap, "rank_weight": weight,
                    "metrics": metrics})
        variants[fmt] = {"raw_path": out.relative_to(ROOT).as_posix(),
            "raw_sha256": sha256(out), "model_identity": identity.to_dict(),
            "elapsed_seconds": time.perf_counter() - started, "trials": variants[fmt]}
        print(json.dumps({"format": fmt, "elapsed_seconds": variants[fmt]["elapsed_seconds"],
            "trials": len(variants[fmt]["trials"])}), flush=True)
    after = source_identity(ROOT)
    baseline = summarize(rows, {obs["qid"]: obs["baseline"] for obs in raw["observations"]})
    for fmt, data in variants.items():
        for trial in data["trials"]:
            trial["delta_mrr_relative"] = trial["metrics"]["mrr"] / baseline["mrr"] - 1
            trial["delta_ndcg5_relative"] = trial["metrics"]["ndcg5"] / baseline["ndcg5"] - 1
        data["best_ranking_only"] = max(data["trials"], key=lambda x: (x["metrics"]["mrr"], x["metrics"]["ndcg5"]))
    report = {"schema_version": 1, "task": "P7-09", "status": "diagnostic",
        "release_eligible": False, "calibration_split": "dev", "test_used": False,
        "holdout_used": False, "started_at": started_at,
        "ended_at": datetime.now(timezone.utc).isoformat(), "source_stable": before == after,
        "source_identity_before": before, "source_identity_after": after,
        "dev_sha256": sha256(DEV), "candidate_raw_sha256": sha256(RAW),
        "baseline_metrics": baseline, "formats": variants,
        "best_variant": max(((fmt, data["best_ranking_only"]) for fmt, data in variants.items()),
            key=lambda x: (x[1]["metrics"]["mrr"], x[1]["metrics"]["ndcg5"])),
        "interpretation": "Controlled ranking-only input-format ablation; all variants use identical 889 dev queries, actual frozen candidate pools, CUDA snapshot/dtype/batch/candidate cap and index. Exploratory only; no grouped OOF or held-out data.",
        "limitations": ["No evidence policy/threshold fitting or HTTP/resource profiling is included in this ablation.",
            "P7-09 still requires grouped OOF, route/subset/table/dtype/batch ablations, uplift/ceiling analysis and joint answer/runtime feasibility."]}
    write_json(REPORT_OUT, report)
    print(json.dumps({"source_stable": report["source_stable"],
        "baseline": baseline, "best_variant": report["best_variant"]}, ensure_ascii=False, indent=2))
    return int(not report["source_stable"])


if __name__ == "__main__":
    raise SystemExit(main())
