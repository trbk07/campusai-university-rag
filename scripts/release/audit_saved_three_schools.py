"""Reproduce an offline transcript audit. Never calls an app or a model.

Review receipts are human/agent judgements, not substring grading. Historical
four-document predictions cannot certify the new three-document fixture.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
import unicodedata


def digest(text):
    value = ' '.join(unicodedata.normalize('NFKC', text).casefold().split())
    return hashlib.sha256(value.rstrip('.!?').strip().encode()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def parts(value):
    return [re.sub(r'^\[L\d+\]\s*', '', s.strip()) for s in value.split(' || ')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack', type=Path, required=True)
    parser.add_argument('--saved-results', type=Path, required=True)
    parser.add_argument('--run', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    bank_path = args.pack/'campusai_golden_65_3schools.jsonl'
    bank = [json.loads(s) for s in bank_path.read_text(encoding='utf-8-sig').splitlines() if s.strip()]
    archive = read(args.saved_results)
    run = next(r for r in archive['runs'] if r['id'] == args.run)
    reviews = read(args.output/'review_receipts.json')
    predictions = {digest(p['request']['question']): p for p in run['predictions']}
    records = []
    for case in bank:
        questions, expected = parts(case['input']), parts(case['expected'])
        if len(questions) != len(expected):
            raise ValueError('conversation_gold_turn_count_mismatch')
        for index, (question, gold) in enumerate(zip(questions, expected), 1):
            pred = predictions.get(digest(question))
            if pred and (pred['case'] != case['id'] or pred['turn'] != index):
                raise ValueError('question_case_turn_binding_mismatch')
            response = (pred or {}).get('response', {})
            answer = response.get('answer', {})
            trace = (pred or {}).get('trace', {})
            review = reviews[case['id']]
            status = review['status'] if pred else 'MISSING'
            evidence = trace.get('retrieved_evidence', [])
            drafts = [a.get('provider_payload') for g in trace.get('grounding_diagnostics', []) for a in g.get('attempts', [])]
            records.append(dict(case_id=case['id'], turn=index, group=case['group'], question=question,
                expected_answer=gold, source=case['source'], gold_status=case['gold_status'],
                question_sha256=digest(question), historical_run=run['id'],
                status=status, final_answer=answer.get('answer'), citations=answer.get('citations', []),
                failure_stage=review['stage'], review_notes=review['notes'],
                correct_chunk_retrieved='NOT_MEASURABLE',
                stored_first_five=evidence[:5], stored_evidence=evidence,
                raw_drafts=drafts, context_evidence_ids=[g.get('evidence_ids', []) for g in trace.get('grounding_diagnostics', [])],
                actual_packed_context=None, pre_generation_capture_verified=False,
                original_request=(pred or {}).get('request'), historical_trace=trace,
                latency_ms=(pred or {}).get('latency_ms'), http_status=(pred or {}).get('http_status')))
    if len(bank) != 65 or len(records) != 73:
        raise ValueError('benchmark_size_changed')
    counts = Counter(r['status'] for r in records)
    valid = [r for r in records if r['status'] != 'GOLD_REVIEW']
    cases_valid = [c for c in bank if reviews[c['id']]['status'] != 'GOLD_REVIEW']
    case_pass = sum(all(r['status'] == 'PASS' for r in records if r['case_id'] == c['id']) for c in cases_valid)
    metrics = dict(kind='HISTORICAL_TRANSCRIPT_COMPLIANCE_ONLY', counts=dict(counts),
                   observed_turns=sum(r['final_answer'] is not None for r in records), expected_turns=73,
                   pass_turns=counts['PASS'], valid_expected_turns=len(valid),
                   transcript_compliance_percent=100*counts['PASS']/len(valid),
                   case_pass=case_pass, valid_cases=len(cases_valid),
                   case_transcript_compliance_percent=100*case_pass/len(cases_valid),
                   generation_accuracy_three_school_fixture=None, recall_at_1=None, recall_at_3=None,
                   recall_at_5=None, conditional_generation_accuracy=None,
                   reason='Historical requests selected four PDFs; stored ranks are not a verified pre-generation snapshot and packed contexts are absent. Missing predictions remain in the denominator. FACT15 is separately quarantined.')
    save(args.output/'metrics.json', metrics)
    with (args.output/'trace.jsonl').open('w', encoding='utf-8') as out:
        for record in records:
            out.write(json.dumps(record, ensure_ascii=False)+'\n')
    fields = ['case_id','turn','question','expected_answer','source','historical_run','status',
              'correct_chunk_retrieved','final_answer','citations','failure_stage','review_notes','latency_ms','http_status','stored_first_five']
    with (args.output/'results.csv').open('w', encoding='utf-8-sig', newline='') as out:
        writer = csv.DictWriter(out, fieldnames=fields)
        writer.writeheader()
        for record in records:
            writer.writerow({k: json.dumps(record[k], ensure_ascii=False) if isinstance(record[k], (dict, list)) else record[k] for k in fields})
    save(args.output/'benchmark_snapshot.json', bank)
    root = Path.cwd()
    manifest = dict(run_id=args.output.name, mode='OFFLINE_NO_INFERENCE', historical_run=run['id'],
                    historical_candidate=run.get('source_snapshot_commit'),
                    workspace_commit=subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
                    benchmark_sha256=hashlib.sha256(bank_path.read_bytes()).hexdigest(),
                    archive_sha256=hashlib.sha256(args.saved_results.read_bytes()).hexdigest(),
                    selected_run_sha256=hashlib.sha256(json.dumps(run, ensure_ascii=False,sort_keys=True).encode()).hexdigest(),
                    reviews_sha256=hashlib.sha256((args.output/'review_receipts.json').read_bytes()).hexdigest(),
                    historical_protocol=run['protocol'], historical_trace_binding=run.get('raw_observer_trace_binding'),
                    historical_citation_audit=run.get('citation_audit'),
                    pdf_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in args.pack.glob('*.pdf')},
                    generation_fixture_status='NOT_EQUIVALENT_TO_THREE_SCHOOL_FIXTURE',
                    all_historical_selected_doc_counts=sorted({len(p['request']['doc_ids']) for p in run['predictions']}))
    save(args.output/'manifest.json', manifest)
    failures = ['# Offline failure analysis', '', 'Single historical R15 candidate. No supplement is mixed into these records.', '']
    for record in records:
        if record['status'] == 'PASS':
            continue
        failures.extend([f"## {record['case_id']} / turn {record['turn']} - {record['status']}", '',
                         f"Stage: {record['failure_stage']}. {record['review_notes']}", '',
                         f"Question: {record['question']}", '', f"Expected (unchanged): {record['expected_answer']}", '',
                         f"Actual final: {record['final_answer'] or '[NO EXACT SAVED PREDICTION]'}", '',
                         'Stored drafts: '+json.dumps(record['raw_drafts'],ensure_ascii=False), '',
                         'Stored evidence IDs: '+json.dumps([e['chunk_id'] for e in record['stored_evidence']]), '',
                         'Context evidence IDs are retained; the exact packed prompt is unavailable. Missing evidence cannot automatically be attributed to the LLM.', ''])
    (args.output/'failure_analysis.md').write_text('\n'.join(failures), encoding='utf-8')
    print(json.dumps(metrics))


if __name__ == '__main__':
    main()
