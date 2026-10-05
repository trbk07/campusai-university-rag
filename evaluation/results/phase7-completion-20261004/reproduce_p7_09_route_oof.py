"""Refit hard-query router using current expanded-index dev queries and group OOF."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "evaluation/results/phase7-completion-20261004"
DEV = TASK / "p7-02-dev-replay/human_retrieval_dev.jsonl"
BASE_RAW = TASK / "p7-09-full-dev-reranker-raw-v2.json"
OUT = TASK / "p7-09-route-oof.json"


def main() -> int:
    from campusai.rag.context import benchmark_retrieval_request
    from campusai.retrieval.route_probability import FEATURES, route_observations
    from evaluation.common.release_artifacts import sha256, source_identity, write_json
    from evaluation.reranker.calibrate_evidence_probabilities import _fold_groups
    from evaluation.reranker.calibrate_hard_query_route import route_metrics
    from evaluation.reranker.calibrate_route_probabilities import fit_route_probabilities

    if OUT.exists():
        raise FileExistsError("preserve prior P7-09 grouped route fit")
    rows = [json.loads(line) for line in DEV.read_text(encoding="utf-8").splitlines() if line.strip()]
    raw = json.loads(BASE_RAW.read_text(encoding="utf-8"))
    if (len(rows) != 889 or any(row.get("split") != "dev" for row in rows)
            or raw.get("dev_sha256") != sha256(DEV)
            or raw.get("test_used") or raw.get("holdout_used")):
        raise ValueError("route fit requires exact dev-only inputs")
    if {row["qid"] for row in rows} != {item["qid"] for item in raw["observations"]}:
        raise ValueError("route observations must bind every dev qid")
    before = source_identity(ROOT)
    samples = []
    for row in rows:
        query = benchmark_retrieval_request(row, [])["query"]
        features = route_observations(query, [])
        samples.append({"qid": row["qid"], "difficulty": row["difficulty"], **features})
    groups = _fold_groups(rows)
    group_count = len(set(groups))
    model, diagnostics, feasible = fit_route_probabilities(samples, rows)
    selected = route_metrics(samples, 1., 1., route_model=model)
    after = source_identity(ROOT)
    report = {"schema_version": 1, "task": "P7-09", "status": "diagnostic",
        "release_eligible": False, "calibration_split": "dev", "test_used": False,
        "holdout_used": False, "created_at": datetime.now(timezone.utc).isoformat(),
        "source_stable": before == after, "source_identity_before": before,
        "source_identity_after": after, "dev_sha256": sha256(DEV),
        "candidate_raw_sha256": sha256(BASE_RAW), "rows": len(rows),
        "difficulty_counts": {level: sum(row["difficulty"] == level for row in rows)
                               for level in sorted({row["difficulty"] for row in rows})},
        "connected_groups": group_count, "feature_allowlist": list(FEATURES),
        "forbidden_features": ["qid", "difficulty", "language", "template", "gold", "candidate_count"],
        "route_model": model, "grouped_oof": diagnostics,
        "dev_feasible": feasible, "selected_fitted_metrics": selected,
        "interpretation": "Grouped connected-family OOF fit on dev only; group semantics/F0 remain subject to P7-03 reviewer approval. This is a diagnostic and is not the frozen Phase 7 route calibration.",
        "limitations": ["Config/route features are evaluated on the same dev packet used for fitting; not held-out acceptance.",
            "P7-03 exposure approval, P7-06 paired answers/live LLM, P7-08 application telemetry and P7-09 joint ranking/evidence policy remain outstanding."]}
    write_json(OUT, report)
    print(json.dumps({"source_stable": report["source_stable"],
        "difficulty_counts": report["difficulty_counts"], "connected_groups": group_count,
        "folds": diagnostics["fold_count"], "feasible": feasible,
        "oof": diagnostics["out_of_fold_metrics"], "fitted": diagnostics["fitted_metrics"]},
        ensure_ascii=False, indent=2))
    return int(not report["source_stable"])


if __name__ == "__main__":
    raise SystemExit(main())
