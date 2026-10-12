"""Qualify the current expanded baseline on consumed historical regressions.

This is a separate baseline-bridge experiment. The exact historical reports
and fresh successor human primary inputs remain untouched.
"""
import argparse
import gzip
import json
import os
from pathlib import Path
import sys
from datetime import datetime, timezone

from evaluation.common.release_artifacts import read_json,sha256,source_identity,write_json

ROOT=Path(__file__).resolve().parents[2]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('index-dir','calibration','output-dir'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--scope-index',type=Path)
    parser.add_argument('--dense-device',choices=('cpu','cuda','cuda:0'))
    args=parser.parse_args()
    output=args.output_dir.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'.release/reranker/studies'):
        raise ValueError('new isolated baseline-bridge study required')
    historical=read_json(ROOT/'evaluation/results/retrieval_baseline_manifest.json')
    os.environ['HF_HUB_OFFLINE']='1'
    os.environ['TRANSFORMERS_OFFLINE']='1'
    os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
    for split,digest in historical['benchmark_sha256'].items():
        if sha256(ROOT/f'data/benchmark/hybrid_retrieval_{split}.jsonl')!=digest:
            raise ValueError('historical regression inputs changed')
    calibration=read_json(args.calibration)
    if calibration['index_sha256']!=sha256(args.index_dir/'manifest.json'):
        raise ValueError('expanded calibration/index mismatch')
    from scripts.benchmarks.qualify_phase6_policy_on_successor_dev import qualification_scope
    original_calibration=read_json(ROOT/'evaluation/results/hybrid_retrieval_calibration.json')
    documents,scope=qualification_scope(args.index_dir,original_calibration,args.scope_index)
    before=source_identity(ROOT)
    output.mkdir(parents=True)
    record={'status':'REGISTERED_EXPANDED_BASELINE_REGRESSION','release_eligible':False,
        'source_identity_before':before,'runner_sha256':sha256(Path(__file__)),
        'historical_benchmark_sha256':historical['benchmark_sha256'],
        'index_sha256':sha256(args.index_dir/'manifest.json'),
        'calibration_sha256':sha256(args.calibration),'torch_threads':8,
        'dense_serving_device_override':args.dense_device,
        'started_at':datetime.now(timezone.utc).isoformat(),
        'historical_corpus_scope':scope,'documents':documents,
        'fresh_successor_test_read':False,'fresh_successor_holdout_read':False,
        'llm_called':False,'reranker_called':False,
        'purpose':'Original-source historical M0 proof is separate; current expanded baseline must retain original numeric quality floors before a versioned index bridge.'}
    write_json(output/'run_identity.json',record)
    import torch
    torch.set_num_threads(8)
    from evaluation.retrieval import evaluate_hybrid_release as evaluator
    original=evaluator._run_mode
    calls=[]
    def measured(rows,retriever,doc_ids,mode,**options):
        if set(documents)-set(doc_ids):raise ValueError('frozen request scope is outside expanded index')
        report,outputs,traces=original(rows,retriever,documents,mode,**options)
        raw=output/f'actual-mode-{len(calls)+1}-{mode}.json.gz'
        with gzip.open(raw,'xt',encoding='utf8') as stream:
            json.dump({'qids':[r['qid'] for r in rows],'documents':documents,'mode':mode,
                'outputs':{qid:[r.to_dict() for r in items] for qid,items in outputs.items()},
                'traces':traces},stream,ensure_ascii=False,allow_nan=False)
        calls.append({'mode':mode,'rows':len(rows),'path':raw.relative_to(ROOT).as_posix(),'sha256':sha256(raw)})
        print(json.dumps({'completed_modes':len(calls),'mode':mode,'rows':len(rows)}),flush=True)
        return report,outputs,traces
    evaluator._run_mode=measured
    sys.argv=['evaluate_hybrid_release','--index-dir',str(args.index_dir),
        '--calibration',str(args.calibration),'--output-dir',str(output)]
    if args.dense_device is not None:sys.argv+=['--dense-device',args.dense_device]
    try:code=evaluator.main()
    finally:
        record['source_identity_after']=source_identity(ROOT)
        record['source_stable']=before==record['source_identity_after']
        record['status']='ACTUAL_EXPANDED_BASELINE_REGRESSION_COMPLETE'
        record['finished_at']=datetime.now(timezone.utc).isoformat()
        record['actual_modes']=calls
        from campusai.retrieval.model_runtime import retrieval_runtime
        runtime=retrieval_runtime();record['runtime_loaded_models']=runtime.loaded_models()
        commits=[]
        for model in runtime._models.values():
            first=model._modules.get('0');auto=getattr(first,'auto_model',None)
            if auto is not None:commits.append(getattr(auto.config,'_commit_hash',None))
        record['actual_dense_commit_hashes']=commits
        write_json(output/'run_identity.json',record)
    if not record['source_stable']:raise ValueError('source/runtime changed during measurement')
    if not commits or set(commits)!={historical['dense_model']['revision']}:
        raise ValueError('actual dense model revision differs from historical pin')
    return code


if __name__=='__main__':raise SystemExit(main())
