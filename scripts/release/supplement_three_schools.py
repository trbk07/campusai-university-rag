"""One missing three-school turn through the real local API; no gold in HTTP.

This is an explicitly requested supplement, never a replacement cohort score.
Reservations survive errors and interruption. Run only for an unasked question.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import time
import unicodedata
from urllib.request import Request, urlopen
from urllib.error import HTTPError


def digest(text):
    normalized = ' '.join(unicodedata.normalize('NFKC', text).casefold().split())
    return hashlib.sha256(normalized.rstrip('.!?').strip().encode()).hexdigest()


def save(path, value):
    with path.open('w', encoding='utf-8') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path.cwd()
    args.output.mkdir(parents=True, exist_ok=False)
    bank = [json.loads(s) for s in (args.pack/'campusai_golden_65_3schools.jsonl').read_text(encoding='utf-8-sig').splitlines() if s.strip()]
    registry_path = root/'evaluation/results/campusai_100_remediation_20261103/results.json'
    raw = registry_path.read_bytes()
    data = json.loads(raw)
    registry = data['question_lock_registry']
    questions = [(c['id'], re.sub(r'^\[L\d+\]\s*', '', q.strip()))
                 for c in bank for q in c['input'].split(' || ')]
    missing = [(ident, q) for ident, q in questions if digest(q) not in registry['entries']]
    # Narrow scope selected after auditing the historical R15 responses.
    if len(missing) != 1 or missing[0][0] != 'ABS07':
        raise ValueError('missing_scope_changed_requires_fresh_offline_audit')
    ident, question = missing[0]
    fingerprint = digest(question)
    for path in root.glob('data/operations/**/attempts.sqlite3'):
        with sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True) as db:
            if db.execute('SELECT 1 FROM attempts WHERE digest=?', (fingerprint,)).fetchone():
                raise ValueError('question_already_attempted_in_retained_journal')
    files = sorted(args.pack.glob('*.pdf'))
    if len(files) != 3:
        raise ValueError('exact_three_pdf_scope_required')
    doc_ids = [hashlib.sha256(p.read_bytes()).hexdigest() for p in files]
    with urlopen('http://127.0.0.1:8000/api/documents', timeout=10) as response:
        documents = json.load(response)
    if not all(any(d['doc_id'] == ident and d['ready'] for d in documents['documents']) for ident in doc_ids):
        raise ValueError('source_not_ready')
    body = dict(question=question, doc_ids=doc_ids, language='vi', history=[])
    hashes = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in root.glob('configs/*.yaml') if p.name not in {'key.yaml', 'gemini.yaml'}}
    index_files = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in (root/'data/web-test/index').rglob('*') if p.is_file() and p.suffix == '.json'}
    manifest = dict(run_id=args.output.name, kind='SEPARATE_MISSING_TURN_SUPPLEMENT',
                    workspace_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                    workspace_diff_sha256=hashlib.sha256(subprocess.check_output(['git', 'diff', '--binary'])).hexdigest(),
                    running_process_candidate='UNVERIFIED; workspace hash is not a process identity',
                    config_files_sha256=hashes, observed_index_files_sha256=index_files,
                    index_identity='Observed data/web-test index; running-process binding unverified',
                    pdf_sha256={p.name: h for p, h in zip(files, doc_ids)},
                    question_sha256=fingerprint, registry_before_sha256=hashlib.sha256(raw).hexdigest(),
                    authorization='Owner: nếu thiếu hoặc k đủ thì tự chạy lại những câu còn thiếu',
                    ui_status='BLOCKED: no browsers exposed by computer-use runtime',
                    retrieval_trace_status='UNAVAILABLE from existing public API; not reconstructed from citations')
    save(args.output/'manifest.json', manifest)
    save(args.output/'request.json', body)
    # Persist both a durable reservation and central lock BEFORE the only POST.
    save(args.output/'attempt.json', dict(status='reserved', question_sha256=fingerprint, case_id=ident))
    if registry_path.read_bytes() != raw:
        raise ValueError('question_registry_changed')
    registry['entries'][fingerprint] = dict(first_run=args.output.name, first_case=ident,
                                           first_turn=1, attempt_records=1)
    registry['distinct_locked_questions'] = len(registry['entries'])
    staged = registry_path.with_suffix('.json.pending-three-schools')
    save(staged, data)
    staged.replace(registry_path)
    started = time.perf_counter()
    request = Request('http://127.0.0.1:8000/api/query', data=json.dumps(body, ensure_ascii=False).encode(),
                      headers={'Content-Type': 'application/json'}, method='POST')
    result = dict(case_id=ident, question_sha256=fingerprint, prediction_kind='real_application_http')
    try:
        try:
            with urlopen(request, timeout=210) as response:
                result.update(http_status=response.status, response=json.load(response), request_id=response.headers.get('X-Request-ID'))
        except HTTPError as error:
            result.update(http_status=error.code, response=json.load(error))
        result['status'] = 'completed' if result['http_status'] == 200 and result['response'].get('ok') else 'failed'
    except Exception as error:
        result.update(status='failed', error_type=type(error).__name__)
    finally:
        result['elapsed_seconds'] = time.perf_counter()-started
        save(args.output/'attempt.json', result)
    print(json.dumps({k: v for k, v in result.items() if k != 'response'}))


if __name__ == '__main__':
    main()
