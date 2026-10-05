"""Recompute nested dev OOF quality, provenance, scope and grouped CIs."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "evaluation/results/phase7-completion-20261004"
DEV = TASK / "p7-02-dev-replay/human_retrieval_dev.jsonl"
BASE_RAW = TASK / "p7-09-full-dev-reranker-raw-v2.json"
NESTED = TASK / "p7-09-nested-joint-oof-v2.json"
INDEX = ROOT / ".tmp/phase7-source-b-restored-p701"
OUT = TASK / "p7-09-nested-quality-recompute.json"


def main() -> int:
    from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence
    from evaluation.common.release_artifacts import sha256, source_identity, write_json
    from evaluation.retrieval.compare_retrieval_quality import compare_split

    if OUT.exists():
        raise FileExistsError("preserve previous nested quality recomputation")
    rows = [json.loads(line) for line in DEV.read_text(encoding="utf-8").splitlines() if line.strip()]
    raw = json.loads(BASE_RAW.read_text(encoding="utf-8"))
    nested = json.loads(NESTED.read_text(encoding="utf-8"))
    manifest = json.loads((INDEX / "manifest.json").read_text(encoding="utf-8"))
    if (sha256(INDEX / "manifest.json") != raw.get("index_sha256")
            or sha256(DEV) != nested.get("dev_sha256")
            or sha256(BASE_RAW) != nested.get("candidate_raw_sha256")
            or len(rows) != 889 or any(row.get("split") != "dev" for row in rows)):
        raise ValueError("quality recompute identity mismatch")
    baseline = {obs["qid"]: obs["baseline"] for obs in raw["observations"]}
    selected = {obs["qid"]: obs["selected"] for obs in nested["oof_predictions"]}
    if set(baseline) != {row["qid"] for row in rows} or set(selected) != set(baseline):
        raise ValueError("nested prediction packet does not pair exact dev qids")
    before = source_identity(ROOT)
    comparison = compare_split(rows, baseline, selected,
        frozen_evidence(INDEX), manifest["documents"], seed=7)
    after = source_identity(ROOT)
    report = {"schema_version":1,"task":"P7-09","status":"diagnostic",
        "release_eligible":False,"calibration_split":"dev","test_used":False,
        "holdout_used":False,"created_at":datetime.now(timezone.utc).isoformat(),
        "source_stable":before==after,"source_identity_before":before,
        "source_identity_after":after,"dev_sha256":sha256(DEV),
        "index_sha256":sha256(INDEX/"manifest.json"),
        "candidate_raw_sha256":sha256(BASE_RAW),"nested_oof_sha256":sha256(NESTED),
        "comparison":comparison,
        "limitations":["All results are nested dev OOF and remain ineligible for held-out release acceptance.",
            "F0/group semantic review is pending; group-clustered statistics are provisional.",
            "The chosen route/evidence policy is infeasible in every outer fold; full application and answer evidence are absent."]}
    write_json(OUT,report)
    print(json.dumps({"source_stable":report["source_stable"],
        "mrr_relative_uplift":comparison["mrr_improvement_relative"],
        "ndcg_relative_uplift":comparison["ndcg5_improvement_relative"],
        "recall5_drop":comparison["recall5_drop_absolute"],
        "negative_fpr":comparison["negative_fpr"],
        "all_gold_baseline":comparison["baseline"]["all_gold_recall5"],
        "all_gold_selected":comparison["phase7"]["all_gold_recall5"],
        "provenance_leakage":comparison["provenance_leakage"],
        "scope_leakage":comparison["scope_leakage"],
        "invalid_citation":comparison["invalid_citation"],
        "paired_mrr":comparison["paired_statistics"]["mrr"]},ensure_ascii=False,indent=2))
    return int(not report["source_stable"])


if __name__=="__main__":
    raise SystemExit(main())
