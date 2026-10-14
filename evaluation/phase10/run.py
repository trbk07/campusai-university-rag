"""Zero-provider actual application baseline and captured Chat replay.

Captures are the application's actual prompt/schema, never hand-picked gold.
All runs append immutable receipts. Missing Chat output is never quality PASS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import time
import zipfile
from datetime import date

from jsonschema import Draft202012Validator
from campusai.llm.client import LLMError
from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.rag.schemas import validate_release_response
from campusai.rag.service import CampusAIQueryService
from campusai.retrieval.hybrid import HybridRetriever
from evaluation.common.release_artifacts import source_identity
from evaluation.common.artifact_store import entries, resolve_artifact
from evaluation.phase8.score_temporal_product_outputs import _index_tree_sha256
from evaluation.phase10.prepare import ROOT,RAW,OUT,read,sha,prepare

INDEX=RAW/'index'


class CapturedOrRecordedModel:
    model='owner-mediated-gemini-chat'
    generation_config={'maxOutputTokens':1024}

    def __init__(self,responses):
        self.responses=responses
        self.captures={}
        self.qid=None

    def generate_json(self,prompt,schema=None,**kwargs):
        assert self.qid not in self.captures, 'more than one generation boundary per case'
        self.captures[self.qid]=dict(prompt=prompt,schema=schema)
        if self.qid not in self.responses:
            raise LLMError('LOCAL_CAPTURE_ONLY_NO_PROVIDER_CALL')
        return self.responses[self.qid]


def append_path(path):
    candidate=path
    i=2
    archived=entries()
    while candidate.exists() or candidate.relative_to(ROOT).as_posix() in archived:
        candidate=path.with_name(path.stem+f'-rerun-{i}'+path.suffix)
        i+=1
    return candidate


def build_index():
    sources=read(RAW/'source-records.json')['sources']
    for source in sources.values():
        for name in ['bm25.json','dense.json']:
            original=ROOT/source['source_index']/name
            target=INDEX/source['doc_id']/name
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists():assert sha(target)==sha(original), 'frozen index drift'
            else:shutil.copyfile(original,target)


def snapshot_before():
    target=RAW/'runtime-before.zip'
    if target.exists() or target.relative_to(ROOT).as_posix() in entries():return
    files=sorted((ROOT/'src').rglob('*.py'))+sorted(p for p in (ROOT/'configs').rglob('*')
        if p.is_file() and p.suffix in {'.json','.yaml','.yml','.toml'} and p.name not in {'key.yaml','gemini.yaml'})
    with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for path in files:z.write(path,path.relative_to(ROOT).as_posix())


def load_chat_responses(path, captures):
    """Preserve exact owner bytes and reject incomplete/wrong packets locally.

    This validates input format only. It never assigns a source-review PASS.
    Invalid raw input remains available for audit; no index/model is needed.
    """
    body=resolve_artifact(path).read_bytes()
    digest=hashlib.sha256(body).hexdigest()
    preserved=RAW/('received-chat-'+digest+'.jsonl')
    if preserved.exists() or preserved.relative_to(ROOT).as_posix() in entries():
        assert resolve_artifact(preserved).read_bytes()==body, 'raw input identity collision'
    else:
        preserved.parent.mkdir(parents=True,exist_ok=True)
        with preserved.open('xb') as stream:stream.write(body)
    responses={}
    for number,line in enumerate(body.decode('utf-8-sig').splitlines(),1):
        row=json.loads(line)
        if not isinstance(row,dict) or set(row)!={'qid','response'}:
            raise ValueError(f'Line {number}: expected exactly qid and response')
        qid=row['qid']
        if not isinstance(qid,str) or qid not in captures:
            raise ValueError(f'Line {number}: qid does not belong to the captured Phase10 packet')
        if qid in responses:
            raise ValueError(f'Line {number}: duplicate qid {qid}')
        Draft202012Validator(captures[qid]['schema']).validate(row['response'])
        responses[qid]=row['response']
    missing=set(captures)-responses.keys()
    if missing:
        raise ValueError('Incomplete Phase10 Chat packet; missing: '+', '.join(sorted(missing)))
    return responses,preserved,digest


def run(stage='before',responses_path=None,capture_path=None):
    prepare()
    protocol=read(OUT/'protocol.json')
    identity=source_identity(ROOT)
    if stage=='before':
        assert identity['runtime_sha256']==protocol['baseline_identity']['runtime_sha256'], 'before runtime already changed'
        snapshot_before()
    rows=[json.loads(line) for line in (OUT/'benchmark.jsonl').read_text(encoding='utf-8').splitlines()]
    responses={}
    frozen=None
    preserved=None
    response_digest=None
    if responses_path:
        assert capture_path, 'replay requires exact original capture receipt'
        frozen=read(capture_path)
        assert identity['runtime_sha256']==frozen['source_identity']['runtime_sha256']
        responses,preserved,response_digest=load_chat_responses(responses_path,frozen['captures'])
    build_index()
    if frozen:
        assert _index_tree_sha256(INDEX)==frozen['index_tree_sha256']
    model=CapturedOrRecordedModel(responses)
    retriever=HybridRetriever(INDEX,dense_device='cuda')
    service=CampusAIQueryService(retriever,GroundedAnswerGenerator(model),
        default_mode='hybrid',temporal_clock=lambda:date(2026,10,14))
    original_search=retriever.search
    searches=[]
    def observed_search(*args,**kwargs):
        result=original_search(*args,**kwargs)
        searches.append(dict(query=args[0],doc_ids=kwargs.get('doc_ids'),
            returned_candidates=len(result),top_k=kwargs.get('top_k')))
        return result
    retriever.search=observed_search
    observations=[]
    try:
        for row in rows:
            model.qid=row['qid'];searches.clear();started=time.perf_counter()
            answer=service.ask(**row['request'])
            public=answer.to_public_dict()
            capture=model.captures.get(row['qid'])
            observations.append(dict(qid=row['qid'],request=row['request'],public=public,
                public_schema_valid=validate_release_response(public)[0],
                retrieved=[x.to_dict() for x in service.last_retrieval],
                actual_model_evidence_ids=re.findall(r'chunk_id=([^\s]+)',capture['prompt']) if capture else [],
                generation_boundary_calls=int(capture is not None),model_output_supplied=row['qid'] in responses,
                searches=list(searches),temporal_trace=service._request_local.temporal_trace,
                multi_hop_trace=getattr(service._request_local,'multi_hop_trace',None),
                elapsed_local_ms=(time.perf_counter()-started)*1000))
    finally:service.close()
    assert source_identity(ROOT)==identity, 'source changed during evaluation'
    if frozen:assert model.captures==frozen['captures'], 'actual payload differs from submitted capture'
    path=append_path(RAW/(stage+('-replay' if responses_path else '-preflight')+'.json'))
    data=dict(status='RECORDED_REPLAY_PENDING_SOURCE_REVIEW' if responses_path else 'ACTUAL_PREFLIGHT_MODEL_QUALITY_UNMEASURED',
        source_identity=identity,protocol_sha256=sha(OUT/'protocol.json'),benchmark_sha256=sha(OUT/'benchmark.jsonl'),
        index_tree_sha256=_index_tree_sha256(INDEX),provider_posts=0,observations=observations,captures=model.captures,
        raw_chat_input=(dict(path=preserved.relative_to(ROOT).as_posix(),sha256=response_digest,
            parse_and_schema='PASS',normalization_applied=False) if preserved else None),
        supplied_model_qids=sorted(responses),missing_model_qids=sorted(set(model.captures)-responses.keys()))
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(receipt=path.relative_to(ROOT).as_posix(),cases=len(rows),model_boundaries=len(model.captures),
        local_branches=len(rows)-len(model.captures),provider_posts=0,quality_pass=False)))


def export_packet(capture_path):
    """Export exact actual payloads, without benchmark gold or review labels."""
    receipt=read(capture_path)
    assert receipt['source_identity']['runtime_sha256']==source_identity(ROOT)['runtime_sha256']
    assert receipt['protocol_sha256']==sha(OUT/'protocol.json')
    assert receipt['benchmark_sha256']==sha(OUT/'benchmark.jsonl')
    assert receipt['provider_posts']==0 and receipt['captures']
    packet=OUT/'gemini-chat-packet.md'
    assert not packet.exists(), 'sent packet immutable; explicitly review any replacement'
    sections=['# Phase 10 — actual application Chat packet','',
        'Process each CASE independently. Use only its PROMPT/EVIDENCE. Do not browse or use outside knowledge.',
        'Return one downloadable UTF-8 JSONL file, one {"qid":"...","response":{...}} per CASE.',
        'Return every case exactly once. Each response must satisfy its SCHEMA. No Markdown wrappers.',
        'Keep exact source codes, quotes, page numbers and accents; JSON-escape strings.',
        'Do not combine evidence between cases. If evidence is insufficient, abstain.',
        'This packet has no gold answers. It captures the application boundary, not API timing or availability.','']
    for qid,capture in receipt['captures'].items():
        sections.extend([f'## CASE {qid}','PROMPT:',capture['prompt'],'SCHEMA:',
                         json.dumps(capture['schema'],ensure_ascii=False),''])
    packet.write_text('\n'.join(sections),encoding='utf-8')
    manifest=dict(status='AWAITING_OWNER_MEDIATED_CHAT_OUTPUT',provider_posts=0,
        source_identity=receipt['source_identity'],capture_path=capture_path.relative_to(ROOT).as_posix(),
        capture_sha256=sha(capture_path),packet_sha256=sha(packet),qids=list(receipt['captures']),
        missing_raw_outputs=len(receipt['captures']),quality_pass=False,
        qualification='Owner-mediated Chat; model label/settings unverified, exposed corpus; not native API qualification.')
    (OUT/'chat-packet-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(packet=packet.relative_to(ROOT).as_posix(),cases=len(receipt['captures']),provider_posts=0)))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--stage',choices=['before','after'],default='before')
    parser.add_argument('--responses')
    parser.add_argument('--capture')
    parser.add_argument('--export-packet',help='Export an existing current-runtime capture, with no provider call')
    args=parser.parse_args()
    if args.export_packet:
        export_packet(ROOT/args.export_packet)
    else:
        run(args.stage,ROOT/args.responses if args.responses else None,ROOT/args.capture if args.capture else None)
