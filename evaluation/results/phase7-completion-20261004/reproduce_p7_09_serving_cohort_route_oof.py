"""Grouped route OOF on the actual eligible hybrid_rrf serving cohort."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[3]
TASK=ROOT/"evaluation/results/phase7-completion-20261004"
DEV=TASK/"p7-02-dev-replay/human_retrieval_dev.jsonl"
RAW=TASK/"p7-09-full-dev-reranker-raw-v2.json"
OUT=TASK/"p7-09-serving-cohort-route-oof.json"


def main() -> int:
    from campusai.rag.context import benchmark_retrieval_request
    from campusai.retrieval.rerank_policy import route_features
    from evaluation.benchmarks.connected_groups import connected_groups
    from evaluation.common.grouped_folds import stratified_group_folds
    from evaluation.common.release_artifacts import sha256, source_identity, write_json
    from evaluation.reranker.calibrate_hard_query_route import fit_feature_route, route_metrics
    from evaluation.reranker.calibrate_route_probabilities import metrics_from_selection

    if OUT.exists(): raise FileExistsError("preserve prior serving-cohort route OOF")
    rows=[json.loads(line) for line in DEV.read_text(encoding="utf-8").splitlines() if line.strip()]
    raw=json.loads(RAW.read_text(encoding="utf-8"))
    if len(rows)!=889 or any(r.get("split")!="dev" for r in rows) or raw.get("dev_sha256")!=sha256(DEV):
        raise ValueError("route study requires the exact dev-only packet")
    by_id={r["qid"]:r for r in rows}; docs=[]
    pools={o["qid"]:o["baseline"] for o in raw["observations"]}
    samples=[]
    for qid,results in pools.items():
        # Phase7 bypasses exact-code, empty/abstained and singleton baselines.
        if len(results)<2 or results[0].get("retrieval_mode")!="hybrid_rrf":
            continue
        row=by_id[qid]
        query=benchmark_retrieval_request(row,[])['query']
        objects=[SimpleNamespace(**item) for item in results]
        features=route_features(query,objects)
        features.update(confidence=float(results[0].get("confidence_score") or 0.0),
            margin=max(0.0,float(results[0].get("fusion_score") or 0.0)-float(results[1].get("fusion_score") or 0.0)))
        samples.append({"qid":qid,"difficulty":row["difficulty"],**features})
    if len({x['qid'] for x in samples})<30:
        raise ValueError("serving cohort is too small for route OOF")
    full_groups=connected_groups(rows)
    groups=[full_groups[x['qid']] for x in samples]
    labels=[{'easy':0,'hard':1,'medium':2}[x['difficulty']] for x in samples]
    folds=stratified_group_folds(groups,labels)
    before=source_identity(ROOT)
    oof={}; fold_reports=[]
    for fold in sorted(set(folds)):
        train=[x for i,x in enumerate(samples) if folds[i]!=fold]
        test=[x for i,x in enumerate(samples) if folds[i]==fold]
        config,train_metrics,feasible=fit_feature_route(train)
        test_metrics=route_metrics(test,config['easy_confidence_threshold'],config['easy_margin_threshold'],
            config['minimum_agreement'],config['constraint_threshold'])
        for item in test:
            selected=not (item['confidence']>=config['easy_confidence_threshold']
                and item['margin']>=config['easy_margin_threshold'])
            selected |= bool(config['minimum_agreement'] and item['agreement']<config['minimum_agreement'])
            selected |= bool(config['constraint_threshold'] and item['constraints']>=config['constraint_threshold'])
            oof[item['qid']]={"fold":fold,"group":full_groups[item['qid']],"selected":selected,
                "config":config,"difficulty":item['difficulty']}
        fold_reports.append({"fold":fold,"train_records":len(train),"test_records":len(test),
            "train_groups":len({full_groups[x['qid']] for x in train}),
            "test_groups":len({full_groups[x['qid']] for x in test}),
            "config":config,"train_feasible":feasible,"train_metrics":train_metrics,
            "test_metrics":test_metrics})
        print(json.dumps({"fold":fold,"config":config,"train_feasible":feasible,
            "test_metrics":test_metrics}),flush=True)
    eligible=[x for x in samples if x['difficulty'] in {'hard','easy'}]
    selected=[oof[x['qid']]['selected'] for x in eligible]
    aggregate=metrics_from_selection(eligible,selected)
    after=source_identity(ROOT)
    report={"schema_version":1,"task":"P7-09","status":"diagnostic",
        "release_eligible":False,"calibration_split":"dev","test_used":False,
        "holdout_used":False,"created_at":datetime.now(timezone.utc).isoformat(),
        "source_stable":before==after,"source_identity_before":before,"source_identity_after":after,
        "dev_sha256":sha256(DEV),"candidate_raw_sha256":sha256(RAW),
        "feature_contract":"evaluation.reranker.calibrate_hard_query_route.route_features",
        "bypassed_records":len(rows)-len(samples),"eligible_records":len(samples),
        "eligible_hard_easy_records":len(eligible),
        "difficulty_counts":{level:sum(x['difficulty']==level for x in samples) for level in ('hard','easy','medium')},
        "connected_groups_eligible":len(set(groups)),"fold_count":len(set(folds)),
        "outer_oof_metrics":aggregate,"folds":fold_reports,
        "observations":[{"qid":x['qid'],"difficulty":x['difficulty'],"group":full_groups[x['qid']],**oof[x['qid']]} for x in samples],
        "limitations":["Only current dev cohort; group/F0 semantics remain pending actual reviewer sign-off.",
            "This uses threshold feature route; it is diagnostic and not a frozen routing policy.",
            "No held-out route or downstream full HTTP/answer acceptance is included."]}
    write_json(OUT,report)
    print(json.dumps({"source_stable":report['source_stable'],"bypassed":report['bypassed_records'],
        "eligible":report['eligible_records'],"eligible_hard_easy":report['eligible_hard_easy_records'],
        "groups":report['connected_groups_eligible'],"oof_metrics":aggregate},ensure_ascii=False,indent=2))
    return int(not report['source_stable'])


if __name__=="__main__": raise SystemExit(main())
