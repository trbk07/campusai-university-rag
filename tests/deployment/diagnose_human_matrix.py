"""Offline raw-input retrieval diagnostic; never certifies generated answers."""
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path

from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.rag.service import CampusAIQueryService
from campusai.retrieval.hybrid import HybridRetriever
from evaluation.benchmarks.build_student_natural_benchmark import query_input

ROOT = Path(__file__).resolve().parents[2]
PHASE = ROOT/'docs/deployment/phase13/evidence/comprehensive-natural-20261016'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    os.environ['HF_HUB_OFFLINE'] = '1'
    dataset = ROOT/'data/benchmark/student_natural_queries.jsonl'
    source = [json.loads(line) for line in dataset.read_text(encoding='utf-8').splitlines()]
    docs = sorted({g['doc_id'] for row in source for g in row['gold_evidence']})
    bindings = {'seed_corpus_upload_fixture':docs}
    for row in source:
        for item in row['document_context']['uploaded_documents']:
            bindings[item['document_ref']] = [item['sha256']]
    index = ROOT/'.tmp/baseline-index'
    service = CampusAIQueryService(HybridRetriever(index, dense_device='cpu'),
                                   GroundedAnswerGenerator(None), default_mode='hybrid')
    results, categories = [], defaultdict(Counter)
    try:
        for row in source:
            request = query_input(row, bindings)
            retrieved = service.retrieve(request['query'], doc_ids=request['doc_ids'],
                history=request['context'], selected_text=request['selected_text'], top_k=8)
            gold = {g['chunk_id'] for g in row['gold_evidence']}
            found = {r.chunk_id for r in retrieved}
            trace = getattr(service.retriever, 'last_trace', None)
            reason = getattr(trace, 'abstention_reason', None)
            result = {'id':row['id'],'category':row['category'],'query':row['query'],
                'doc_ids':request['doc_ids'],'answerable_annotation':row['answerable'],
                'ambiguous_annotation':row['ambiguous'],'retrieved':len(retrieved),
                'gold_chunks':len(gold),'gold_chunks_found':len(gold & found),
                'retrieved_ids':sorted(found),'reason':reason,
                'context':getattr(service._request_local,'context_trace',{})}
            results.append(result)
            categories[row['category']]['queries'] += 1
            if row['answerable']:
                categories[row['category']]['answerable'] += 1
                categories[row['category']]['all_gold_retrieved'] += int(gold <= found)
            if not retrieved:
                categories[row['category']]['no_candidates'] += 1
            if len(results) % 80 == 0:
                print(f'Processed {len(results)}/480 raw queries; no provider', flush=True)
    finally:
        service.close()
    report = {'status':'DIAGNOSTIC_COMPLETE','scope':'Raw-input context/retrieval only; no generated-answer quality claim',
        'dataset_author':'AI-authored, not human-reviewed, release_eligible=false; exposed regression, not new holdout',
        'dataset_sha256':sha(dataset),'queries':len(results),'documents':docs,'external_provider_posts':0,
        'categories':{k:dict(v) for k,v in categories.items()},'results':results,
        'sources_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'src/campusai').rglob('*.py')}}
    path = PHASE/'retrieval-diagnostic.json'
    assert not path.exists()
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Completed 480-query, seven-document offline diagnostic; not a generated-answer benchmark')


if __name__ == '__main__':
    main()
