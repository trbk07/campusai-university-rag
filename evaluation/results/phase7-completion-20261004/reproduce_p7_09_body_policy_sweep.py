"""Fit dev-only cap/rank/evidence threshold policies for the body input format."""
from __future__ import annotations

from datetime import datetime, timezone
import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "evaluation/results/phase7-completion-20261004"
DEV = TASK / "p7-02-dev-replay/human_retrieval_dev.jsonl"
BASE_RAW = TASK / "p7-09-full-dev-reranker-raw-v2.json"
BODY_RAW = TASK / "p7-09-input-ablation-v2-body.json.gz"
OUT = TASK / "p7-09-body-policy-sweep.json"


def main() -> int:
    from evaluation.common.release_artifacts import sha256, source_identity, write_json
    from evaluation.reranker.optimize_reranker_dev import fit

    rows = [json.loads(line) for line in DEV.read_text(encoding="utf-8").splitlines() if line.strip()]
    base = json.loads(BASE_RAW.read_text(encoding="utf-8"))
    with gzip.open(BODY_RAW, "rt", encoding="utf-8") as stream:
        body = json.load(stream)
    if (len(rows) != 889 or any(row.get("split") != "dev" for row in rows)
            or body.get("dev_sha256") != sha256(DEV)
            or body.get("candidate_raw_sha256") != sha256(BASE_RAW)
            or body.get("format") != "body"):
        raise ValueError("body policy sweep inputs are not bound to the validated dev replay")
    body_scores = {item["qid"]: item["scores"] for item in body["observations"]}
    by_qid = {item["qid"]: item for item in base["observations"]}
    if set(body_scores) != set(by_qid):
        raise ValueError("body scores do not cover the full candidate replay")
    observations = [{"qid": qid, "baseline": obs["baseline"], "pool": obs["pool"],
        "scores": body_scores[qid]} for qid, obs in by_qid.items()]
    before = source_identity(ROOT)
    fitted = fit(rows, observations,
        evidence_signals=("top_logit", "top_margin", "peak_over_mean"),
        rank_weights=(0., .1, .25, .5, .75, 1.))
    after = source_identity(ROOT)
    trials = fitted["trials"]
    safe = [x for x in trials if x["metrics"]["negative_fpr"] <= .01]
    feasible = [x for x in safe if x["metrics"]["recall5"] >= .95]
    pareto = []
    for threshold in (0., .005, .01, .02, .05, .075, .1):
        group = [x for x in trials if x["metrics"]["negative_fpr"] <= threshold]
        best = max(group, key=lambda x: (x["metrics"]["recall5"], x["metrics"]["mrr"], x["metrics"]["ndcg5"])) if group else None
        if best:
            pareto.append({"max_fpr": threshold, "best_recall_policy": best})
    report = {"schema_version": 1, "task": "P7-09", "status": "diagnostic",
        "release_eligible": False, "calibration_split": "dev", "test_used": False,
        "holdout_used": False, "created_at": datetime.now(timezone.utc).isoformat(),
        "source_stable": before == after, "source_identity_before": before,
        "source_identity_after": after, "dev_sha256": sha256(DEV),
        "base_candidate_raw_sha256": sha256(BASE_RAW), "body_scores_sha256": sha256(BODY_RAW),
        "format": "body", "trial_count": len(trials), "feasible_at_recall95_fpr1": bool(feasible),
        "feasible_trial_count": len(feasible), "best_fpr_le_1pct": max(safe,
            key=lambda x: (x["metrics"]["recall5"], x["metrics"]["mrr"], x["metrics"]["ndcg5"])) if safe else None,
        "best_fpr_le_1pct_by_signal": {signal: (max([x for x in safe if x["evidence_signal"] == signal],
            key=lambda x: (x["metrics"]["recall5"], x["metrics"]["mrr"], x["metrics"]["ndcg5"]))
            if any(x["evidence_signal"] == signal for x in safe) else None)
            for signal in ("top_logit", "top_margin", "peak_over_mean")},
        "fpr_recall_frontier": pareto,
        "feasible_trials": feasible,
        "selection_rule": fitted["selection_rule"],
        "limitations": ["All thresholds are selected and evaluated on the same dev packet; this is exploratory and optimistic.",
            "No grouped OOF or independent split is available until P7-03/F0 reviewer approval.",
            "No same-config HTTP/resource profile or paired answer/LLM evaluation is included."]}
    write_json(OUT, report)
    print(json.dumps({"source_stable": report["source_stable"], "trials": len(trials),
        "feasible": len(feasible), "best_fpr_le_1pct": report["best_fpr_le_1pct"],
        "frontier": pareto}, ensure_ascii=False, indent=2))
    return int(not report["source_stable"])


if __name__ == "__main__":
    raise SystemExit(main())
