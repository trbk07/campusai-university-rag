"""Actual product preflight/Chat replay for the frozen small Phase 9 protocol.

No provider transport is created. Preflight stops at generate_json and exports
the application's actual prompt/schema. Recorded responses are separately scored.
"""
import argparse
import copy
from dataclasses import asdict
from datetime import date
import hashlib
import json
import re
import time

from evaluation.common.artifact_store import ROOT, resolve_artifact
from evaluation.phase9.prepare import INDEX, RAW, OUT
from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.llm.client import LLMError
from campusai.rag.service import CampusAIQueryService
from campusai.rag.temporal import fold, verified_documents
from campusai.rag.schemas import validate_release_response
from campusai.retrieval.bm25_index import BM25Index
from campusai.retrieval.dense_index import DenseIndex, corpus_hash
from campusai.retrieval.hybrid import HybridRetriever
from campusai.retrieval.tokenizer_vi import source_body
from evaluation.common.release_artifacts import source_identity
from evaluation.phase8.score_temporal_product_outputs import _index_tree_sha256
from jsonschema import Draft202012Validator

TARGET = RAW / 'index'


def read(path):
    return json.loads(resolve_artifact(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(resolve_artifact(path).read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def records():
    protocol = read(OUT / 'protocol.json')
    assert protocol['benchmark_sha256'] == sha(OUT / 'benchmark.jsonl')
    assert protocol['source_records_sha256'] == sha(RAW / 'source-records.json')
    for path, digest in protocol['source_bindings'].items():
        assert sha(ROOT / path) == digest, path
    sources = read(RAW / 'source-records.json')['sources']
    result = []
    for source in sources:
        label, doc_id = source['label'], source['doc_id']
        items = copy.deepcopy(source['original_items'])
        family = 'Robotics Engineering' if label.startswith('robotics') else 'Electronics and Communications Engineering Technology'
        version = 'QH-2025' if label.endswith('QH2025') else label.rsplit('-', 1)[1]
        proof_patterns = dict(family_id=re.escape(family).replace(r'\ ', r'[\s\xa0]+'),
            version_label=r'QH[\s\xa0\xad\-–]*2025' if version == 'QH-2025' else version)
        block = dict(schema_version=1, family_id='VNU-UET/' + family, version_label=version,
                     proofs={}, review='Codex — Automated AI Review')
        for field, pattern in proof_patterns.items():
            for item in items:
                body = source_body(item, decode_tables=False)
                match = re.search(pattern, body, re.I)
                if match:
                    block['proofs'][field] = dict(quote=match[0], chunk_id=item['chunk_id'], page=item['page'])
                    break
            assert field in block['proofs'], (label, field)
        for item in items:
            item.setdefault('doc_id', doc_id)
            item.setdefault('page_range', [item['page'], item['page']])
            item.setdefault('metadata', {})['temporal'] = copy.deepcopy(block)
        doc = dict(doc_id=doc_id, items=items, temporal=block, label=label)
        assert len(verified_documents([doc])) == 1
        result.append(doc)
    return result


def build_index(docs):
    TARGET.mkdir(parents=True, exist_ok=True)
    receipt = TARGET / 'source-bindings.json'
    expected = dict(source_records_sha256=sha(RAW / 'source-records.json'),
                    annotation_fingerprint=hashlib.sha256(json.dumps(docs, sort_keys=True).encode()).hexdigest())
    if receipt.exists():
        assert read(receipt) == expected, 'index annotation drift; do not overwrite frozen index'
        return
    for doc in docs:
        target = TARGET / doc['doc_id']
        target.mkdir(parents=True, exist_ok=True)
        BM25Index(doc['items'], 'vi').save(target / 'bm25.json')
        original = INDEX / doc['doc_id'] / 'dense.json'
        if original.exists():
            dense = DenseIndex.load(original)
            assert corpus_hash(doc['items']) == dense.manifest['corpus_hash']
            dense.items = doc['items']  # only source-reviewed metadata changed
        else:
            dense = DenseIndex(model_name='BAAI/bge-m3', device='cuda', batch_size=8)
            dense.build(doc['items'], corpus_id='phase9-real-source', document_id=doc['doc_id'])
        dense.save(target / 'dense.json')
    write(receipt, expected)


class RecordedOrCapturedLLM:
    model = 'owner-mediated-gemini-chat'
    generation_config = {'maxOutputTokens': 1024}

    def __init__(self, responses=None):
        self.responses = responses or {}
        self.qid = None
        self.captures = {}

    def generate_json(self, prompt, schema=None, **kwargs):
        self.captures[self.qid] = dict(prompt=prompt, schema=schema)
        if self.qid not in self.responses:
            raise LLMError('LOCAL_PREFLIGHT_CAPTURE_NO_PROVIDER_CALL')
        return self.responses[self.qid]


def run(responses_path=None, capture_file=None):
    capture_file = capture_file or RAW / 'preflight.json'
    if not responses_path and capture_file.exists():
        raise ValueError('Capture is frozen; use --responses or a new --capture-file for an explicit repair.')
    docs = records()
    build_index(docs)
    rows = [json.loads(line) for line in (OUT / 'benchmark.jsonl').read_text(encoding='utf-8').splitlines()]
    identity = source_identity(ROOT)
    positive = {r['qid'] for r in rows if r['answerable']}
    responses = {}
    if responses_path:
        for line in resolve_artifact(responses_path).read_text(encoding='utf-8').splitlines():
            row = json.loads(line)
            assert row['qid'] not in responses
            responses[row['qid']] = row['response']
        frozen = read(capture_file)
        assert set(responses) <= positive and responses, 'Unexpected or empty Chat population'
        assert identity['runtime_sha256'] == frozen['source_identity']['runtime_sha256'], 'runtime changed after packet capture'
        assert _index_tree_sha256(TARGET) == frozen['index_tree_sha256']
        for qid, value in responses.items():
            Draft202012Validator(frozen['captures'][qid]['schema']).validate(value)
    llm = RecordedOrCapturedLLM(responses)
    retriever = HybridRetriever(TARGET, dense_device='cuda')
    service = CampusAIQueryService(retriever, GroundedAnswerGenerator(llm),
        default_mode='hybrid', temporal_clock=lambda: date(2026, 10, 14))
    observations = []
    try:
        for row in rows:
            llm.qid = row['qid']
            started = time.perf_counter()
            answer = service.ask(row['question'], doc_ids=row['doc_ids'])
            public = answer.to_public_dict()
            trace = service._request_local.temporal_trace
            observations.append(dict(qid=row['qid'], temporal=trace,
                expected_status=row['expected_status'], expected_eligible_doc_ids=row['expected_eligible_doc_ids'],
                routing_correct=trace['status'] == row['expected_status'] and set(trace['eligible_doc_ids']) == set(row['expected_eligible_doc_ids']),
                public=public, public_schema_valid=validate_release_response(public)[0],
                evidence_ids=[r.chunk_id for r in service.last_retrieval],
                model_boundary_reached=row['qid'] in llm.captures,
                elapsed_local_ms=(time.perf_counter()-started)*1000))
    finally:
        service.close()
    mode = 'recorded-replay' if responses_path else 'preflight'
    assert source_identity(ROOT) == identity, 'source drift during run'
    if responses_path:
        assert llm.captures == frozen['captures'], 'actual prompt/schema differs from submitted Chat packet'
    receipt = (RAW / (capture_file.stem + '-replay-' + sha(responses_path)[:12] + '.json')
               if responses_path else capture_file)
    if responses_path:
        original_receipt, attempt = receipt, 2
        while receipt.exists():
            receipt = original_receipt.with_name(original_receipt.stem + f'-rerun-{attempt}.json')
            attempt += 1
    write(receipt, dict(mode=mode, provider_posts=0,
        responses_sha256=sha(responses_path) if responses_path else None,
        supplied_model_cases=sorted(responses), missing_model_cases=sorted(positive - set(responses)),
        source_identity=identity, index_tree_sha256=_index_tree_sha256(TARGET),
        benchmark_sha256=sha(OUT / 'benchmark.jsonl'), protocol_sha256=sha(OUT / 'protocol.json'),
        observations=observations, captures=llm.captures))
    if not responses_path:
        assert set(llm.captures) == positive, (positive, set(llm.captures))
        assert all(o['routing_correct'] for o in observations), [o['qid'] for o in observations if not o['routing_correct']]
        prompt = ['# Phase 9 — Gemini Chat quality packet', '',
            'Process every CASE independently using only its supplied evidence. No web search or outside knowledge.',
            'Return a downloadable UTF-8 JSONL file: one {"qid":"...","response":{...}} per case, no Markdown.',
            'Each response must satisfy that case schema. Preserve exact source quotes; JSON-escape all strings.',
            'State the requested version; comparisons must answer both versions with their own citations.',
            'If evidence is insufficient, abstain. Never invent dates, global current validity, or replacement relations.', '']
        for row in rows:
            if row['qid'] in positive:
                capture = llm.captures[row['qid']]
                prompt += [f'## CASE {row["qid"]}', 'PROMPT:', capture['prompt'], 'SCHEMA:',
                    json.dumps(capture['schema'], ensure_ascii=False), '']
        if capture_file.name == 'preflight.json':
            (OUT / 'gemini-chat-packet.md').write_text('\n'.join(prompt), encoding='utf-8')
        else:
            # Preserve the sent packet and export only changed actual payloads.
            original = read(RAW / 'preflight.json')['captures']
            changed = {qid for qid, capture in llm.captures.items() if capture != original[qid]}
            sections = prompt[:8]
            for row in rows:
                if row['qid'] in changed:
                    capture = llm.captures[row['qid']]
                    sections += [f'## CASE {row["qid"]}', 'PROMPT:', capture['prompt'], 'SCHEMA:',
                                 json.dumps(capture['schema'], ensure_ascii=False), '']
            packet = OUT / (capture_file.stem + '-chat-packet.md')
            assert not packet.exists(), 'Repair packet already frozen'
            packet.write_text('\n'.join(sections), encoding='utf-8')
    print(json.dumps(dict(mode=mode, cases=len(observations), routing_correct=sum(o['routing_correct'] for o in observations),
        model_cases=len(llm.captures), provider_posts=0)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--responses', type=str)
    parser.add_argument('--capture-file', type=str, help='Explicit new capture for a source-reviewed repair; never overwrites the original.')
    args = parser.parse_args()
    run(ROOT / args.responses if args.responses else None,
        ROOT / args.capture_file if args.capture_file else None)
