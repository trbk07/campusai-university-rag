"""Nested connected-group dev learning of query/candidate rerank fusion.

Exact measured BGE logits are reused: no new model/LLM/heldout calls or serving
latency claim. Ridge pairwise weights are fitted on training groups only.
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

import numpy as np

from campusai.retrieval.learned_rank_features import features, FEATURE_NAMES, VERSION
from campusai.retrieval.route_probability import RouteProbabilityModel, route_observations
from evaluation.benchmarks.dev_inheritance import rows_at
from evaluation.common.artifact_store import resolve_artifact
from evaluation.common.release_artifacts import read_json, sha256, source_identity, write_json
from evaluation.reranker.calibrate_route_probabilities import fit_route_probabilities, metrics_from_selection
from evaluation.reranker.optimize_reranker_dev import summarize
from scripts.benchmarks.analyze_phase7_ranking_replay import (ordered_pool, eligible, baseline_covered,
                                                           fold_assignments, group_bootstrap)

ROOT = Path(__file__).resolve().parents[2]
REGULARIZATIONS = (.001, .01, .1, 1.)
BLENDS = (.25, .5, 1.)
CAP = 20


def fit_pairwise(rows, vectors, pools, regularization):
    covariance = np.zeros((len(FEATURE_NAMES), len(FEATURE_NAMES)))
    target = np.zeros(len(FEATURE_NAMES))
    count = 0
    for row in rows:
        qid = row['qid']
        if not row['answerable'] or qid not in vectors:
            continue
        gold = {(x['doc_id'], x['chunk_id']) for x in row['gold_evidence']}
        positive = [i for i,x in enumerate(pools[qid]) if (x['doc_id'],x['chunk_id']) in gold]
        negative = [i for i,x in enumerate(pools[qid]) if (x['doc_id'],x['chunk_id']) not in gold]
        if not positive or not negative:
            continue
        weight = 1. / (len(positive) * len(negative))
        for p in positive:
            for n in negative:
                difference = vectors[qid][p] - vectors[qid][n]
                covariance += weight * np.outer(difference, difference)
                target += weight * difference
                count += 1
    if count == 0:
        raise ValueError('no training preference pairs')
    return np.linalg.solve(covariance + regularization * np.eye(len(FEATURE_NAMES)), target).tolist()


def propose(qid, weights, blend, vectors, pools, baseline):
    learned = vectors[qid] @ np.asarray(weights)
    # A baseline score is monotonic with the original baseline position. A
    # candidate outside baseline carries no manufactured relevance label.
    prior = np.asarray([vectors[qid][i][2] for i in range(len(pools[qid]))])
    values = blend * learned + (1. - blend) * prior
    order = sorted(range(len(values)), key=lambda i: (-values[i], i))
    return [pools[qid][i] for i in order[:5]]


def analyze(rows, observations, inherited):
    groups, folds = fold_assignments(rows)
    obs = {x['qid']:x for x in observations}
    if len(obs) != len(observations) or set(obs) != {x['qid'] for x in rows}:
        raise ValueError('exact unique paired dev required')
    base = {qid:x['baseline'] for qid,x in obs.items()}
    pools, vectors = {}, {}
    for qid,x in obs.items():
        if not eligible(x) or not baseline_covered(x):
            continue
        pools[qid] = ordered_pool(x, 'baseline_priority')[:CAP]
        positions = {p['chunk_id']:i for i,p in enumerate(x['baseline'],1)}
        vectors[qid] = np.asarray([features(x['actual_request']['query'], p,
            x['scores'][p['chunk_id']], positions.get(p['chunk_id'],0), i)
            for i,p in enumerate(pools[qid],1)])
    route_features = {qid:route_observations(x['actual_request']['query'],[]) for qid,x in obs.items()}
    oof, selections, reports = {}, {}, []
    for fold in range(3):
        train = [r for r in rows if folds[r['qid']] != fold]
        valid = [r for r in rows if folds[r['qid']] == fold]
        samples = [{**route_features[r['qid']], 'qid':r['qid'], 'difficulty':r['difficulty']}
            for r in train if r['qid'] in pools and r['difficulty'] in ('hard','easy')]
        data, diagnostic, feasible = fit_route_probabilities(samples, train)
        model = RouteProbabilityModel.from_dict(data)
        selected = {qid:qid in pools and model.selects(route_features[qid]) for qid in obs}
        _, inner = fold_assignments(train, 2)
        trials = []
        train_baseline = summarize(train, base)
        for penalty in REGULARIZATIONS:
            inner_weights = {part:fit_pairwise([r for r in train if inner[r['qid']] != part],
                                              vectors, pools, penalty) for part in (0,1)}
            for blend in BLENDS:
                outputs = {r['qid']:propose(r['qid'],inner_weights[inner[r['qid']]],blend,vectors,pools,base)
                    if selected[r['qid']] else base[r['qid']] for r in train}
                metric = summarize(train, outputs)
                accepted = (metric['recall5'] >= train_baseline['recall5']
                    and metric['negative_fpr'] <= .01 and metric['all_gold_coverage5'] >= train_baseline['all_gold_coverage5'])
                trials.append({'regularization':penalty,'blend':blend,'inner_oof':metric,'feasible':accepted})
        choices = [x for x in trials if x['feasible']]
        chosen = max(choices, key=lambda x:(x['inner_oof']['mrr'],x['inner_oof']['ndcg5'],-x['blend'])) if choices else None
        weights = fit_pairwise(train,vectors,pools,chosen['regularization']) if chosen else None
        for r in valid:
            qid=r['qid'];selections[qid]=selected[qid]
            oof[qid]=propose(qid,weights,chosen['blend'],vectors,pools,base) if selected[qid] and chosen else base[qid]
        assessed=[r for r in valid if r['qid'] in pools and r['difficulty'] in ('hard','easy')]
        reports.append({'fold':fold,'training_groups':sorted({groups[r['qid']] for r in train}),
            'validation_groups':sorted({groups[r['qid']] for r in valid}), 'route_model':data,
            'route_feasible':feasible,'route_inner_oof':diagnostic['out_of_fold_metrics'],
            'selected':chosen,'feature_weights':weights,'trials':trials,
            'validation_metrics':summarize(valid,oof),
            'route_validation':metrics_from_selection(assessed,[selections[r['qid']] for r in assessed])})
    cohorts={'all_dev':rows,'consumed_parent_dev':[r for r in rows if r['qid'] in inherited],
             'new_source_dev':[r for r in rows if r['qid'] not in inherited]}
    quality={}
    for name,part in cohorts.items():
        b,r=summarize(part,base),summarize(part,oof)
        quality[name]={'records':len(part),'groups':len({groups[x['qid']] for x in part}),
            'baseline':b,'reranked':r,'relative_uplift':{k:r[k]/b[k]-1 for k in ('mrr','ndcg5')},
            'paired_bootstrap':group_bootstrap(part,base,oof,groups)}
    return {'feature_version':VERSION,'feature_names':FEATURE_NAMES,'cap':CAP,'folds':reports,
        'quality_by_cohort':quality,'selection_protocol':'Three connected-group outer folds; two inner ranking folds; all selection on outer training groups only.',
        'ranking_model_training_uses_gold':True,'ranking_inference_uses_gold_or_qid_or_difficulty':False},[
        {'qid':r['qid'],'group':groups[r['qid']],'fold':folds[r['qid']],
         'route_selected':selections[r['qid']],'baseline':base[r['qid']],'results':oof[r['qid']]} for r in rows]


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
        raise ValueError('score report is not source-bound dev-only')
    with gzip.open(resolve_artifact(args.scores),'rt',encoding='utf8') as stream:raw=json.load(stream)
    if raw['source_identity_before']!=raw['source_identity_after']:
        raise ValueError('measured score source changed')
    inherited={qid for p in read_json(args.inheritance)['parents'] for qid in p['qids']}
    before=source_identity(ROOT)
    result,decisions=analyze(rows_at(args.dev),raw['observations'],inherited)
    if before!=source_identity(ROOT):raise ValueError('source changed during learning')
    args.output_dir.mkdir(parents=True)
    path=args.output_dir/'nested_oof_decisions.json.gz'
    with gzip.open(path,'xt',encoding='utf8') as stream:json.dump(decisions,stream,ensure_ascii=False,allow_nan=False)
    result.update({'status':'NESTED_LEARNED_DEV_FUSION_NOT_RELEASE','source_identity':before,
        'release_eligible':False,'test_used':False,'holdout_used':False,'new_model_calls':0,
        'scores_path':args.scores.as_posix(),'scores_sha256':sha256(args.scores),
        'score_report_sha256':sha256(args.score_report),'dev_sha256':sha256(args.dev),
        'inheritance_sha256':sha256(args.inheritance),'model_identity':raw['model_identity'],
        'decisions_sha256':sha256(path),'limitations':['Dev-trained fusion not activated in serving.',
        'Reused measured cap40 logits; no serving latency/resource/answer acceptance.']})
    write_json(args.output_dir/'nested_dev_report.json',result)
    print(json.dumps(result['quality_by_cohort'],ensure_ascii=False))


if __name__=='__main__':main()
