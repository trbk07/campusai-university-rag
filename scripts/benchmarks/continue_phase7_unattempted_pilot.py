"""Continue only the never-attempted suffix of one authorized pilot packet.

The original failed journal stays immutable. No failed prompt is retried and
the combined call ceiling remains twelve. A continuation cannot restart.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time

from campusai.rag.grounding import GroundedAnswerGenerator
from evaluation.common.release_artifacts import read_json, write_json, sha256, source_identity
from evaluation.reranker.collect_paired_answers import recording_generate
from evaluation.reranker.paired_answer_quality import answer_digest
from scripts.benchmarks.phase7_dev_answer_pilot import results
from scripts.benchmarks.phase7_final_policy_pilot import ROOT, bound_sources, validate_authorization


def remaining_pairs(packet, prior):
    observed=prior['observations']
    if (prior.get('status') not in ('PARTIAL_PROVIDER_OR_PRECHECK_FAILURE',
                                  'CONTINUATION_PARTIAL_PROVIDER_OR_PRECHECK_FAILURE') or prior.get('source_stable') is not True
            or not observed or len(observed)>=len(packet['pairs'])):
        raise ValueError('only a completed, source-stable partial journal can continue')
    keys=[(o['qid'],o['arm']) for o in observed]
    expected=[(p['qid'],p['arm']) for p in packet['pairs'][:len(observed)]]
    if keys!=expected or len(set(keys))!=len(keys):
        raise ValueError('prior observations must be the exact unique packet prefix')
    count=0
    for pair,obs in zip(packet['pairs'],observed):
        calls=obs['llm_calls']
        if len(calls)!=int(pair['planned_provider_call']):
            raise ValueError('prior attempted-call accounting is incomplete')
        for call in calls:
            if call['prompt_sha256']!=pair['prompt_sha256'] or call['provider_status'] not in ('completed','failed'):
                raise ValueError('prior call no longer binds the authorized prompt')
        count+=len(calls)
    if count!=prior['attempted_calls'] or count>=12:
        raise ValueError('combined call ceiling exhausted or inconsistent')
    suffix=packet['pairs'][len(observed):]
    if count+sum(p['planned_provider_call'] for p in suffix)!=12:
        raise ValueError('remaining calls differ from authorized twelve-call ceiling')
    return suffix


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('packet','authorization','prior','config'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    output=args.prior.with_name(args.prior.stem+'-continuation.json')
    if output.exists():
        raise FileExistsError('continuation already consumed; never restart')
    packet,prior=read_json(args.packet),read_json(args.prior)
    validate_authorization(args.packet,packet,read_json(args.authorization))
    if (prior['packet_sha256']!=sha256(args.packet) or prior['authorization_sha256']!=sha256(args.authorization)
            or packet['bound_sources']!=bound_sources()):
        raise ValueError('exact packet/authorization/grounding source changed')
    suffix=remaining_pairs(packet,prior)
    import yaml
    from campusai.llm.client import GeminiClient
    config=yaml.safe_load(args.config.read_text(encoding='utf8'))
    key=os.environ.get('GEMINI_API_KEY') or config.get('api_key')
    if not key:raise ValueError('credential missing')
    client=GeminiClient(key,model=packet['model'],cache=None,max_retries=0,timeout=60)
    failures=[]
    original_generate=client.generate
    def sanitized_generate(prompt,**options):
        try:return original_generate(prompt,**options)
        except Exception as error:
            cause=error.__cause__
            status=getattr(cause,'code',None)
            failures.append({'exception_type':type(error).__name__,
                'cause_type':type(cause).__name__ if cause else None,
                'http_status':status if type(status) is int and 100<=status<=599 else None})
            raise
    calls=[];client.generate=recording_generate(sanitized_generate,calls)
    original_json=client.generate_json
    client.generate_json=lambda prompt,**options:original_json(prompt,generationConfig=packet['generation_config'],**options)
    generator=GroundedAnswerGenerator(client,max_context_chars=12000,max_context_tokens=2500)
    before=source_identity(ROOT)
    record={'schema_version':1,'status':'CONTINUATION_IN_PROGRESS','release_eligible':False,
        'packet_sha256':sha256(args.packet),'authorization_sha256':sha256(args.authorization),
        'prior_path':args.prior.as_posix(),'prior_sha256':sha256(args.prior),
        'prior_attempted_calls':prior['attempted_calls'],'attempted_calls':prior['attempted_calls'],
        'observations':prior['observations'].copy(),'source_identity_before':before,
        'effective_grounding_sources':bound_sources(),'new_segment_observations':0,
        'retried_prompt_count':0,'live_provider':True,'answer_cache_enabled':False,'llm_cache_enabled':False,
        'continuation_runner_sha256':sha256(Path(__file__)),'sanitized_failures':failures}
    with output.open('x',encoding='utf8') as stream:json.dump(record,stream,ensure_ascii=False,allow_nan=False)
    elapsed=(datetime.now(timezone.utc)-datetime.fromisoformat(prior['observations'][-1]['observed_at'])).total_seconds()
    previous_start=time.monotonic()-max(0,elapsed)
    try:
        for pair in suffix:
            selected=results(pair['evidence'])
            if pair['planned_provider_call']:
                if generator.prompt(pair['question'],selected)!=pair['prompt']:raise ValueError('authorized prompt changed')
                remaining=30-(time.monotonic()-previous_start)
                if remaining>0:time.sleep(remaining)
                previous_start=time.monotonic()
            calls.clear();answer=generator.answer(pair['question'],selected);public=answer.to_public_dict()
            record['attempted_calls']+=len(calls);record['new_segment_observations']+=1
            record['observations'].append({'qid':pair['qid'],'arm':pair['arm'],'answer':public,
                'grounding_diagnostics':answer.to_dict(),'llm_calls':list(calls),
                'observed_at':datetime.now(timezone.utc).isoformat(),
                'review':{'status':'pending','answer_sha256':answer_digest(public)}})
            record['status']='PENDING_SEMANTIC_REVIEW';write_json(output,record)
            print(json.dumps({'observed_arms':len(record['observations']),'combined_provider_calls':record['attempted_calls'],
                'abstained':answer.abstained,'reason':answer.reason,'sanitized_failures':failures}),flush=True)
            if (len(calls)!=int(pair['planned_provider_call']) or record['attempted_calls']>12
                    or any(c['provider_status']!='completed' or c['cached'] for c in calls)):
                record['status']='CONTINUATION_PARTIAL_PROVIDER_OR_PRECHECK_FAILURE'
                return 1
    finally:
        record['source_identity_after']=source_identity(ROOT);record['source_stable']=before==record['source_identity_after']
        write_json(output,record)
    return 0


if __name__=='__main__':raise SystemExit(main())
