"""Nested connected-group OOF diagnostic for route, reranker config and evidence.

Every outer fold keeps connected query families together. Format/cap/rank policy,
route model and evidence policy are selected only from each outer training fold.
The existing dev packet is provisional pending P7-03/F0 review.
"""
from __future__ import annotations

from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "evaluation/results/phase7-completion-20261004"
DEV = TASK / "p7-02-dev-replay/human_retrieval_dev.jsonl"
BASE_RAW = TASK / "p7-09-full-dev-reranker-raw-v2.json"
BODY_SWEEP = TASK / "p7-09-input-format-ablation-v2.json"
OUT = TASK / "p7-09-nested-joint-oof-v2.json"
FORMATS = ("full_chunk", "body", "section_body", "table_text", "table_window", "body_table_window")
CAPS = (8, 10, 12, 16, 20, 40)
WEIGHTS = (0., .1, .25, .5, .75, 1.)


def main() -> int:
    from campusai.rag.context import benchmark_retrieval_request
    from campusai.retrieval.route_probability import route_observations
    from evaluation.common.release_artifacts import sha256, source_identity, write_json
    from evaluation.common.grouped_folds import stratified_group_folds
    from evaluation.reranker.calibrate_evidence_probabilities import (
        CLASSES, _fold_groups, calibrate_probabilities,
    )
    from evaluation.reranker.calibrate_hard_query_route import route_metrics
    from evaluation.reranker.calibrate_route_probabilities import fit_route_probabilities
    from evaluation.reranker.calibrate_reranker_scores import _quality, calibrated_outputs
    from evaluation.reranker.optimize_reranker_dev import rank_fusion, summarize
    from evaluation.retrieval.compare_retrieval_quality import paired_bootstrap, query_metrics
    from evaluation.benchmarks.connected_groups import connected_groups

    if OUT.exists():
        raise FileExistsError("preserve existing nested joint OOF study")
    rows = [json.loads(line) for line in DEV.read_text(encoding="utf-8").splitlines() if line.strip()]
    base_raw = json.loads(BASE_RAW.read_text(encoding="utf-8"))
    if (len(rows) != 889 or any(row.get("split") != "dev" for row in rows)
            or base_raw.get("dev_sha256") != sha256(DEV)
            or base_raw.get("test_used") or base_raw.get("holdout_used")):
        raise ValueError("nested study accepts only the bound dev packet")
    pools = {obs["qid"]: obs for obs in base_raw["observations"]}
    score_maps = {"full_chunk": {qid: obs["scores"] for qid, obs in pools.items()}}
    format_bindings = {"full_chunk": sha256(BASE_RAW)}
    json.loads(BODY_SWEEP.read_text(encoding="utf-8"))  # require completed, parseable format ablation
    for fmt in FORMATS[1:]:
        path = TASK / f"p7-09-input-ablation-v2-{fmt}.json.gz"
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            variant = json.load(stream)
        if variant.get("dev_sha256") != sha256(DEV) or variant.get("candidate_raw_sha256") != sha256(BASE_RAW):
            raise ValueError(f"candidate/dev binding mismatch for {fmt}")
        score_maps[fmt] = {obs["qid"]: obs["scores"] for obs in variant["observations"]}
        format_bindings[fmt] = sha256(path)
    qids = {row["qid"] for row in rows}
    if set(pools) != qids or any(set(scores) != qids for scores in score_maps.values()):
        raise ValueError("every format and pool must pair the complete dev packet")

    def evidence_label(row):
        if not row["answerable"]:
            return 0
        gold = {(g["doc_id"], g["chunk_id"]) for g in row["gold_evidence"]}
        available = {(x["doc_id"], x["chunk_id"]) for x in pools[row["qid"]]["pool"]}
        return 2 if gold and gold <= available else 1

    groups = _fold_groups(rows)
    outer_labels = [evidence_label(row) for row in rows]
    folds = stratified_group_folds(groups, outer_labels)
    fold_count = len(set(folds))
    before = source_identity(ROOT)
    qrow = {row["qid"]: row for row in rows}
    baseline_all = {qid: obs["baseline"] for qid, obs in pools.items()}
    all_oof_outputs = {}
    prediction_folds = {}
    fold_reports = []

    for fold in range(fold_count):
        train_rows = [row for i, row in enumerate(rows) if folds[i] != fold]
        test_rows = [row for i, row in enumerate(rows) if folds[i] == fold]
        train_ids = {row["qid"] for row in train_rows}
        test_ids = {row["qid"] for row in test_rows}
        train_baseline = {qid: baseline_all[qid] for qid in train_ids}
        test_baseline = {qid: baseline_all[qid] for qid in test_ids}

        # Select one ranking config on outer-train only. Prefer configs that
        # jointly clear dev ranking/all-gold floors; then optimize MRR/nDCG.
        ranking_trials = []
        for fmt in FORMATS:
            for cap in CAPS:
                for weight in WEIGHTS:
                    outputs = {row["qid"]: rank_fusion(pools[row["qid"]]["pool"],
                        score_maps[fmt][row["qid"]], weight, cap)[:5] for row in train_rows}
                    metrics = summarize(train_rows, outputs)
                    ranking_trials.append({"format": fmt, "cap": cap, "rank_weight": weight,
                        "metrics": metrics,
                        "ranking_feasible": metrics["recall5"] >= .95 and metrics["all_gold_coverage5"] >= .95})
        feasible_rankings = [trial for trial in ranking_trials if trial["ranking_feasible"]]
        selected_ranking = max(feasible_rankings or ranking_trials, key=lambda trial: (
            trial["metrics"]["mrr"] + trial["metrics"]["ndcg5"],
            trial["metrics"]["recall5"], trial["metrics"]["all_gold_coverage5"], -trial["cap"]))
        fmt, cap, weight = selected_ranking["format"], selected_ranking["cap"], selected_ranking["rank_weight"]

        train_route_samples = [{"qid": row["qid"], "difficulty": row["difficulty"],
            **route_observations(benchmark_retrieval_request(row, [])["query"], [])}
            for row in train_rows]
        route_model, route_diag, route_feasible = fit_route_probabilities(train_route_samples, train_rows)
        routed_train = set()
        for sample in train_route_samples:
            probability = route_model_probability(route_model, sample)
            if probability is not None and probability >= route_model["threshold"]:
                routed_train.add(sample["qid"])

        train_proposals = build_proposals(train_rows, pools, score_maps[fmt], cap, weight, routed_train)
        try:
            evidence_model_policy, evidence_diag = calibrate_probabilities(
                train_rows, train_baseline, train_proposals)
            evidence_fit_error = None
        except ValueError as error:
            evidence_model_policy = {"threshold": 0.0, "margin_threshold": 0.0,
                                     "low_score_action": "phase6"}
            evidence_diag = {"feasible": False, "fit_error": str(error)}
            evidence_fit_error = str(error)

        test_route_samples = [{"qid": row["qid"], "difficulty": row["difficulty"],
            **route_observations(benchmark_retrieval_request(row, [])["query"], [])}
            for row in test_rows]
        routed_test = set()
        for sample in test_route_samples:
            probability = route_model_probability(route_model, sample)
            if probability is not None and probability >= route_model["threshold"]:
                routed_test.add(sample["qid"])
        test_proposals = build_proposals(test_rows, pools, score_maps[fmt], cap, weight, routed_test)
        outputs = calibrated_outputs(test_baseline, test_proposals, evidence_model_policy,
                                     rows=test_rows)
        all_oof_outputs.update(outputs)
        for row in test_rows:
            prediction_folds[row["qid"]] = fold
        fold_quality = _quality(test_rows, outputs)
        fold_baseline = _quality(test_rows, test_baseline)
        fold_reports.append({"fold": fold, "train_records": len(train_rows), "test_records": len(test_rows),
            "test_groups": len({groups[i] for i, assignment in enumerate(folds) if assignment == fold}),
            "ranking_trials": len(ranking_trials), "ranking_feasible_trial_count": len(feasible_rankings),
            "selected_ranking_config": selected_ranking,
            "route_model": route_model, "route_feasible_on_train": route_feasible,
            "route_train_oof": route_diag["out_of_fold_metrics"],
            "route_test_metrics": route_metrics(test_route_samples, 1., 1., route_model=route_model),
            "train_routed_queries": len(routed_train), "test_routed_queries": len(routed_test),
            "evidence_policy": evidence_model_policy, "evidence_fit_error": evidence_fit_error,
            "evidence_train_oof": {k:v for k,v in evidence_diag.items() if k != "observations"},
            "test_baseline": fold_baseline, "test_selected": fold_quality,
            "test_output_qids": sorted(outputs)})
        print(json.dumps({"fold": fold, "config": {"format": fmt,"cap":cap,"weight":weight},
            "route_feasible_train": route_feasible, "routed_test": len(routed_test),
            "test_quality": fold_quality}, ensure_ascii=False), flush=True)

    if set(all_oof_outputs) != qids:
        raise ValueError("nested OOF must produce exactly one output for every dev qid")
    after = source_identity(ROOT)
    aggregated_baseline = summarize(rows, baseline_all)
    aggregated_selected = summarize(rows, all_oof_outputs)
    connected = connected_groups(rows)
    paired_by_metric = {}
    for metric in ("mrr", "ndcg5", "recall5", "all_gold_recall5", "evidence_recall5"):
        positives = [row for row in rows if row["answerable"]]
        paired_by_metric[metric] = paired_bootstrap(
            [query_metrics(row, all_oof_outputs[row["qid"]])[metric]
             - query_metrics(row, baseline_all[row["qid"]])[metric] for row in positives],
            resamples=10000, seed=7,
            groups=[connected[row["qid"]] for row in positives])
    oof_predictions = [{"qid": row["qid"], "fold": prediction_folds[row["qid"]],
        "connected_group": connected[row["qid"]], "answerable": row["answerable"],
        "difficulty": row["difficulty"], "baseline": baseline_all[row["qid"]],
        "selected": all_oof_outputs[row["qid"]]} for row in rows]
    report = {"schema_version":1,"task":"P7-09","status":"diagnostic",
        "release_eligible":False,"calibration_split":"dev","test_used":False,
        "holdout_used":False,"created_at":datetime.now(timezone.utc).isoformat(),
        "source_stable":before==after,"source_identity_before":before,
        "source_identity_after":after,"dev_sha256":sha256(DEV),
        "candidate_raw_sha256":sha256(BASE_RAW),"format_score_hashes":format_bindings,
        "group_count":len(set(groups)),"outer_fold_count":fold_count,
        "outer_split_method":"stratified_group_folds over connected_groups; evidence-presence class used only for allocation",
        "group_assignment_sha256":hashlib.sha256(json.dumps(
            dict(zip((row["qid"] for row in rows),groups)),sort_keys=True).encode()).hexdigest(),
        "baseline":aggregated_baseline,"nested_group_oof":aggregated_selected,
        "relative_uplift":{"mrr":aggregated_selected["mrr"]/aggregated_baseline["mrr"]-1,
            "ndcg5":aggregated_selected["ndcg5"]/aggregated_baseline["ndcg5"]-1},
        "paired_group_bootstrap":{"resamples":10000,"seed":7,"metrics":paired_by_metric},
        "oof_predictions":oof_predictions,
        "folds":fold_reports,
        "limitations":["This is dev-only nested OOF; the 889-row packet and connected group semantics still require P7-03/F0 review.",
            "Source/runtime/index and model/input identities are diagnostic; no successor freeze exists.",
            "No paired answer/LLM, full application HTTP, or same-config end-to-end resource evidence is included.",
            "Thresholds and config selection are nested within these dev folds but this does not replace held-out M4/M5/M6 or M8/S4/S5 acceptance."]}
    write_json(OUT, report)
    print(json.dumps({"source_stable":report["source_stable"],"groups":report["group_count"],
        "baseline":aggregated_baseline,"nested_oof":aggregated_selected,
        "uplift":report["relative_uplift"],"folds":fold_count},ensure_ascii=False,indent=2))
    return int(not report["source_stable"])


def route_model_probability(model: dict, sample: dict):
    from campusai.retrieval.route_probability import RouteProbabilityModel
    return RouteProbabilityModel.from_dict(model).probability(sample)


def build_proposals(rows, pools, score_maps, cap, weight, routed_qids):
    from evaluation.reranker.optimize_reranker_dev import rank_fusion
    proposals = {}
    for row in rows:
        qid = row["qid"]
        if qid not in routed_qids:
            continue
        pool, scores = pools[qid]["pool"], score_maps[qid]
        head = pool[:cap]
        if not head:
            continue
        ce_order = sorted(head, key=lambda item: (-scores[item["chunk_id"]],item["rank"],item["chunk_id"]))
        ce_scores = [float(scores[item["chunk_id"]]) for item in ce_order]
        proposals[qid] = {"results":rank_fusion(pool,scores,weight,cap)[:5],
            "top_score":ce_scores[0],"margin":ce_scores[0]-ce_scores[1] if len(ce_scores)>1 else 0.0,
            "evidence_inputs":{"ranked_candidates":ce_order,"scores":ce_scores}}
    return proposals


if __name__ == "__main__":
    raise SystemExit(main())
