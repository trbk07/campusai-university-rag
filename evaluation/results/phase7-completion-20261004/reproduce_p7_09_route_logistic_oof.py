"""Grouped OOF logistic route diagnostic on eligible hybrid_rrf requests."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[3]
TASK=ROOT/"evaluation/results/phase7-completion-20261004"
DEV=TASK/"p7-02-dev-replay/human_retrieval_dev.jsonl"
RAW=TASK/"p7-09-full-dev-reranker-raw-v2.json"
OUT=TASK/"p7-09-route-logistic-oof.json"
FEATURES=("confidence","margin","agreement","constraints","query_length","distinct_documents","concentration")


def metrics(samples,selected):
    hard=[bool(choice) for sample,choice in zip(samples,selected) if sample['difficulty']=='hard']
    easy=[bool(choice) for sample,choice in zip(samples,selected) if sample['difficulty']=='easy']
    if not hard or not easy: raise ValueError('route fold lacks a hard or easy cohort')
    n=sum(selected)
    return {'eligible':len(samples),'selected':n,'hard_recall':sum(hard)/len(hard),
        'easy_unnecessary_rerank_rate':sum(easy)/len(easy),
        'selection_precision':sum(hard)/n if n else 0.0,'hard_count':len(hard),'easy_count':len(easy)}


def choose_threshold(samples,probabilities):
    options=[]
    for threshold in sorted({0.0,1.0,*probabilities}):
        result=metrics(samples,[p>=threshold for p in probabilities])
        feasible=result['hard_recall']>=.95 and result['easy_unnecessary_rerank_rate']<=.20
        utility=result['hard_recall']-max(0.0,result['easy_unnecessary_rerank_rate']-.20)
        options.append((feasible,utility,-result['selected'],threshold,result))
    feasible=[x for x in options if x[0]]
    selected=max(feasible or options,key=lambda x:(x[1],x[2],x[3]))
    return selected[3],selected[4],bool(feasible)


def main()->int:
    from campusai.rag.context import benchmark_retrieval_request
    from campusai.retrieval.rerank_policy import route_features
    from evaluation.benchmarks.connected_groups import connected_groups
    from evaluation.common.grouped_folds import stratified_group_folds
    from evaluation.common.release_artifacts import sha256,source_identity,write_json
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    if OUT.exists():raise FileExistsError('preserve previous logistic route OOF')
    rows=[json.loads(line) for line in DEV.read_text(encoding='utf-8').splitlines() if line.strip()]
    raw=json.loads(RAW.read_text(encoding='utf-8')); by_id={r['qid']:r for r in rows}
    if len(rows)!=889 or raw.get('dev_sha256')!=sha256(DEV):raise ValueError('wrong dev packet')
    samples=[]
    full_groups=connected_groups(rows)
    for obs in raw['observations']:
        results=obs['baseline']
        if len(results)<2 or results[0].get('retrieval_mode')!='hybrid_rrf':continue
        row=by_id[obs['qid']]
        if row['difficulty'] not in {'hard','easy'}:continue
        query=benchmark_retrieval_request(row,[])['query']
        features=route_features(query,[SimpleNamespace(**item) for item in results])
        features.update(confidence=float(results[0].get('confidence_score') or 0.0),
            margin=max(0.0,float(results[0].get('fusion_score') or 0)-float(results[1].get('fusion_score') or 0)))
        samples.append({'qid':row['qid'],'difficulty':row['difficulty'],
            'group':full_groups[row['qid']],**features})
    groups=[x['group'] for x in samples]; labels=[int(x['difficulty']=='hard') for x in samples]
    folds=stratified_group_folds(groups,labels)
    before=source_identity(ROOT); predictions={}; reports=[]
    for fold in sorted(set(folds)):
        train=[x for i,x in enumerate(samples) if folds[i]!=fold]
        test=[x for i,x in enumerate(samples) if folds[i]==fold]
        scaler=StandardScaler().fit([[x[k] for k in FEATURES] for x in train])
        model=LogisticRegression(C=1.0,class_weight='balanced',solver='liblinear',max_iter=5000,random_state=7)
        model.fit(scaler.transform([[x[k] for k in FEATURES] for x in train]),
            [int(x['difficulty']=='hard') for x in train])
        train_probs=model.predict_proba(scaler.transform([[x[k] for k in FEATURES] for x in train]))[:,1].tolist()
        threshold,train_metrics,feasible=choose_threshold(train,train_probs)
        test_probs=model.predict_proba(scaler.transform([[x[k] for k in FEATURES] for x in test]))[:,1].tolist()
        test_metrics=metrics(test,[p>=threshold for p in test_probs])
        for sample,probability in zip(test,test_probs):predictions[sample['qid']]={'fold':fold,'group':sample['group'],'difficulty':sample['difficulty'],'probability':probability,'selected':probability>=threshold}
        reports.append({'fold':fold,'train_count':len(train),'test_count':len(test),
            'train_groups':len({x['group'] for x in train}),'test_groups':len({x['group'] for x in test}),
            'threshold':threshold,'train_feasible':feasible,'train_metrics':train_metrics,
            'test_metrics':test_metrics,'model_coefficients':dict(zip(FEATURES,model.coef_[0].tolist())),
            'model_intercept':float(model.intercept_[0])})
        print(json.dumps({'fold':fold,'threshold':threshold,'train_feasible':feasible,'test':test_metrics}),flush=True)
    selected=[predictions[x['qid']]['selected'] for x in samples]
    aggregate=metrics(samples,selected)
    after=source_identity(ROOT)
    report={'schema_version':1,'task':'P7-09','status':'diagnostic','release_eligible':False,
        'calibration_split':'dev','test_used':False,'holdout_used':False,
        'created_at':datetime.now(timezone.utc).isoformat(),'source_stable':before==after,
        'source_identity_before':before,'source_identity_after':after,'dev_sha256':sha256(DEV),
        'candidate_raw_sha256':sha256(RAW),'feature_allowlist':list(FEATURES),
        'forbidden_features':['difficulty','qid','group','answerability','gold','template','language'],
        'eligible_cohort':'hybrid_rrf with >=2 results and hard/easy difficulty','rows':len(samples),
        'groups':len(set(groups)),'fold_count':len(set(folds)),'outer_oof_metrics':aggregate,
        'folds':reports,'observations':[{'qid':x['qid'],'group':x['group'],'difficulty':x['difficulty'],**predictions[x['qid']]} for x in samples],
        'limitations':['Dev-only and provisional pending P7-03/F0 group and exposure review.',
            'Logistic route does not include a reranker or evidence acceptance decision.',
            'Does not establish held-out route acceptance or M4/M5.']}
    write_json(OUT,report)
    print(json.dumps({'source_stable':report['source_stable'],'eligible':len(samples),
        'groups':report['groups'],'oof':aggregate,'feasible_folds':sum(x['train_feasible'] for x in reports)},indent=2))
    return int(not report['source_stable'])


if __name__=='__main__':raise SystemExit(main())
