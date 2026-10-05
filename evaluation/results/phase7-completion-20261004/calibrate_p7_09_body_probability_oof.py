"""Exploratory connected-group OOF evidence calibration for body/cap16 dev."""
from __future__ import annotations

from datetime import datetime, timezone
import gzip
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "evaluation/results/phase7-completion-20261004"
DEV = TASK / "p7-02-dev-replay/human_retrieval_dev.jsonl"
BASE_RAW = TASK / "p7-09-full-dev-reranker-raw-v2.json"
BODY_RAW = TASK / "p7-09-input-ablation-v2-body.json.gz"
OUT = TASK / "p7-09-body-probability-oof.json"


def main() -> int:
    from evaluation.common.release_artifacts import sha256, source_identity, write_json
    from evaluation.reranker.optimize_reranker_dev import rank_fusion
    from evaluation.reranker.calibrate_evidence_probabilities import (
        CLASSES, calibrate_probabilities, target_class,
    )

    if OUT.exists():
        raise FileExistsError("preserve existing P7-09 grouped OOF calibration")
    rows = [json.loads(line) for line in DEV.read_text(encoding="utf-8").splitlines() if line.strip()]
    base = json.loads(BASE_RAW.read_text(encoding="utf-8"))
    with gzip.open(BODY_RAW, "rt", encoding="utf-8") as stream:
        body = json.load(stream)
    if (len(rows) != 889 or any(row.get("split") != "dev" for row in rows)
            or body.get("dev_sha256") != sha256(DEV)
            or body.get("candidate_raw_sha256") != sha256(BASE_RAW)):
        raise ValueError("OOF inputs are not bound to the exact dev packet and candidate pools")
    base_obs = {obs["qid"]: obs for obs in base["observations"]}
    score_obs = {obs["qid"]: obs["scores"] for obs in body["observations"]}
    if set(base_obs) != {row["qid"] for row in rows} or set(score_obs) != set(base_obs):
        raise ValueError("OOF candidate/scoring observations must cover all dev qids")
    baseline = {qid: obs["baseline"] for qid, obs in base_obs.items()}
    proposals = {}
    for row in rows:
        qid = row["qid"]
        obs = base_obs[qid]
        pool, scores = obs["pool"], score_obs[qid]
        if not pool:
            continue
        head = pool[:16]
        if any(item["chunk_id"] not in scores or type(scores[item["chunk_id"]]) not in (int, float)
               or not math.isfinite(scores[item["chunk_id"]])
               for item in head):
            raise ValueError(f"missing/invalid body score for {qid}")
        ce_order = sorted(head, key=lambda item: (-scores[item["chunk_id"]], item["rank"], item["chunk_id"]))
        fused = rank_fusion(pool, scores, .5, 16)[:5]
        ce_scores = [float(scores[item["chunk_id"]]) for item in ce_order]
        proposals[qid] = {"results": fused,
            "top_score": ce_scores[0],
            "margin": ce_scores[0]-ce_scores[1] if len(ce_scores)>1 else 0.0,
            "evidence_inputs": {"ranked_candidates": ce_order, "scores": ce_scores}}
    labels = {key: 0 for key in CLASSES}
    for row in rows:
        proposal = proposals.get(row["qid"])
        if proposal:
            labels[CLASSES[target_class(row, proposal)]] += 1
    before = source_identity(ROOT)
    policy, diagnostics = calibrate_probabilities(rows, baseline, proposals)
    after = source_identity(ROOT)
    groups = {x["group"] for x in diagnostics["observations"]}
    report = {"schema_version": 1, "task": "P7-09", "status": "diagnostic",
        "release_eligible": False, "calibration_split": "dev", "test_used": False,
        "holdout_used": False, "created_at": datetime.now(timezone.utc).isoformat(),
        "source_stable": before == after, "source_identity_before": before,
        "source_identity_after": after, "dev_sha256": sha256(DEV),
        "candidate_raw_sha256": sha256(BASE_RAW), "body_score_raw_sha256": sha256(BODY_RAW),
        "config_selection_note": "body format and cap16/rank_weight0.5 were selected on the full same dev packet; OOF evidence-probability scores are grouped, but the overall config comparison is exploratory and not nested OOF.",
        "ranking_policy": {"input_format": "body", "cap": 16, "rank_weight": .5},
        "rows": len(rows), "scored_rows": len(proposals), "unscored_rows": len(rows)-len(proposals),
        "evidence_class_counts": labels, "connected_group_count_scored": len(groups),
        "selected_probability_policy": policy, "comparison": diagnostics,
        "limitations": ["The group schema has not received P7-03 semantic exposure/F0 approval.",
            "Ranking config was selected on the full dev packet, so this does not establish unbiased joint config OOF.",
            "No paired answer/LLM or same-config application HTTP/resource evidence is included.",
            "This cannot change official r18 M2 FAIL or establish release gates."]}
    write_json(OUT, report)
    print(json.dumps({"source_stable": report["source_stable"],
        "scored_rows": report["scored_rows"], "class_counts": labels,
        "connected_group_count_scored": len(groups), "folds": diagnostics["fold_count"],
        "feasible": diagnostics["feasible"], "baseline": diagnostics["baseline"],
        "selected": diagnostics["selected"], "out_of_fold": diagnostics["out_of_fold_quality"]},
        ensure_ascii=False, indent=2))
    return int(not report["source_stable"])


if __name__ == "__main__":
    raise SystemExit(main())
