"""Recompute threshold frontier from persisted grouped route OOF probabilities."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "evaluation/results/phase7-completion-20261004"
ROUTE = TASK / "p7-09-route-oof.json"
DEV = TASK / "p7-02-dev-replay/human_retrieval_dev.jsonl"
OUT = TASK / "p7-09-route-oof-frontier.json"


def main() -> int:
    from evaluation.reranker.calibrate_route_probabilities import metrics_from_selection

    route = json.loads(ROUTE.read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in DEV.read_text(encoding="utf-8").splitlines() if line.strip()]
    by_qid = {row["qid"]: row for row in rows}
    observations = route["grouped_oof"]["observations"]
    samples, probabilities = [], []
    for obs in observations:
        row = by_qid[obs["qid"]]
        if row["difficulty"] not in {"hard", "easy"}:
            continue
        samples.append({"qid": row["qid"], "difficulty": row["difficulty"]})
        probabilities.append(obs["probability"])
    thresholds = sorted({0.0, 1.0, *(value for value in probabilities if value is not None)})
    trials = []
    for threshold in thresholds:
        metrics = metrics_from_selection(samples,
            [value is not None and value >= threshold for value in probabilities])
        trials.append({"threshold": threshold, **metrics})
    under_easy_budget = [x for x in trials if x["easy_unnecessary_rerank_rate"] <= .20]
    at_hard_floor = [x for x in trials if x["hard_recall"] >= .95]
    best_hard = max(under_easy_budget,
        key=lambda x: (x["hard_recall"], -x["easy_unnecessary_rerank_rate"]))
    best_easy = min(at_hard_floor,
        key=lambda x: (x["easy_unnecessary_rerank_rate"], -x["hard_recall"])) if at_hard_floor else None
    report = {"schema_version": 1, "task": "P7-09", "status": "diagnostic",
        "release_eligible": False, "calibration_split": "dev",
        "route_oof_sha256": hashlib.sha256(ROUTE.read_bytes()).hexdigest(),
        "threshold_trials": len(trials),
        "max_hard_recall_at_easy_rate_le_20pct": best_hard,
        "minimum_easy_rate_at_hard_recall_ge_95pct": best_easy,
        "note": "Thresholds evaluated on grouped OOF probabilities; group semantic/F0 approval remains pending."}
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"trials": len(trials), "best_hard_recall_under_easy20": best_hard,
        "minimum_easy_rate_at_hard95": best_easy}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
