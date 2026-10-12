"""Rerun consumed historical primary sets with a clean, exact Phase 6 source.

Successor primary inputs are never read. Measurement and evaluator provenance
are recorded separately; no source substitution or metric rewriting occurs.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
COMMIT = '8e3a331838fbccaa16b4dd00381b9ed4738e958f'


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
    return h.hexdigest()


def git(tree,*args):
    return subprocess.check_output(['git',*args],cwd=tree,text=True).strip()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-worktree',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--torch-threads',type=int,choices=(1,2,4,8),default=4)
    args=parser.parse_args()
    tree=args.source_worktree.resolve();output=args.output_dir.resolve()
    if (not tree.is_relative_to(ROOT/'.local_artifacts/experiment_runs')
            or not output.is_relative_to(ROOT/'.release/reranker/studies') or output.exists()):
        raise ValueError('use isolated source and a new output')
    if git(tree,'rev-parse','HEAD')!=COMMIT or git(tree,'status','--porcelain'):
        raise ValueError('exact historical source worktree must be clean')
    if any(name=='campusai' or name.startswith('campusai.') for name in sys.modules):
        raise ValueError('current CampusAI already imported')
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
    sys.dont_write_bytecode=True
    sys.path.insert(0,str(tree/'src'))
    os.chdir(ROOT)
    baseline=json.loads((ROOT/'evaluation/results/retrieval_baseline_manifest.json').read_text(encoding='utf8'))
    inputs={ROOT/'data/benchmark'/f'hybrid_retrieval_{split}.jsonl':h for split,h in baseline['benchmark_sha256'].items()}
    inputs[ROOT/'.tmp/hybrid-index/manifest.json']=baseline['index_sha256']
    inputs[ROOT/'evaluation/results/hybrid_retrieval_calibration.json']=baseline['calibration_sha256']
    for path,h in inputs.items():
        if digest(path)!=h:raise ValueError('historical input hash mismatch')
    output.mkdir(parents=True)
    binding={'source_commit':COMMIT,'source_worktree':tree.relative_to(ROOT).as_posix(),
        'source_worktree_clean_before':True,'runner_sha256':digest(Path(__file__)),
        'evaluator_sha256':digest(ROOT/'evaluation/retrieval/evaluate_hybrid_release.py'),
        'inputs':{p.relative_to(ROOT).as_posix():h for p,h in inputs.items()},
        'successor_test_read':False,'successor_holdout_read':False,'llm_called':False,'reranker_called':False,
        'torch_threads':args.torch_threads,'status':'REGISTERED_HISTORICAL_M0_REMEASUREMENT'}
    (output/'run_identity.json').write_text(json.dumps(binding,indent=2)+'\n',encoding='utf8')
    import torch
    torch.set_num_threads(args.torch_threads)
    from evaluation.retrieval import evaluate_hybrid_release as evaluator
    for name,module in list(sys.modules.items()):
        if (name=='campusai' or name.startswith('campusai.')) and getattr(module,'__file__',None):
            if not Path(module.__file__).resolve().is_relative_to(tree/'src'):
                raise ValueError('mixed current and historical retrieval source')
    original=evaluator._run_mode
    calls=[]
    def measured(rows,retriever,doc_ids,mode,**options):
        report,outputs,traces=original(rows,retriever,doc_ids,mode,**options)
        ordinal=len(calls)+1
        raw=output/f'actual-mode-{ordinal}-{mode}.json.gz'
        with gzip.open(raw,'xt',encoding='utf8') as stream:
            json.dump({'qids':[r['qid'] for r in rows],'mode':mode,
                'outputs':{qid:[r.to_dict() for r in values] for qid,values in outputs.items()},
                'traces':traces},stream,ensure_ascii=False,allow_nan=False)
        calls.append({'mode':mode,'rows':len(rows),'path':raw.relative_to(ROOT).as_posix(),'sha256':digest(raw)})
        print(json.dumps({'historical_completed_modes':ordinal,'rows':len(rows),'mode':mode}),flush=True)
        return report,outputs,traces
    evaluator._run_mode=measured
    sys.argv=['evaluate_hybrid_release','--index-dir',str(ROOT/'.tmp/hybrid-index'),
        '--calibration',str(ROOT/'evaluation/results/hybrid_retrieval_calibration.json'),'--output-dir',str(output)]
    try:
        code=evaluator.main()
    finally:
        from campusai.retrieval.model_runtime import retrieval_runtime
        runtime=retrieval_runtime()
        commits=[]
        for model in runtime._models.values():
            first=model._modules.get('0')
            auto=getattr(first,'auto_model',None)
            if auto is not None:commits.append(getattr(auto.config,'_commit_hash',None))
        binding.update({'actual_modes':calls,'source_worktree_clean_after':not bool(git(tree,'status','--porcelain')),
            'loaded_dense_commit_hashes':commits,'runtime_loaded_models':runtime.loaded_models()})
        for name,module in list(sys.modules.items()):
            if (name=='campusai' or name.startswith('campusai.')) and getattr(module,'__file__',None):
                if not Path(module.__file__).resolve().is_relative_to(tree/'src'):
                    raise ValueError('mixed source after measurement')
        binding['status']='ACTUAL_HISTORICAL_REMEASUREMENT_SOURCE_VERIFIED'
        (output/'run_identity.json').write_text(json.dumps(binding,indent=2)+'\n',encoding='utf8')
    if not binding['source_worktree_clean_after']:
        raise ValueError('historical source changed')
    if commits!=[baseline['dense_model']['revision']]:
        raise ValueError('actual dense revision differs from historical pinned identity')
    return code


if __name__=='__main__':
    raise SystemExit(main())
