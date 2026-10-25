"""Measure concurrent read-only library/PDF fact requests; never ask the model."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
import math
from pathlib import Path
import sqlite3
import threading
import time
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def measure(base_url, quota_path, *, users=20, turns=20):
    parsed = urlsplit(base_url)
    if parsed.scheme != 'http' or parsed.hostname not in {'127.0.0.1', 'localhost', '::1'} or parsed.path:
        raise ValueError('Use a loopback application URL without a path')
    if not 1 <= users <= 20 or not 2 <= turns <= 100:
        raise ValueError('Bounded workload requires 1..20 users and 2..100 turns')

    def reservations():
        with sqlite3.connect(quota_path.resolve().as_uri() + '?mode=ro', uri=True) as conn:
            return conn.execute('SELECT COUNT(*) FROM quota_attempts WHERE scope = ?',
                                ('gemini:owner:gemini-3.5-flash-lite',)).fetchone()[0]

    def request(endpoint, body=None):
        data = None if body is None else json.dumps(body).encode('utf-8')
        req = Request(base_url + endpoint, data=data, headers={'Content-Type': 'application/json'})
        started = time.perf_counter()
        try:
            with urlopen(req, timeout=30) as response:
                return response.status, json.load(response), time.perf_counter() - started
        except HTTPError as error:
            return error.code, json.load(error), time.perf_counter() - started

    initial_status, initial, _ = request('/api/documents')
    assert initial_status == 200
    original_ids = sorted(d['doc_id'] for d in initial['documents'])
    ready = [d for d in initial['documents'] if d['ready']]
    assert ready, 'At least one ready PDF is required'
    barrier = threading.Barrier(users)
    question = 'How many pages are in this PDF?'
    before = reservations()

    def user(index):
        barrier.wait(timeout=30)
        results = []
        doc = ready[index % len(ready)]
        for turn in range(turns):
            endpoint = '/api/query' if turn % 2 else '/api/documents'
            status, body, seconds = request(endpoint, {'question': question, 'doc_ids': [doc['doc_id']]}
                                            if turn % 2 else None)
            row = {'user': index, 'turn': turn, 'endpoint': endpoint, 'status': status,
                   'seconds': seconds, 'error_code': body.get('error_code')}
            if status == 200 and turn % 2:
                info = body['document_info']['documents']
                assert len(info) == 1 and info[0]['doc_id'] == doc['doc_id']
                assert info[0]['page_count'] == doc['page_count']
                row['verified_page_count'] = info[0]['page_count']
            elif status == 200:
                assert sorted(d['doc_id'] for d in body['documents']) == original_ids
            results.append(row)
        return results

    with ThreadPoolExecutor(max_workers=users) as executor:
        rows = [row for result in executor.map(user, range(users)) for row in result]
    after = reservations()
    _, final, _ = request('/api/documents')
    assert original_ids == sorted(d['doc_id'] for d in final['documents'])
    assert before == after, 'Unexpected provider use during metadata benchmark'

    def p95(values):
        return sorted(values)[math.ceil(.95 * len(values)) - 1]

    return {'scope': 'Actual app20 concurrent users,400 ordinary metadata/list requests; not20 native AI generations',
            'users': users, 'requests': len(rows), 'percentile_method': 'nearest rank',
            'status_counts': dict(Counter(str(row['status']) for row in rows)),
            'p95_seconds': p95([row['seconds'] for row in rows]),
            'endpoint_p95_seconds': {endpoint: p95([r['seconds'] for r in rows if r['endpoint'] == endpoint])
                                     for endpoint in ('/api/documents', '/api/query')},
            'quota_reservations_before': before, 'quota_reservations_after': after,
            'quota_count_scope': 'gemini:owner:gemini-3.5-flash-lite',
            'additional_provider_calls': after - before, 'original_document_ids_retained': original_ids,
            'rows': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    parser.add_argument('--quota', type=Path, default=Path('data/operations/flash-lite-quota.sqlite3'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = measure(args.url, args.quota)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items() if key != 'rows'}))


if __name__ == '__main__':
    main()
