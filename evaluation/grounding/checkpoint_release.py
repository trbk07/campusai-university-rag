"""Internal Phase5 acceptance of physically recomputed real HTTP checkpoints.

This is separate from public release and never labels reused responses fresh.
The frozen producer executes offline; missing inputs cannot become negatives.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from campusai.rag.calibration import IsotonicCalibrator, load_calibration_artifact
from campusai.rag.schemas import validate_response, validate_release_response
from evaluation.common.release_artifacts import source_identity, verify_index_files
from evaluation.grounding.calibrate_confidence import _score, _label, evaluate_calibrator, risk_at_coverage
from evaluation.grounding.checkpoint import PROTOCOL, digest
from evaluation.grounding.collect_native_predictions import inference_request
from evaluation.grounding.grounding_metrics import evaluate_grounding
from evaluation.grounding.native_artifacts import load_native_run
from evaluation.grounding.repair_benchmark import load_rows
from evaluation.grounding.scoring_provenance import bind_scoring_source, source_tree_dirty, verify_scoring_source

FILES=frozenset({'source-pool.json','predictions.jsonl','pending.jsonl'})


def zero(value):
    return type(value) is int and value==0


def load_checkpoint(directory: Path):
    directory=directory.resolve()
    run=json.loads((directory/'run.json').read_text(encoding='utf8'))
    if (run.get('protocol')!=PROTOCOL or run.get('generation_kind')!='native_checkpoint'
            or set(run.get('artifacts',{}))!=FILES
            or any(digest(directory/name)!=run['artifacts'][name] for name in FILES)
            or not zero(run.get('fresh_provider_posts')) or not zero(run.get('fresh_model_outputs'))
            or not zero(run.get('official_predictions'))):
        raise ValueError('Checkpoint protocol, artifacts or measured counters invalid')
    predictions=load_rows(directory/'predictions.jsonl');pending=load_rows(directory/'pending.jsonl')
    ids=[row['id'] for row in predictions];missing=[row['id'] for row in pending]
    if (len(ids)!=len(set(ids)) or len(missing)!=len(set(missing)) or set(ids)&set(missing)
            or type(run.get('pipeline_predictions')) is not int or type(run.get('pending')) is not int
            or run.get('pipeline_predictions')!=len(ids) or run.get('pending')!=len(missing)
            or any(row.get('protocol')!=PROTOCOL or not zero(row.get('fresh_provider_posts'))
                   or not zero(row.get('fresh_model_outputs')) for row in predictions)):
        raise ValueError('Checkpoint population or counters invalid')
    return run,predictions,pending


def prediction_rows(benchmark: Path,predictions: list[dict]):
    gold={row['id']:row for row in load_rows(benchmark)}
    rows=[];seen=set()
    for prediction in predictions:
        identifier=prediction['id']
        if identifier in seen or identifier not in gold:
            raise ValueError('Checkpoint prediction population invalid')
        seen.add(identifier)
        if prediction['request']!=inference_request(gold[identifier]):
            raise ValueError('Checkpoint request differs from user-input-only projection')
        public=prediction['public_response'];internal=prediction['internal_response']
        claims=[c for c in internal['claims'] if c['claim_id'] in {v['claim_id'] for v in public['claims']}]
        rows.append({**deepcopy(gold[identifier]),**internal,'answer':public['answer'],
            'abstained':public['abstained'],'claims':claims,'citations':public['citations'],
            'abstention_reason':public.get('abstention_reason'),'public_response':public,
            'internal_trace':internal,'native_failure':None,
            'schema_valid':validate_release_response(public)[0] and validate_response(internal,include_internal=True)[0],
            'citation_valid':validate_release_response(public)[0],
            'retrieved_pages':sorted({f"{x['doc_id']}:{x['page']}" for x in prediction['retrieved_evidence']})})
    return rows


def output_counts(predictions,pool):
    unique={(use['origin']['path'],use['origin']['capture_index'])
            for p in predictions for use in p['capture_uses']}
    return {'pipeline_outcomes':len(predictions),
            'reused_gemini_response_uses':sum(len(p['capture_uses']) for p in predictions),
            'unique_original_responses':len(unique),'fresh_provider_posts_in_reprocessing':0,
            'source_native_runs':len(pool['runs']),
            'source_native_journal_post_starts':sum(load_native_run(Path(b['path']).parent)[0]['provider_posts']
                                                   for b in pool['runs'])}


def score_checkpoint(directory: Path,plan_path: Path,root: Path,signoff: Path):
    from evaluation.grounding.validate_grounding_release import validate
    run,predictions,pending=load_checkpoint(directory)
    benchmark=Path(run['benchmark_path']);rows=prediction_rows(benchmark,predictions)
    calibration=Path(run['calibration_artifact_path'])
    calibrator,calibration_sha=load_calibration_artifact(calibration,
        expected_sha256=run['calibration_artifact_sha256'])
    plan=json.loads(plan_path.read_text(encoding='utf8'))
    binding=bind_scoring_source(root/plan['producer_checkout'],root)
    current=source_identity(root);gold=load_rows(benchmark)
    pool=json.loads((directory/'source-pool.json').read_text(encoding='utf8'))
    report={'schema_version':2,'phase':'grounding','mode':'runtime','acceptance_scope':'phase5_acceptance',
        'benchmark':str(benchmark),'benchmark_sha256':digest(benchmark),'dataset':{'sha256':digest(benchmark)},
        'dataset_count':len(rows),'benchmark_population':len(gold),'collection_complete':not pending and len(rows)==len(gold),
        'missing_prediction_ids':sorted({r['id'] for r in gold}-{r['id'] for r in rows}),
        'failed_prediction_ids':[],'policy_version':'grounding-v1','source_identity':current,
        'inference_source_identity':run['source_identity'],
        'metadata':{'commit':current['commit'],'working_tree':source_tree_dirty(root),
                    'working_tree_scope':'tracked-files-and-untracked-source-v1'},
        'generation':{'kind':'native_checkpoint','protocol':PROTOCOL,'gold_seeded':False,
            'checkpoint_run_path':str((directory/'run.json').resolve()),
            'checkpoint_run_sha256':digest(directory/'run.json'),'plan_path':str(plan_path.resolve()),
            'plan_sha256':digest(plan_path),'scoring_source_binding':binding},
        'rows':rows,'metrics':evaluate_grounding(rows,allow_reviewed_source_subspan=True),
        'split_metrics':{v:evaluate_grounding([r for r in rows if r['split']==v],allow_reviewed_source_subspan=True)
                         for v in sorted({r['split'] for r in rows})},
        'category_metrics':{v:evaluate_grounding([r for r in rows if r['category']==v],allow_reviewed_source_subspan=True)
                            for v in sorted({r['category'] for r in rows})},
        'calibration':evaluate_calibrator(rows,calibrator),
        'risk_at_coverage':{str(v):risk_at_coverage(rows,calibrator,v) for v in (.8,.9)},
        'risk_population':'holdout','calibration_artifact_path':str(calibration),
        'calibration_artifact_version':calibrator.version,'calibration_artifact_sha256':calibration_sha,
        'calibration_benchmark_sha256':json.loads(calibration.read_text(encoding='utf8'))['benchmark_sha256'],
        'calibration_population':{v:{'count':len(part),'positive':sum(_label(r) for r in part),
            'negative':sum(not _label(r) for r in part)} for v in ('dev','test','holdout')
            if (part:=[r for r in rows if r['split']==v])},
        'annotation_signoff':json.loads(signoff.read_text(encoding='utf8')),
        'annotation_signoff_path':str(signoff),'annotation_signoff_sha256':digest(signoff),
        'checkpoint_output_counts':output_counts(predictions,pool)}
    report['release_errors']=validate(report,root=root,acceptance_scope='phase5_acceptance')
    report['release_status']='BLOCKED' if report['release_errors'] else 'PASS'
    return report


def verify_checkpoint_report(report,root):
    """Recompute physical outputs in the immutable producer, with HTTP disabled."""
    root=root.resolve();generation=report['generation']
    def path(value,*,directory=False):
        item=(root/value).resolve()
        if not item.is_relative_to(root) or not (item.is_dir() if directory else item.is_file()):
            raise ValueError('Checkpoint input path invalid')
        return item
    errors=[]
    if source_tree_dirty(root):errors.append('working_tree_dirty')
    if report['source_identity']!=source_identity(root):errors.append('current_source_identity_mismatch')
    if report['metadata']['commit']!=report['source_identity']['commit']:
        errors.append('commit_fingerprint_mismatch')
    producer=verify_scoring_source(generation['scoring_source_binding'],root)
    run_path=path(generation['checkpoint_run_path']);plan_path=path(generation['plan_path'])
    if digest(run_path)!=generation['checkpoint_run_sha256'] or digest(plan_path)!=generation['plan_sha256']:
        raise ValueError('Checkpoint run or plan changed')
    run,predictions,pending=load_checkpoint(run_path.parent)
    plan=json.loads(plan_path.read_text(encoding='utf8'))
    if pending:return errors+['checkpoint_incomplete']
    if (report.get('collection_complete') is not True or report.get('missing_prediction_ids')!=[]
            or report.get('failed_prediction_ids')!=[]):
        raise ValueError('Checkpoint collection completeness declaration invalid')
    if (run['source_identity']!=producer or report['inference_source_identity']!=producer
            or plan['source_identity']!=producer or plan.get('protocol')!=PROTOCOL):
        raise ValueError('Checkpoint producer binding invalid')
    benchmark=path(run['benchmark_path']);calibration=path(run['calibration_artifact_path'])
    for name in ('benchmark','config','calibration_artifact'):
        original=path(run[name+'_path'])
        if digest(original)!=plan['file_sha256'][name]:raise ValueError('Checkpoint frozen input changed')
    if digest(path(run['config_path']))!=run['config_sha256']:
        raise ValueError('Checkpoint configuration binding invalid')
    if digest(benchmark)!=run['benchmark_sha256'] or digest(benchmark)!=report['benchmark_sha256']:
        raise ValueError('Checkpoint benchmark changed')
    index=path(run['index_path'],directory=True)
    if digest(index/'manifest.json')!=run['index_manifest_sha256'] or not verify_index_files(index):
        raise ValueError('Checkpoint physical index changed')
    signoff=path(report['annotation_signoff_path'])
    if (digest(signoff)!=report['annotation_signoff_sha256']
            or json.loads(signoff.read_text(encoding='utf8'))!=report['annotation_signoff']):
        raise ValueError('Checkpoint annotation signoff changed')
    if prediction_rows(benchmark,predictions)!=report['rows']:
        raise ValueError('Checkpoint scored rows differ from physical predictions')
    calibrator,calibration_sha=load_calibration_artifact(calibration,
        expected_sha256=report['calibration_artifact_sha256'])
    dev=[r for r in report['rows'] if r['split']=='dev']
    fitted=IsotonicCalibrator.fit([_score(r) for r in dev],[_label(r) for r in dev])
    if fitted.to_dict()!=calibrator.to_dict() or calibration_sha!=run['calibration_artifact_sha256']:
        raise ValueError('Checkpoint calibration is not the unchanged dev-only fit')
    population={v:{'count':len(part),'positive':sum(_label(r) for r in part),
        'negative':sum(not _label(r) for r in part)} for v in ('dev','test','holdout')
        if (part:=[r for r in report['rows'] if r['split']==v])}
    if (population!=report['calibration_population']
            or path(report['calibration_artifact_path'])!=calibration
            or report['calibration_artifact_version']!=calibrator.version):
        raise ValueError('Checkpoint calibration metadata changed')
    pin_path=path(plan['original_calibration_pin_path'])
    if digest(pin_path)!=plan['original_calibration_pin_sha256']:raise ValueError('Checkpoint pin changed')
    pin=json.loads(pin_path.read_text(encoding='utf8'))
    locked=datetime.fromisoformat(pin['locked_at']);started=datetime.fromisoformat(plan['created_at'])
    ended=datetime.fromisoformat(run['completed_at'])
    if (not all(v.tzinfo for v in (locked,started,ended)) or not locked<=started<ended
            or pin['artifact_sha256']!=calibration_sha or pin['file_sha256']!=digest(calibration)
            or pin['fit_split']!='dev' or pin['fit_count']!=len(dev)):
        raise ValueError('Checkpoint dev pin protocol invalid')
    if evaluate_calibrator(report['rows'],calibrator)!=report['calibration']:
        raise ValueError('Checkpoint calibration metrics changed')
    if {str(v):risk_at_coverage(report['rows'],calibrator,v) for v in (.8,.9)}!=report['risk_at_coverage']:
        raise ValueError('Checkpoint risk metrics changed')
    pool=json.loads((run_path.parent/'source-pool.json').read_text(encoding='utf8'))
    for binding in pool['runs']:
        if digest(path(binding['path']))!=binding['sha256']:raise ValueError('Checkpoint original run changed')
    if output_counts(predictions,pool)!=report['checkpoint_output_counts']:
        raise ValueError('Checkpoint reuse counters changed')
    producer_root=path(plan['producer_checkout'],directory=True)
    config=path(run['config_path']);store=path(plan['store_path'],directory=True)
    campaigns=[path(value,directory=True) for value in plan['native_campaigns']]
    roots=[path(value,directory=True) for value in plan['source_roots']]
    dev_score=path(plan['dev_score_path'])
    if digest(dev_score)!=plan['dev_score_sha256']:raise ValueError('Checkpoint dev anchor changed')
    temporary_root=root/'.tmp';temporary_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='phase5-physical-verify-',dir=temporary_root) as temporary:
        assert Path(temporary).resolve().is_relative_to(temporary_root.resolve())
        output=Path(temporary)/'recomputed'
        command=[sys.executable,str(producer_root/'evaluation/grounding/checkpoint.py'),
            '--benchmark',str(benchmark),'--config',str(config),'--index',str(index),
            '--store',str(store),'--dev-score',str(dev_score),'--calibration',str(calibration),
            '--output',str(output)]
        for value in campaigns:command.extend(['--native-campaign',str(value)])
        for value in roots:command.extend(['--source-root',str(value)])
        environment={**os.environ,'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1',
                     'PYTHONPATH':os.pathsep.join([str(producer_root/'src'),str(producer_root)])}
        try:
            result=subprocess.run(command,cwd=root,env=environment,stdout=subprocess.DEVNULL,
                                  stderr=subprocess.PIPE,timeout=1200)
        except subprocess.TimeoutExpired as error:
            raise ValueError('Checkpoint physical recomputation timed out') from error
        if result.returncode:raise ValueError('Checkpoint offline physical recomputation failed')
        reproduced,actual,missing=load_checkpoint(output)
        if (missing or actual!=predictions or reproduced['source_identity']!=producer
                or json.loads((output/'source-pool.json').read_text(encoding='utf8'))!=pool):
            raise ValueError('Checkpoint physical recomputation differs from declared outputs')
    return errors


def main():
    import argparse
    from evaluation.common.release_artifacts import write_json
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint-dir',type=Path,required=True)
    parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--annotation-signoff',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report=score_checkpoint(args.checkpoint_dir,args.plan,Path.cwd(),args.annotation_signoff)
    write_json(args.output,report)
    print(json.dumps({'release_status':report['release_status'],'errors':report['release_errors'],
                      'scope':report['acceptance_scope'],'count':report['dataset_count']}))
    raise SystemExit(0 if not report['release_errors'] else 1)


if __name__=='__main__':main()
