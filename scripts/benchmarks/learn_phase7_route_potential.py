"""Select a retrieval-only router before a new ranker is fitted.

Three outer groups and three inner groups separate fitting, route selection,
and validation. Oracle ranking is an explicitly gold-aware diagnostic only.
"""
import argparse
import gzip
import json
from pathlib import Path

from campusai.retrieval.route_probability import RouteProbabilityModel,route_observations
from campusai.retrieval.route_utility import utility_features
from evaluation.benchmarks.dev_inheritance import rows_at
from evaluation.common.artifact_store import resolve_artifact
from evaluation.common.release_artifacts import read_json,write_json,sha256,source_identity
from evaluation.reranker.calibrate_route_probabilities import fit_route_probabilities,metrics_from_selection
from evaluation.reranker.optimize_reranker_dev import summarize
from evaluation.retrieval.compare_retrieval_quality import query_metrics
from scripts.benchmarks.analyze_phase7_ranking_replay import fold_assignments,eligible,baseline_covered,ordered_pool
from scripts.benchmarks.learn_phase7_utility_route import repairable,route_ok,THRESHOLDS,CAP
from scripts.benchmarks.phase7_route_forest import fit_forest as fit_head

ROOT=Path(__file__).resolve().parents[2]


def analyze(rows,observations):
    obs={o['qid']:o for o in observations}
    if len(obs)!=len(observations) or set(obs)!={r['qid'] for r in rows}:raise ValueError('unpaired dev')
    groups,folds=fold_assignments(rows);base={qid:o['baseline'] for qid,o in obs.items()}
    ids={qid for qid,o in obs.items() if eligible(o)}
    features={qid:utility_features(obs[qid]['actual_request']['query'],obs[qid]['baseline'],obs[qid]['pool']) for qid in ids}
    old_features={qid:route_observations(o['actual_request']['query'],o['pool']) for qid,o in obs.items()}
    oracle={};gain={}
    for row in rows:
        qid=row['qid'];o=obs[qid];gold={g['chunk_id'] for g in row['gold_evidence']}
        proposal=sorted(ordered_pool(o,'baseline_priority')[:CAP],key=lambda r:r['chunk_id'] not in gold)[:5] if baseline_covered(o) else base[qid]
        oracle[qid]=proposal
        b,p=query_metrics(row,base[qid]),query_metrics(row,proposal)
        gain[qid]=max(0.,p['mrr']-b['mrr'])+max(0.,p['ndcg5']-b['ndcg5'])
    selections,reports={},[]
    for fold in range(3):
        train=[r for r in rows if folds[r['qid']]!=fold];valid=[r for r in rows if folds[r['qid']]==fold]
        assessed=[r for r in train if r['qid'] in ids and r['difficulty'] in ('hard','easy')]
        risk_rows=[r for r in train if r['qid'] in ids]
        old_data,diagnostics,old_feasible=fit_route_probabilities([
            {**old_features[r['qid']],'qid':r['qid'],'difficulty':r['difficulty']} for r in assessed],train)
        old=RouteProbabilityModel.from_dict(old_data)
        old_oof={r['qid']:r['probability'] for r in diagnostics['observations']}
        hard_targets={r['qid']:r['difficulty']=='hard' for r in assessed}
        risk_targets={r['qid']:repairable(r,obs[r['qid']]) for r in risk_rows}
        # All training rows define connectivity, including intermediate medium
        # and negative records. Repairability is valid for medium difficulty;
        # only the separate hard/easy head needs a binary difficulty label.
        _,inner=fold_assignments(train)
        hard_oof,risk_oof={},{}
        for inner_fold in range(3):
            fit_ids=[r['qid'] for r in assessed if inner[r['qid']]!=inner_fold]
            risk_fit_ids=[r['qid'] for r in risk_rows if inner[r['qid']]!=inner_fold]
            hard_model=fit_head(fit_ids,features,hard_targets);risk_model=fit_head(risk_fit_ids,features,risk_targets)
            for r in assessed:
                qid=r['qid']
                if inner[qid]==inner_fold:
                    hard_oof[qid]=hard_model.probability(features[qid]);risk_oof[qid]=risk_model.probability(features[qid])
        hard_model=fit_head([r['qid'] for r in assessed],features,hard_targets)
        risk_model=fit_head([r['qid'] for r in risk_rows],features,risk_targets)
        hard_actual={r['qid']:hard_model.probability(features[r['qid']]) for r in assessed}
        risk_actual={r['qid']:risk_model.probability(features[r['qid']]) for r in assessed}
        def selected(qid,kind,hard_threshold,risk_threshold,oof):
            legacy=old_oof.get(qid) if oof else old.probability(old_features[qid])
            h=(old_oof.get(qid) if oof else old.probability(old_features[qid])) if kind=='legacy' else (hard_oof.get(qid) if oof else hard_actual[qid])
            risk=risk_oof.get(qid) if oof else risk_actual[qid]
            threshold=old.threshold if kind=='legacy' else hard_threshold
            return ((legacy is not None and legacy>=old.threshold)
                or (h is not None and h>=threshold) or (risk is not None and risk>=risk_threshold))
        trials=[]
        for kind,hard_threshold in [('legacy',old.threshold)]+[('augmented',t) for t in THRESHOLDS]:
            for risk_threshold in THRESHOLDS:
                inner_selections=[selected(r['qid'],kind,hard_threshold,risk_threshold,True) for r in assessed]
                actual_selections=[selected(r['qid'],kind,hard_threshold,risk_threshold,False) for r in assessed]
                inner_metrics=metrics_from_selection(assessed,inner_selections);actual_metrics=metrics_from_selection(assessed,actual_selections)
                if not route_ok(inner_metrics) or not route_ok(actual_metrics):continue
                potential=sum(gain[r['qid']] for r,s in zip(assessed,inner_selections) if s)
                trials.append({'hard_kind':kind,'hard_threshold':hard_threshold,'risk_threshold':risk_threshold,
                    'train_inner_oof_potential_gain':potential,'train_inner_oof_route':inner_metrics,'train_fitted_route':actual_metrics})
        chosen=max(trials,key=lambda t:(t['train_inner_oof_potential_gain'],-t['train_inner_oof_route']['coverage'],t['risk_threshold'],t['hard_threshold'])) if trials else None
        kind=chosen['hard_kind'] if chosen else 'legacy';ht=chosen['hard_threshold'] if chosen else old.threshold;rt=chosen['risk_threshold'] if chosen else 1.
        for row in valid:
            qid=row['qid']
            if qid not in ids:selections[qid]=False;continue
            h=old.probability(old_features[qid]) if kind=='legacy' else hard_model.probability(features[qid])
            risk=risk_model.probability(features[qid]);threshold=old.threshold if kind=='legacy' else ht
            selections[qid]=(old.selects(old_features[qid])
                or (h is not None and h>=threshold) or (risk is not None and risk>=rt))
        validation=[r for r in valid if r['qid'] in ids and r['difficulty'] in ('hard','easy')]
        reports.append({'fold':fold,'training_groups':sorted({groups[r['qid']] for r in train}),
            'validation_groups':sorted({groups[r['qid']] for r in valid}),
            'legacy_hard_model':old_data,'augmented_hard_model':hard_model.to_dict(),'risk_model':risk_model.to_dict(),
            'risk_training_qids':[r['qid'] for r in risk_rows],
            'hard_training_qids':[r['qid'] for r in assessed],
            'original_route_fit_feasible':old_feasible,'selected':chosen,'feasible_route_trials':len(trials),
            'validation_route':metrics_from_selection(validation,[selections[r['qid']] for r in validation])})
    assessed=[r for r in rows if r['qid'] in ids and r['difficulty'] in ('hard','easy')]
    # Gold-aware output is isolated and never passed to serving/acceptance.
    ideal={qid:oracle[qid] if selections[qid] else values for qid,values in base.items()}
    b,p=summarize(rows,base),summarize(rows,ideal)
    return {'folds':reports,'route_outer_oof':metrics_from_selection(assessed,[selections[r['qid']] for r in assessed]),
        'baseline':b,'gold_aware_rank_potential_only':p,'relative_gold_aware_potential':{k:p[k]/b[k]-1 for k in ('mrr','ndcg5')},
        'route_selections':[{'qid':r['qid'],'group':groups[r['qid']],'fold':folds[r['qid']],'selected':selections[r['qid']]} for r in rows]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('dev','scores','score-report','output-dir'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if args.output_dir.exists() or not args.output_dir.resolve().is_relative_to(ROOT/'.release/reranker/studies'):raise ValueError('new isolated dev study required')
    report=read_json(args.score_report)
    if (report['dev_sha256']!=sha256(args.dev) or report['raw_scores_sha256']!=sha256(args.scores)
            or report['test_used'] or report['holdout_used'] or report['release_eligible'] or not report['source_stable']):raise ValueError('invalid dev score binding')
    with gzip.open(resolve_artifact(args.scores),'rt',encoding='utf8') as stream:raw=json.load(stream)
    if raw['source_identity_before']!=raw['source_identity_after']:raise ValueError('unstable ancestor source')
    before=source_identity(ROOT);result=analyze(rows_at(args.dev),raw['observations'])
    if source_identity(ROOT)!=before:raise ValueError('source changed during study')
    args.output_dir.mkdir(parents=True)
    result.update({'status':'NESTED_OBSERVABLE_ROUTE_WITH_GOLD_AWARE_POTENTIAL_DIAGNOSTIC',
        'release_eligible':False,'actual_rank_uplift_claim':False,'test_used':False,'holdout_used':False,
        'model_called':False,'llm_called':False,'source_identity':before,'runner_sha256':sha256(Path(__file__)),
        'dev_sha256':sha256(args.dev),'scores_sha256':sha256(args.scores),'score_report_sha256':sha256(args.score_report),
        'protocol':'Three connected-group outer folds; three inner groups defined by all training rows; repairability trains on all eligible difficulties, hard head only on hard/easy; preserve legacy hard selection with OR; both inner-OOF and fitted route constraints; select route on train-inner-OOF potential before ranker fitting.',
        'limitations':['Oracle rank metrics are potential only, never actual reranker output or gate evidence.','Training uses annotated gold; inference features exclude gold/qid/difficulty/CE logits.','No policy activated in serving.']})
    write_json(args.output_dir/'route_potential_report.json',result)
    print(json.dumps({k:result[k] for k in ('route_outer_oof','relative_gold_aware_potential')}))


if __name__=='__main__':main()
