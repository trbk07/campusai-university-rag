"""Collect a frozen public QA bank through real application HTTP, never gold.

Preparation and tests do not authorize collection. The caller supplies the
exact authorized egress-scope fingerprint after execution approval. Review and
candidate pins are checked before opening the journal and before every send.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .blind_holdout import commitment, validate_public_cases
from .measure_ocr import percentile, save
from .native_journal import NativeJournal, question_digest


def _bound_file(root, name, expected):
    path = (root/name).resolve()
    if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError('frozen_file_binding_mismatch')
    return path


def preflight(root, protocol, authorized_scope):
    """No HTTP and no question locks until all whole-cohort gates succeed."""
    root = Path(root).resolve()
    scope = protocol['external_request_scope']
    if commitment(scope) != authorized_scope or protocol['external_request_scope_sha256'] != authorized_scope:
        raise ValueError('exact_egress_scope_required')
    if (scope['frozen_files_fingerprint'] != commitment(protocol['frozen_files_sha256'])
            or scope['source_review_sha256'] != protocol['source_review_sha256']
            or scope['failure_policy'] != protocol['failure_policy']):
        raise ValueError('execution_scope_binding_mismatch')
    for name, expected in protocol['frozen_files_sha256'].items():
        _bound_file(root, name, expected)
    if not protocol['frozen_files_sha256']:
        raise ValueError('candidate_file_bindings_required')
    bank_path = _bound_file(root, protocol['public_bank_path'], protocol['public_bank_sha256'])
    cases = json.loads(bank_path.read_text(encoding='utf-8'))['cases']
    ids = validate_public_cases(cases)
    if (len(cases) != protocol['expected_cases'] or len(cases) < 200
            or sum(len(c['turns']) for c in cases) != protocol['expected_turns']
            or scope['public_bank_sha256'] != protocol['public_bank_sha256']
            or scope['cases'] != len(cases) or scope['turns'] != protocol['expected_turns']):
        raise ValueError('whole_public_bank_scope_required')
    review_path = _bound_file(root, protocol['source_review_path'], protocol['source_review_sha256'])
    review = json.loads(review_path.read_text(encoding='utf-8'))
    received = review['peer_review_validation']
    if (review.get('development_gold_ready') is not True or len(received) != len(cases)
            or {r['case_id'] for r in received} != ids
            or any(r['status'] != 'SOURCE_BOUND_AI_APPROVAL' for r in received)):
        raise ValueError('whole_cohort_source_review_required')
    url = urlsplit(protocol['base_url'])
    if (url.scheme != 'http' or url.hostname not in {'127.0.0.1', '::1'}
            or url.username or url.password or url.path or url.query or url.fragment):
        raise ValueError('local_application_endpoint_required')
    if protocol['failure_policy'] not in {'stop', 'continue_independent'}:
        raise ValueError('frozen_failure_policy_required')
    return cases, commitment(protocol)


def send_real_http(base, body, case_id, turn):
    class LocalOnly(HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    request = Request(base+'/api/query', data=json.dumps(body, ensure_ascii=False, allow_nan=False).encode(),
                      headers={'Content-Type': 'application/json',
                               'X-CampusAI-Qualification': case_id+':'+str(turn+1)})
    try:
        with build_opener(LocalOnly).open(request, timeout=210) as response:
            return response.status, json.load(response), response.headers.get('X-Request-ID')
    except HTTPError as error:
        with error:
            try:
                response = json.load(error)
            except (ValueError, OSError):
                response = {'ok': False, 'error_code': 'invalid_http_error_body'}
        return error.code, response, error.headers.get('X-Request-ID')


def _collect_locked(root, protocol, authorized_scope, output, *, send):
    """One reservation per question; resumed CTX uses persisted actual answers."""
    root = Path(root).resolve(); output = Path(output)
    cases, candidate = preflight(root, protocol, authorized_scope)
    registry_path = (root/protocol['question_lock_registry_path']).resolve()
    registry = json.loads(registry_path.read_text(encoding='utf-8'))
    registry_stamp = registry_path.stat().st_mtime_ns
    external_locks = registry['question_lock_registry']['entries']
    # Retained native journals must have been audited into the registry. Pin
    # every audited file so a new interrupted attempt cannot be overlooked.
    for name, expected in protocol['retained_native_files_sha256'].items():
        _bound_file(root, name, expected)
    if not protocol['retained_native_files_sha256']:
        raise ValueError('retained_native_journal_bindings_required')
    output.mkdir(parents=True, exist_ok=True)
    journal = NativeJournal(output/'attempts.sqlite3', candidate, cases, locked_questions=external_locks)
    own_locks = {row[0] for row in journal.db.execute('SELECT digest FROM attempts')}
    if any(question_digest(q) in external_locks and question_digest(q) not in own_locks
           for c in cases for q in c['turns']):
        journal.close()
        raise ValueError('public_question_already_attempted')
    stopped = False; aborted = None
    try:
        for case in cases:
            existing = journal.db.execute('SELECT turn,status FROM attempts WHERE case_id=? ORDER BY turn',
                                          (case['id'],)).fetchall()
            if any(status != 'completed' for _n, status in existing):
                continue  # Error/interruption stays locked; no invented CTX.
            for turn in range(len(existing), len(case['turns'])):
                # Code/config/index/review changes abort before reserving the
                # next question, preserving unattempted questions for later.
                preflight(root, protocol, authorized_scope)
                if registry_path.stat().st_mtime_ns != registry_stamp:
                    raise ValueError('question_registry_changed_during_collection')
                digest, body = journal.reserve(case['id'], turn)
                started_at = datetime.now(timezone.utc).isoformat()
                started = time.perf_counter()
                try:
                    code, response, request_id = send(protocol['base_url'], body, case['id'], turn)
                except (URLError, TimeoutError, OSError, ValueError) as error:
                    code, request_id = 0, None
                    response = {'ok': False, 'transport_error': type(error).__name__}
                elapsed = time.perf_counter()-started
                journal.complete(digest, code, response, execution={
                    'started_at_utc': started_at, 'elapsed_seconds': elapsed,
                    'request_id': request_id, 'prediction_kind': 'real_application_http'})
                failed = journal.db.execute('SELECT status FROM attempts WHERE digest=?', (digest,)).fetchone()[0] != 'completed'
                print(json.dumps({'case_id': case['id'], 'turn': turn+1, 'http_status': code,
                                  'elapsed_seconds': round(elapsed, 3), 'failed': failed}), flush=True)
                if failed:
                    stopped = protocol['failure_policy'] == 'stop'
                    break
            if stopped:
                break
    except BaseException as error:
        aborted = type(error).__name__
        raise
    finally:
        rows = journal.db.execute('SELECT case_id,turn,request,status,response,http_status,execution FROM attempts ORDER BY rowid').fetchall()
        result = {'purpose': 'DEVELOPMENT_NOT_BLIND', 'candidate_fingerprint': candidate,
                  'protocol_sha256': commitment(protocol), 'expected_cases': len(cases),
                  'expected_turns': protocol['expected_turns'], 'attempted_turns': len(rows),
                  'status': 'STOPPED_ON_ERROR' if stopped else 'COLLECTION_INCOMPLETE',
                  'accuracy_percent': None, 'predictions': []}
        if aborted:
            result.update(status='ABORTED_EXCEPTION', error_type=aborted)
        for ident, turn, request, status, response, code, execution in rows:
            result['predictions'].append({'case_id': ident, 'turn': turn+1, 'request': json.loads(request),
                'status': status, 'response': json.loads(response) if response else None,
                'http_status': code, 'execution': json.loads(execution) if execution else None})
        if not aborted and len(rows) == protocol['expected_turns'] and all(r[3] == 'completed' for r in rows):
            result['status'] = 'COLLECTED_UNGRADED'
        latencies = [r['execution']['elapsed_seconds'] for r in result['predictions'] if r['execution']]
        result['p95_seconds'] = percentile(latencies)
        save(output/'results.json', result)
        journal.close()
        # One central-registry update per run, not a 100-MB rewrite per turn.
        # Interrupted/reserved requests are locked just as completed ones are.
        if registry_path.stat().st_mtime_ns != registry_stamp:
            registry = json.loads(registry_path.read_text(encoding='utf-8'))
        entries = registry['question_lock_registry']['entries']
        for ident, turn, request, _status, _response, _code, _execution in rows:
            digest = question_digest(json.loads(request)['question'])
            entries.setdefault(digest, {'first_run': 'native:'+candidate,
                                       'first_case': ident, 'first_turn': turn+1, 'attempt_records': 1})
        registry['question_lock_registry']['distinct_locked_questions'] = len(entries)
        save(registry_path, registry)
    return result


@contextmanager
def _registry_session(path, candidate):
    """An unresolved crash lock needs process verification, never auto-steal."""
    try:
        handle = path.open('x', encoding='utf-8')
    except FileExistsError:
        raise ValueError('collection_session_active_or_unresolved') from None
    try:
        handle.write(json.dumps({'pid': os.getpid(), 'candidate': candidate,
                                 'started_at_utc': datetime.now(timezone.utc).isoformat()}))
        handle.flush(); os.fsync(handle.fileno())
        yield
    finally:
        handle.close()
        path.unlink()


def collect(root, protocol, authorized_scope, output, *, send=send_real_http):
    root = Path(root).resolve()
    _cases, candidate = preflight(root, protocol, authorized_scope)
    registry = (root/protocol['question_lock_registry_path']).resolve()
    if not registry.is_relative_to(root):
        raise ValueError('registry_outside_qualification_root')
    with _registry_session(registry.with_name('.native-collection.lock'), candidate):
        return _collect_locked(root, protocol, authorized_scope, output, send=send)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', type=Path, required=True)
    parser.add_argument('--authorized-scope', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    collect(Path.cwd(), json.loads(args.protocol.read_text(encoding='utf-8')),
            args.authorized_scope, args.output)


if __name__ == '__main__':
    main()
