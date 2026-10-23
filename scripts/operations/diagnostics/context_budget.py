"""Measure source coverage and prompt size with local retrieval, zero LLM calls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from campusai.rag.context import resolve_query
from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.retrieval.hybrid import HybridRetriever


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    os.environ['HF_HUB_OFFLINE'] = '1'
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    retriever = HybridRetriever('data/index', dense_device='cpu')
    retriever.warm_up()
    history, rows = [], []
    baseline = GroundedAnswerGenerator(None)
    optimized = GroundedAnswerGenerator(None, max_context_chars=8000, balanced_context=True)
    for case in manifest['cases']:
        if case['kind'] != 'generated':
            continue
        query = resolve_query(case['question'], history=history[-8:]).resolved
        original = retriever.search(query, doc_ids=manifest['doc_ids'], top_k=5, mode='auto')
        broader = retriever.search(query, doc_ids=manifest['doc_ids'], top_k=8, mode='auto')
        before = baseline.prompt(query, original, case['language'])
        after = optimized.prompt(query, broader, case['language'])
        normalized = lambda value: ' '.join(value.split()).casefold()
        checks = [{'source_fact': fact, 'baseline_visible': normalized(fact) in normalized(before),
                   'optimized_visible': normalized(fact) in normalized(after)} for fact in case['source_facts']]
        rows.append({'id': case['id'], 'query': query, 'baseline_prompt_chars': len(before),
            'optimized_prompt_chars': len(after), 'checks': checks,
            'baseline_chunks': [r.chunk_id for r in original], 'optimized_chunks': [r.chunk_id for r in broader],
            'optimized_prompt': after})
        history.append({'role': 'user', 'content': case['question']})
    report = {'date': '2026-10-16', 'status': 'PASS' if all(c['optimized_visible'] for r in rows for c in r['checks']) else 'NOT_PASSED',
        'scope': 'Exposed public-source regression; prior user questions supply the same last-user topic anchor; no assistant text or provider calls',
        'provider_calls': 0, 'rows': rows,
        'baseline_total_prompt_chars': sum(r['baseline_prompt_chars'] for r in rows),
        'optimized_total_prompt_chars': sum(r['optimized_prompt_chars'] for r in rows),
        'manifest_sha256': hashlib.sha256(args.manifest.read_bytes()).hexdigest()}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'rows'}))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
