"""Nested dev-only utility routing before any CE inference.

The additional head predicts repairable ranking/evidence gaps from retrieval
features. Gold supplies training targets only; both heads are group OOF.
"""
import argparse
import gzip
import json
from pathlib import Path
import numpy as np

from campusai.retrieval.route_probability import RouteProbabilityModel,route_observations
from campusai.retrieval.route_utility import UtilityRouteModel,FEATURE_NAMES,VERSION,utility_features
from evaluation.benchmarks.dev_inheritance import rows_at
from evaluation.common.artifact_store import resolve_artifact
from evaluation.common.release_artifacts import read_json,write_json,sha256,source_identity
from evaluation.reranker.calibrate_route_probabilities import fit_route_probabilities,metrics_from_selection
from evaluation.reranker.optimize_reranker_dev import rank_fusion,summarize
from scripts.benchmarks.analyze_phase7_ranking_replay import (
    fold_assignments,eligible,baseline_covered,ordered_pool,group_bootstrap)

ROOT=Path(__file__).resolve().parents[2]
THRESHOLDS=(.1,.2,.3,.4,.5,.6,.7,.8,.9,1.)
WEIGHTS=(0.,.1,.25,.5,.75,1.)
CAP=20


def repairable(row,observation):
    if not row['answerable'] or not baseline_covered(observation):return False
    gold={g['chunk_id'] for g in row['gold_evidence']}
    ids={r['chunk_id'] for r in ordered_pool(observation,'baseline_priority')[:CAP]}
    baseline=observation['baseline'][:5]
    return bool(gold & ids) and (baseline[0]['chunk_id'] not in gold
        or not gold<={r['chunk_id'] for r in baseline})


def fit_head(qids,vectors,targets):
    from sklearn.linear_model import LogisticRegression
    labels=[int(targets[qid]) for qid in qids]
    if set(labels)!={0,1}:raise ValueError('utility training fold needs both classes')
    x=np.asarray([[vectors[qid][key] for key in FEATURE_NAMES] for qid in qids],dtype=float)
    means=x.mean(axis=0);scales=np.maximum(x.std(axis=0),.1)
    fitted=LogisticRegression(C=1.,class_weight='balanced',max_iter=2000,random_state=20261007)
    fitted.fit((x-means)/scales,labels)
    if max(fitted.n_iter_)>=2000:raise ValueError('utility logistic fit did not converge')
    return UtilityRouteModel(VERSION,FEATURE_NAMES,tuple(map(float,means)),tuple(map(float,scales)),
        tuple(map(float,fitted.coef_[0])),float(fitted.intercept_[0]))


def route_ok(metrics):
    return metrics['hard_recall']>=.95 and metrics['easy_unnecessary_rerank_rate']<=.20


def analyze(rows,observations,inherited):
    obs={o['qid']:o for o in observations}
    if len(obs)!=len(observations) or set(obs)!={r['qid'] for r in rows}:raise ValueError('unpaired dev observations')
    groups,folds=fold_assignments(rows)
    base={qid:o['baseline'] for qid,o in obs.items()}
    eligible_ids={qid for qid,o in obs.items() if eligible(o)}
    old_features={qid:route_observations(o['actual_request']['query'],o['pool']) for qid,o in obs.items()}
    vectors={qid:utility_features(obs[qid]['actual_request']['query'],obs[qid]['baseline'],obs[qid]['pool']) for qid in eligible_ids}
    proposals={}
    for weight in WEIGHTS:
        proposals[weight]={}
        for qid,o in obs.items():
            proposals[weight][qid]=base[qid] if weight==0 or not baseline_covered(o) else rank_fusion(
                ordered_pool(o,'baseline_priority'),o['scores'],weight,CAP)[:5]
    outputs,selections,reports={},{},[]
    for fold in range(3):
        train=[r for r in rows if folds[r['qid']]!=fold];valid=[r for r in rows if folds[r['qid']]==fold]
        assessed=[r for r in train if r['qid'] in eligible_ids and r['difficulty'] in ('hard','easy')]
        samples=[{**old_features[r['qid']],'qid':r['qid'],'difficulty':r['difficulty']} for r in assessed]
        old_data,old_diag,old_feasible=fit_route_probabilities(samples,train)
        old_model=RouteProbabilityModel.from_dict(old_data)
        old_oof={r['qid']:r['probability'] for r in old_diag['observations']}
        targets={r['qid']:repairable(r,obs[r['qid']]) for r in assessed}
        _inner_groups,inner_folds=fold_assignments(assessed)
        utility_oof={}
        for inner in range(3):
            fit_ids=[r['qid'] for r in assessed if inner_folds[r['qid']]!=inner]
            head=fit_head(fit_ids,vectors,targets)
            for r in assessed:
                if inner_folds[r['qid']]==inner:utility_oof[r['qid']]=head.probability(vectors[r['qid']])
        head=fit_head([r['qid'] for r in assessed],vectors,targets)
        actual={r['qid']:head.probability(vectors[r['qid']]) for r in assessed}
        baseline_metrics=summarize(train,base)
        trials=[]
        for threshold in THRESHOLDS:
            inner_selected={r['qid']:((old_oof[r['qid']] is not None and old_oof[r['qid']]>=old_model.threshold)
                or (utility_oof[r['qid']] is not None and utility_oof[r['qid']]>=threshold)) for r in assessed}
            fitted_selected={r['qid']:(old_model.selects(old_features[r['qid']])
                or (actual[r['qid']] is not None and actual[r['qid']]>=threshold)) for r in assessed}
            inner_metrics=metrics_from_selection(assessed,[inner_selected[r['qid']] for r in assessed])
            fitted_metrics=metrics_from_selection(assessed,[fitted_selected[r['qid']] for r in assessed])
            if not route_ok(inner_metrics) or not route_ok(fitted_metrics):continue
            for weight in WEIGHTS:
                proposed={r['qid']:proposals[weight][r['qid']] if inner_selected.get(r['qid'],False) else base[r['qid']] for r in train}
                quality=summarize(train,proposed)
                if (quality['recall5']>=.95 and quality['negative_fpr']<=.01
                        and quality['all_gold_coverage5']>=baseline_metrics['all_gold_coverage5']):
                    trials.append({'threshold':threshold,'weight':weight,'inner_route':inner_metrics,
                        'fitted_route':fitted_metrics,'inner_selected_ranking':quality})
        chosen=max(trials,key=lambda t:(t['inner_selected_ranking']['mrr'],t['inner_selected_ranking']['ndcg5'],
            -t['inner_route']['coverage'],-t['weight'],t['threshold'])) if trials else None
        threshold=chosen['threshold'] if chosen else 1.;weight=chosen['weight'] if chosen else 0.
        for row in valid:
            qid=row['qid'];probability=head.probability(vectors[qid]) if qid in eligible_ids else None
            selected=qid in eligible_ids and (old_model.selects(old_features[qid])
                or (probability is not None and probability>=threshold))
            selections[qid]=selected;outputs[qid]=proposals[weight][qid] if selected else base[qid]
        valid_assessed=[r for r in valid if r['qid'] in eligible_ids and r['difficulty'] in ('hard','easy')]
        reports.append({'fold':fold,'training_groups':sorted({groups[r['qid']] for r in train}),
            'validation_groups':sorted({groups[r['qid']] for r in valid}),
            'hard_model':old_data,'utility_model':head.to_dict(),'original_hard_route_train_feasible':old_feasible,
            'selected':chosen,'feasible_trial_count':len(trials),'validation_quality':summarize(valid,outputs),
            'validation_route':metrics_from_selection(valid_assessed,[selections[r['qid']] for r in valid_assessed])})
    quality={}
    cohorts={'all_dev':rows,'consumed_parent_dev':[r for r in rows if r['qid'] in inherited],
             'new_source_dev':[r for r in rows if r['qid'] not in inherited]}
    for name,part in cohorts.items():
        b,p=summarize(part,base),summarize(part,outputs)
        quality[name]={'records':len(part),'baseline':b,'reranked':p,
            'relative_uplift':{k:p[k]/b[k]-1 for k in ('mrr','ndcg5')},
            'paired_bootstrap':group_bootstrap(part,base,outputs,groups)}
    assessed=[r for r in rows if r['qid'] in eligible_ids and r['difficulty'] in ('hard','easy')]
    return {'quality_by_cohort':quality,'folds':reports,
        'route_outer_oof':metrics_from_selection(assessed,[selections[r['qid']] for r in assessed])},[
        {'qid':r['qid'],'group':groups[r['qid']],'fold':folds[r['qid']],
         'route_selected':selections[r['qid']],'baseline':base[r['qid']],'results':outputs[r['qid']]} for r in rows]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('dev','scores','score-report','inheritance','output-dir'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if args.output_dir.exists() or not args.output_dir.resolve().is_relative_to(ROOT/'.release/reranker/studies'):
        raise ValueError('use a new isolated dev study')
    report=read_json(args.score_report)
    if (report['raw_scores_sha256']!=sha256(args.scores) or report['dev_sha256']!=sha256(args.dev)
            or report['test_used'] or report['holdout_used'] or report['release_eligible'] or not report['source_stable']):
        raise ValueError('scores must be source-bound dev-only')
    with gzip.open(resolve_artifact(args.scores),'rt',encoding='utf8') as stream:raw=json.load(stream)
    if raw['source_identity_before']!=raw['source_identity_after']:raise ValueError('unstable measured score source')
    inherited={qid for parent in read_json(args.inheritance)['parents'] for qid in parent['qids']}
    before=source_identity(ROOT);result,decisions=analyze(rows_at(args.dev),raw['observations'],inherited)
    if source_identity(ROOT)!=before:raise ValueError('source changed during nested study')
    args.output_dir.mkdir(parents=True)
    path=args.output_dir/'nested_oof_decisions.json.gz'
    with gzip.open(path,'xt',encoding='utf8') as stream:json.dump(decisions,stream,ensure_ascii=False,allow_nan=False)
    result.update({'status':'MEASURED_UTILITY_ROUTE_DEV_REPLAY_NOT_RELEASE','release_eligible':False,
        'test_used':False,'holdout_used':False,'new_model_calls':0,'llm_called':False,'source_identity':before,
        'scores_path':args.scores.as_posix(),'scores_sha256':sha256(args.scores),
        'score_report_sha256':sha256(args.score_report),'dev_sha256':sha256(args.dev),
        'inheritance_sha256':sha256(args.inheritance),'model_identity':raw['model_identity'],
        'decisions_sha256':sha256(path),'runner_sha256':sha256(Path(__file__)),
        'protocol':'Three connected-group outer folds; three inner utility folds; separate original hard-route OOF; train-inner-OOF threshold/cap20/weight selection; no outer validation enters fitting or selection.',
        'training_uses_gold':True,'inference_uses_gold_qid_difficulty_or_ce_logits':False,
        'limitations':['Research policy not activated in serving; reused measured logits do not establish latency/resource acceptance.',
            'Utility labels are annotated-gold ranking preferences, not exhaustive semantic nonrelevance labels.',
            'A fold with no joint feasible trial uses baseline ranking; no failed fold is omitted.']})
    write_json(args.output_dir/'nested_dev_report.json',result)
    print(json.dumps({'quality':result['quality_by_cohort'],'route':result['route_outer_oof']}))


if __name__=='__main__':main()
