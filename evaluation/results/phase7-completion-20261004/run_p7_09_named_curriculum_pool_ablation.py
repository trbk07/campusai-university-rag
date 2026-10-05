"""Dev-only reranker replay comparing existing-code and named curriculum pools."""
from __future__ import annotations

from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "evaluation/results/phase7-completion-20261004"
DEV = TASK / "p7-02-dev-replay/human_retrieval_dev.jsonl"
POOLS = TASK / "p7-05-candidate-dev-expanded"
SMOKE = TASK / "p7-07-cuda-snapshot-smoke.json"
REPORT = TASK / "p7-09-named-curriculum-pool-ablation.json"


def main() -> int:
    from campusai.retrieval.cross_encoder_provider import (
        ModelIdentity, OfflineCrossEncoderReranker, RerankCandidate, snapshot_sha256,
    )
    from evaluation.common.release_artifacts import sha256, source_identity, write_json
    from evaluation.reranker.optimize_reranker_dev import rank_fusion, summarize

    rows = [json.loads(line) for line in DEV.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != 889 or any(row.get("split") != "dev" for row in rows):
        raise ValueError("only the pinned 889-query dev packet is allowed")
    row_by_qid = {row["qid"]: row for row in rows}
    if len(row_by_qid) != len(rows):
        raise ValueError("duplicate qids in dev packet")
    pools = {}
    for name in ("existing_code_rows", "named_curriculum_rows"):
        with gzip.open(POOLS / f"{name}.json.gz", "rt", encoding="utf-8") as stream:
            payload = json.load(stream)
        if set(payload["outputs"]) != set(row_by_qid):
            raise ValueError(f"{name} qids do not exactly bind the dev packet")
        pools[name] = payload["outputs"]

    smoke = json.loads(SMOKE.read_text(encoding="utf-8"))
    identity = ModelIdentity(**smoke["model_identity"])
    # Match prior controlled body-input ablations, holding model snapshot and input format fixed.
    from dataclasses import replace
    identity = replace(identity, input_format="body")
    model_dir = ROOT / ".tmp/phase7-models" / identity.model_revision
    if snapshot_sha256(model_dir) != identity.model_sha256:
        raise ValueError("frozen model snapshot hash mismatch")
    if REPORT.exists() or any((TASK / f"p7-09-named-pool-{name}-scores.json.gz").exists()
                              for name in pools):
        raise FileExistsError("preserve existing named-pool ablation outputs")

    before = source_identity(ROOT)
    started = datetime.now(timezone.utc).isoformat()
    scores_by_pool = {}
    pool_summaries = {}
    for name, outputs in pools.items():
        provider = OfflineCrossEncoderReranker(identity, model_dir, timeout_ms=60000,
                                               candidate_cap=40, score_cache_size=0)
        observations = []
        timer = time.perf_counter()
        try:
            provider.warm_up()
            for idx, (qid, candidates_raw) in enumerate(outputs.items(), 1):
                candidates = [RerankCandidate(
                    item["chunk_id"], item["doc_id"], item["chunk_id"], item["page"],
                    item["content"], int(item["rank"]), float(item.get("fusion_score") or 0.0),
                ) for item in candidates_raw]
                scored = provider.score(row_by_qid[qid]["question"], candidates) if candidates else []
                observations.append({"qid": qid, "scores": {
                    result.chunk_id: result.reranker_score for result in scored
                }})
                if idx % 100 == 0:
                    print(f"{name}: {idx}/{len(outputs)}", flush=True)
            provider.drain()
        finally:
            provider.close()
            provider.drain()
        scores = {item["qid"]: item["scores"] for item in observations}
        scores_by_pool[name] = scores
        raw_path = TASK / f"p7-09-named-pool-{name}-scores.json.gz"
        raw = {
            "schema_version": 1, "task": "P7-09", "release_eligible": False,
            "calibration_split": "dev", "test_used": False, "holdout_used": False,
            "source_identity_before": before, "model_identity": identity.to_dict(),
            "model_identity_sha256": identity.fingerprint, "dev_sha256": sha256(DEV),
            "candidate_pool_sha256": sha256(POOLS / f"{name}.json.gz"),
            "index_manifest_sha256": "40a3e711298fdb66cdd906b19ad84ab9565dd43badfed7caed4eef81a671bec6",
            "pool_name": name, "observations": observations,
        }
        with gzip.open(raw_path, "wt", encoding="utf-8") as stream:
            json.dump(raw, stream, ensure_ascii=False, allow_nan=False)
        pool_summaries[name] = {
            "score_path": raw_path.relative_to(ROOT).as_posix(),
            "score_sha256": sha256(raw_path), "elapsed_seconds": time.perf_counter() - timer,
            "scored_pairs": sum(len(scores[qid]) for qid in scores),
            "candidate_pairs": sum(len(pool) for pool in outputs.values()),
            "trials": [],
        }
        for cap in (8, 10, 12, 16, 20, 40):
            for weight in (0.0, 0.1, 0.25, 0.5, 0.75, 1.0):
                ranked = {row["qid"]: rank_fusion(outputs[row["qid"]], scores[row["qid"]], weight, cap)[:5]
                          for row in rows}
                pool_summaries[name]["trials"].append({
                    "cap": cap, "rank_weight": weight, "metrics": summarize(rows, ranked),
                })
        print(json.dumps({"pool": name, "elapsed_seconds": pool_summaries[name]["elapsed_seconds"],
                          "scored_pairs": pool_summaries[name]["scored_pairs"]}), flush=True)

    baseline = summarize(rows, {o["qid"]: o["baseline"] for o in json.loads(
        (TASK / "p7-09-full-dev-reranker-raw-v2.json").read_text(encoding="utf-8"))["observations"]})
    for pool in pool_summaries.values():
        for trial in pool["trials"]:
            trial["delta_mrr_relative_vs_full_dev_baseline"] = trial["metrics"]["mrr"] / baseline["mrr"] - 1
            trial["delta_ndcg5_relative_vs_full_dev_baseline"] = trial["metrics"]["ndcg5"] / baseline["ndcg5"] - 1
    after = source_identity(ROOT)
    previous_raw = json.loads((TASK / "p7-09-full-dev-reranker-raw-v2.json").read_text(encoding="utf-8"))
    previous_by_qid = {item["qid"]: item["pool"] for item in previous_raw["observations"]}
    pool_binding = {
        "baseline_raw_path": "p7-09-full-dev-reranker-raw-v2.json",
        "baseline_exact_pool_matches": sum(
            previous_by_qid[qid] == pools["named_curriculum_rows"][qid] for qid in row_by_qid
        ),
        "baseline_exact_pool_matches_expected": len(row_by_qid),
        "existing_code_pool_exact_match_to_baseline_count": sum(
            previous_by_qid[qid] == pools["existing_code_rows"][qid] for qid in row_by_qid
        ),
        "interpretation": "The named curriculum pool exactly reproduces the P7-09 full-dev baseline candidate pool; existing-code pool is the controlled alternative.",
    }
    fixed_comparison = {
        name: next(trial for trial in summary["trials"]
                   if trial["cap"] == 40 and trial["rank_weight"] == 0.5)
        for name, summary in pool_summaries.items()
    }
    report = {
        "schema_version": 1, "task": "P7-09", "status": "diagnostic",
        "release_eligible": False, "calibration_split": "dev", "test_used": False,
        "holdout_used": False, "started_at": started,
        "ended_at": datetime.now(timezone.utc).isoformat(), "source_stable": before == after,
        "source_identity_before": before, "source_identity_after": after,
        "dev_sha256": sha256(DEV), "baseline_metrics": baseline,
        "model_identity": identity.to_dict(), "pool_results": pool_summaries,
        "candidate_pool_binding": pool_binding,
        "fixed_config_comparison": fixed_comparison,
        "interpretation": "Exploratory paired dev-only candidate-pool/reranker ablation. Both 889-query pools were rescored with the same pinned CUDA body-input reranker and evaluated with identical rank-fusion settings. Trial selection is not independent confirmation and no release claim is made.",
        "limitations": [
            "Both candidate-generation variants and all ranking trials use the same dev packet; grouped nested OOF and independent human review remain required.",
            "This diagnostic does not establish live RAG, LLM grounding, HTTP capacity, or release gates.",
        ],
    }
    write_json(REPORT, report)
    print(json.dumps({"source_stable": report["source_stable"],
                      "pools": {name: {"candidate_pairs": v["candidate_pairs"],
                                       "scored_pairs": v["scored_pairs"],
                                       "best": max(v["trials"], key=lambda t: (t["metrics"]["mrr"], t["metrics"]["ndcg5"]))}
                                for name, v in pool_summaries.items()}}, ensure_ascii=False, indent=2))
    return int(not report["source_stable"])


if __name__ == "__main__":
    raise SystemExit(main())
