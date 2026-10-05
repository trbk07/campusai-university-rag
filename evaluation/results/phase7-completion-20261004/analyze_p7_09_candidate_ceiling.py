"""Compute candidate-pool and per-fold cap ranking ceilings on dev only."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "evaluation/results/phase7-completion-20261004"
DEV = TASK / "p7-02-dev-replay/human_retrieval_dev.jsonl"
BASE_RAW = TASK / "p7-09-full-dev-reranker-raw-v2.json"
NESTED = TASK / "p7-09-nested-joint-oof-v2.json"
INDEX = ROOT / ".tmp/phase7-source-b-restored-p701"
OUT = TASK / "p7-09-candidate-ceiling.json"
CAPS = (8, 10, 12, 16, 20, 40)


def ndcg_ceiling(found: int, total_gold: int) -> float:
    if total_gold <= 0:
        return 0.0
    dcg = sum(1 / math.log2(rank + 2) for rank in range(min(found, 5)))
    ideal = sum(1 / math.log2(rank + 2) for rank in range(min(total_gold, 5)))
    return dcg / ideal if ideal else 0.0


def main() -> int:
    from evaluation.common.release_artifacts import sha256, source_identity, write_json
    from evaluation.retrieval.compare_retrieval_quality import query_metrics

    if OUT.exists():
        raise FileExistsError("preserve prior ceiling analysis")
    rows = [json.loads(line) for line in DEV.read_text(encoding="utf-8").splitlines() if line.strip()]
    raw = json.loads(BASE_RAW.read_text(encoding="utf-8"))
    nested = json.loads(NESTED.read_text(encoding="utf-8"))
    if (len(rows) != 889 or raw.get("dev_sha256") != sha256(DEV)
            or nested.get("dev_sha256") != sha256(DEV)
            or nested.get("candidate_raw_sha256") != sha256(BASE_RAW)
            or raw.get("index_sha256") != sha256(INDEX / "manifest.json")):
        raise ValueError("ceiling analysis must bind to the 889-row dev packet and physical index")
    pools = {obs["qid"]: obs for obs in raw["observations"]}
    selected = {obs["qid"]: obs["selected"] for obs in nested["oof_predictions"]}
    folds = {fold: fold_report for fold, fold_report in enumerate(nested["folds"])}
    qfold = {obs["qid"]: obs["fold"] for obs in nested["oof_predictions"]}
    if set(pools) != {row["qid"] for row in rows} or set(selected) != set(pools):
        raise ValueError("ceiling outputs do not pair exact dev qids")
    before = source_identity(ROOT)
    positives = [row for row in rows if row["answerable"]]
    per_cap = {}
    for cap in CAPS:
        hit, all_gold, covered_mass, mrr, ndcg = [], [], [], [], []
        for row in positives:
            gold = {(g["doc_id"], g["chunk_id"]) for g in row["gold_evidence"]}
            candidate = {(x["doc_id"], x["chunk_id"]) for x in pools[row["qid"]]["pool"][:cap]}
            n_found = len(gold & candidate)
            hit.append(bool(n_found)); all_gold.append(bool(gold) and gold <= candidate and len(gold) <= 5)
            covered_mass.append(n_found / len(gold) if gold else 0.0)
            mrr.append(float(n_found > 0)); ndcg.append(ndcg_ceiling(n_found, len(gold)))
        per_cap[str(cap)] = {"answerable":len(positives),"candidate_hit_ceiling_recall5":statistics.mean(hit),
            "candidate_all_gold5_ceiling":statistics.mean(all_gold),
            "candidate_gold_mass_recall":sum(covered_mass[i]*len(positives[i]["gold_evidence"])
                for i in range(len(positives)))/sum(len(x["gold_evidence"]) for x in positives),
            "mrr_ceiling":statistics.mean(mrr),"ndcg5_ceiling":statistics.mean(ndcg)}

    per_query = []
    for row in positives:
        qid=row["qid"]; fold=qfold[qid]; cap=folds[fold]["selected_ranking_config"]["cap"]
        gold={(g["doc_id"],g["chunk_id"]) for g in row["gold_evidence"]}
        head={(x["doc_id"],x["chunk_id"]) for x in pools[qid]["pool"][:cap]}
        actual=query_metrics(row,selected[qid])
        ceiling={"recall5":float(bool(gold&head)),
            "all_gold_recall5":float(bool(gold) and gold<=head and len(gold)<=5),
            "evidence_recall5":len(gold&head)/len(gold) if gold else 0.0,
            "mrr":float(bool(gold&head)),"ndcg5":ndcg_ceiling(len(gold&head),len(gold))}
        per_query.append({"qid":qid,"fold":fold,"cap":cap,"candidate_gold_count":len(gold&head),
            "gold_count":len(gold),"candidate_ceiling":ceiling,"actual_nested_oof":actual,
            "ranking_loss_recall5":ceiling["recall5"]-actual["recall5"],
            "ranking_loss_all_gold5":ceiling["all_gold_recall5"]-actual["all_gold_recall5"]})
    cap_counts={str(cap):sum(item["cap"]==cap for item in per_query) for cap in CAPS}
    report={"schema_version":1,"task":"P7-09","status":"diagnostic",
        "release_eligible":False,"calibration_split":"dev","test_used":False,
        "holdout_used":False,"created_at":datetime.now(timezone.utc).isoformat(),
        "source_stable":before==source_identity(ROOT),"source_identity":before,
        "index_sha256":sha256(INDEX/"manifest.json"),"dev_sha256":sha256(DEV),
        "candidate_raw_sha256":sha256(BASE_RAW),"nested_oof_sha256":sha256(NESTED),
        "candidate_pool_ceilings_by_cap":per_cap,"nested_selected_cap_query_counts":cap_counts,
        "nested_cap_conditioned_oracle":{
            "recall5":statistics.mean(x["candidate_ceiling"]["recall5"] for x in per_query),
            "all_gold_recall5":statistics.mean(x["candidate_ceiling"]["all_gold_recall5"] for x in per_query),
            "evidence_recall5":statistics.mean(x["candidate_ceiling"]["evidence_recall5"] for x in per_query),
            "mrr":statistics.mean(x["candidate_ceiling"]["mrr"] for x in per_query),
            "ndcg5":statistics.mean(x["candidate_ceiling"]["ndcg5"] for x in per_query)},
        "nested_cap_conditioned_actual":{
            key:statistics.mean(x["actual_nested_oof"][key] for x in per_query)
            for key in ("recall5","all_gold_recall5","evidence_recall5","mrr","ndcg5")},
        "queries_where_selected_cap_cannot_cover_gold":sum(
            x["candidate_ceiling"]["recall5"]==0 for x in per_query),
        "queries_with_candidate_ceiling_but_actual_miss":sum(
            x["ranking_loss_recall5"]>0 for x in per_query),
        "per_positive_query":per_query,
        "limitations":["Ceilings assume oracle ordering and are diagnostics on the dev candidate pools only.",
            "The outer dev groups and config remain provisional pending P7-03/F0 review.",
            "No oracle is used as a release policy; this does not replace joint OOF or held-out acceptance."]}
    write_json(OUT,report)
    print(json.dumps({"source_stable":report["source_stable"],"cap_40":per_cap["40"],
        "nested_cap_counts":cap_counts,"selected_cap_oracle":report["nested_cap_conditioned_oracle"],
        "selected_cap_actual":report["nested_cap_conditioned_actual"],
        "queries_with_candidate_ceiling_but_actual_miss":report["queries_with_candidate_ceiling_but_actual_miss"]},ensure_ascii=False,indent=2))
    return int(not report["source_stable"])


if __name__=="__main__":
    raise SystemExit(main())
