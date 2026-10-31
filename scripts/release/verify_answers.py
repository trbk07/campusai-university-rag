"""Collect real local-web answers with frozen inputs, never gold in inference."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import threading
import time
import yaml
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from campusai.rag.schemas import validate_release_response
from .measure_ocr import digest, percentile, save, ROOT


def turns(row):
    """Only the user-authored input column can become a question."""
    value = row['input'].strip()
    if row.get('group') != 'multi-turn':
        return [value]
    values = re.split(r'\s*\|\s*(?=(?:Lượt|Turn)\s*\d+\s*:)', value, flags=re.I)
    return [re.sub(r'^(?:Lượt|Turn)\s*\d+\s*:\s*', '', item, flags=re.I) for item in values]


def inference_payload(question, doc_ids, history, language):
    return {'question': question, 'doc_ids': list(doc_ids), 'language': language,
            'history': [dict(turn) for turn in history]}


def natural_variants(rows, count, language='vi'):
    """Polite input variants reuse the question only, never labels or answers."""
    candidates = [row for row in rows if row.get('group') != 'multi-turn']
    if not 0 <= count <= len(candidates):
        raise ValueError('variant_count_exceeds_single_turn_cases')
    prefixes = (('Please help me check: ', 'According to the selected sources, ')
        if language == 'en' else ('Cho mình hỏi, ', 'Bạn giúp mình tra trong tài liệu: ',
                                  'Mình muốn biết: ', 'Theo nguồn đã chọn, '))
    return [{**row, 'id': 'natural_' + row['id'], 'input': prefixes[i % len(prefixes)] + row['input']}
            for i, row in enumerate(candidates[:count])]


def rss_monitor(pid):
    import psutil
    process = psutil.Process(pid)
    memory = {'server_pid': pid, 'total_ram_bytes': psutil.virtual_memory().total,
              'peak_rss_bytes': 0, 'sample_interval_seconds': .1}
    stopped = threading.Event()
    def sample_memory():
        try:
            rss = process.memory_info().rss
            for child in process.children(recursive=True):
                try:
                    rss += child.memory_info().rss
                except psutil.NoSuchProcess:
                    pass
            memory['peak_rss_bytes'] = max(memory['peak_rss_bytes'], rss)
        except psutil.Error as error:
            memory['error'] = type(error).__name__
    sample_memory()
    def sample_loop():
        while not stopped.wait(.1):
            sample_memory()
    worker = threading.Thread(target=sample_loop, daemon=True, name='qualification-rss')
    worker.start()
    def finish():
        stopped.set()
        worker.join(timeout=1)
    return memory, finish


def runtime_identity():
    files = subprocess.check_output(['git', 'ls-files', '-z', '--', 'src', 'scripts/operations',
        'configs/free_llm.yaml', 'configs/free_multi_project.yaml', 'configs/local', 'uv.lock'], cwd=ROOT)
    return {name: digest(ROOT / name) for name in files.decode().split('\0')
            if name and (ROOT / name).is_file()}


def request_json(base, path, body=None, timeout=210):
    encoded = None if body is None else json.dumps(body, ensure_ascii=False, allow_nan=False).encode('utf-8')
    request = Request(base + path, data=encoded, headers={'Content-Type': 'application/json'})
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, json.load(response), response.headers.get('X-Request-ID')
    except HTTPError as error:
        try:
            with error:
                return error.code, json.load(error), error.headers.get('X-Request-ID')
        except (ValueError, OSError):
            return error.code, {'ok': False, 'error_code': 'invalid_http_error_body'}, None


def response_errors(response, chunks):
    if not isinstance(response, dict) or response.get('ok') is not True:
        return ['request_failed']
    answer = response.get('answer')
    _valid, errors = validate_release_response(answer)
    errors = list(errors)
    for citation in answer.get('citations', []) if isinstance(answer, dict) else []:
        if not isinstance(citation, dict):
            continue
        chunk = chunks.get((citation.get('doc_id'), citation.get('chunk_id')))
        if chunk is None:
            errors.append('citation_missing_from_frozen_index')
            continue
        start, end = chunk.get('page_range', [chunk['page'], chunk['page']])
        if type(citation.get('page')) is not int or not start <= citation['page'] <= end:
            errors.append('citation_wrong_physical_page')
    return sorted(set(errors))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--benchmark', type=Path, required=True)
    parser.add_argument('--index', type=Path, required=True)
    parser.add_argument('--store', type=Path, required=True)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    parser.add_argument('--ids', help='Optional comma-separated dev subset; full runs omit this')
    parser.add_argument('--language', choices=['vi', 'en'], default='vi')
    parser.add_argument('--p95-limit', type=float, default=10.)
    parser.add_argument('--timeout-rate-limit', type=float, default=.005)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timings', type=Path, help='Numeric JSONL from the local launcher --timing-log')
    parser.add_argument('--variants', type=int, default=0, help='Additional polite variants; these remain exposed dev cases')
    parser.add_argument('--server-pid', type=int, help='Actual listening backend process for RSS sampling')
    parser.add_argument('--require-r01', action='store_true', help='Require 100 HTTP / 54 provider successes, p95, timeout and RSS gates')
    args = parser.parse_args(argv)
    parsed = urlsplit(args.base_url)
    if parsed.scheme != 'http' or parsed.hostname not in {'127.0.0.1', 'localhost', '::1'} or parsed.username or parsed.password:
        parser.error('local_loopback_endpoint_required')
    if args.output.exists():
        parser.error('output_exists_keep_previous_evidence')
    if args.require_r01 and (args.server_pid is None or args.timings is None):
        parser.error('r01_requires_server_pid_and_timings')
    if not 0 < args.p95_limit <= 210 or not 0 <= args.timeout_rate_limit <= 1:
        parser.error('invalid_latency_contract')
    with args.benchmark.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    if args.ids:
        wanted = set(args.ids.split(','))
        rows = [row for row in rows if row['id'] in wanted]
        if {row['id'] for row in rows} != wanted:
            parser.error('requested_case_missing')
    if not rows or len({row['id'] for row in rows}) != len(rows):
        parser.error('nonempty_unique_cases_required')
    try:
        rows += natural_variants(rows, args.variants, args.language)
    except ValueError as error:
        parser.error(str(error))
    status, library, _request_id = request_json(args.base_url, '/api/documents')
    if status != 200:
        parser.error('document_library_unavailable')
    selected = [doc for doc in library['documents'] if doc['ready']]
    doc_ids = sorted(doc['doc_id'] for doc in selected)
    if not doc_ids:
        parser.error('selected_sources_not_ready')
    chunks, sources = {}, []
    for doc in selected:
        payload = json.loads((args.index / doc['doc_id'] / 'bm25.json').read_text(encoding='utf-8'))
        for item in payload['items']:
            chunks[(doc['doc_id'], item['chunk_id'])] = item
        files = list((args.store / 'uploads' / doc['doc_id']).glob('*.pdf'))
        if len(files) != 1:
            parser.error('ambiguous_pdf_identity')
        sources.append({'doc_id': doc['doc_id'], 'name': files[0].name, 'sha256': digest(files[0])})
    source_identity = runtime_identity()
    profile = yaml.safe_load(args.profile.read_text(encoding='utf-8'))
    protocol = {'benchmark_sha256': digest(args.benchmark), 'ids': [row['id'] for row in rows],
        'started_at_utc': datetime.now(timezone.utc).isoformat(),
        'collector_sha256': digest(__file__),
        'expected_http_requests': sum(len(turns(row)) for row in rows),
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
        'runtime_files_sha256': source_identity, 'profile_sha256': digest(args.profile),
        'provider': profile['llm']['provider'], 'model': profile['llm']['model'],
        'index_manifest_sha256': digest(args.index / 'manifest.json'), 'sources': sources,
        'language': args.language, 'p95_limit_seconds': args.p95_limit,
        'timeout_rate_limit': args.timeout_rate_limit, 'client_retries': 0,
        'scope': 'exposed owner development set; not fresh holdout or independent quality approval',
        'cache_policy': 'application default; report cache hits separately; never clear quota or cache',
        'history_policy': 'actual prior user/assistant turns; no school/category/gold prefixes',
        'quality_review': 'pending source comparison; structural success is not semantic accuracy'}
    protocol['natural_variants'] = {'count': args.variants, 'algorithm': 'polite-preface-v1', 'independent_holdout': False}
    protocol['rss_limit_fraction'] = .75
    protocol['qualification_requirements'] = {'http_requests_min': 100, 'provider_inference_successes_min': 54,
        'required_for_exit_success': args.require_r01}
    encoded = json.dumps(protocol, sort_keys=True, ensure_ascii=True).encode()
    result = {'status': 'running', 'protocol': protocol,
        'protocol_sha256': hashlib.sha256(encoded).hexdigest(), 'predictions': []}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    save(args.output, result)
    memory, stop_monitor = rss_monitor(args.server_pid) if args.server_pid else ({}, lambda: None)
    stopped = False
    for row in rows:
        history = []
        for turn_number, question in enumerate(turns(row), 1):
            payload = inference_payload(question, doc_ids, history, args.language)
            started = time.perf_counter()
            prediction = {'id': row['id'], 'turn': turn_number, 'request': payload,
                'started_at_utc': datetime.now(timezone.utc).isoformat(),
                'prediction_kind': 'real_local_http', 'review_status': 'pending'}
            try:
                code, response, request_id = request_json(args.base_url, '/api/query', payload)
                prediction.update(http_status=code, response=response, request_id=request_id,
                    structural_errors=response_errors(response, chunks))
                response = response if isinstance(response, dict) else {}
                answer = response.get('answer', {})
                answer = answer if isinstance(answer, dict) else {}
                history += [{'role': 'user', 'content': question},
                            {'role': 'assistant', 'content': answer.get('answer', '')}]
                stopped = code != 200 or not response or bool(response.get('provider_status')) or bool(
                    str(response.get('error_code', '')).startswith('provider_'))
            except (URLError, TimeoutError, OSError, ValueError) as error:
                prediction.update(http_status=0, transport_error=type(error).__name__,
                    timeout=isinstance(error, TimeoutError) or isinstance(getattr(error, 'reason', None), TimeoutError),
                    structural_errors=['transport_error'])
                stopped = True
            prediction['elapsed_seconds'] = round(time.perf_counter() - started, 6)
            result['predictions'].append(prediction)
            save(args.output, result)
            print(json.dumps({'id': row['id'], 'turn': turn_number,
                'elapsed_seconds': prediction['elapsed_seconds'], 'errors': prediction['structural_errors']}), flush=True)
            if stopped:
                break
        if stopped:
            break
    predictions = result['predictions']
    stop_monitor()
    result['memory'] = memory
    if args.timings:
        traces = {row['request_id']: row for line in args.timings.read_text(encoding='utf-8').splitlines()
                  if (row := json.loads(line)).get('request_id')}
        for prediction in predictions:
            prediction['timing'] = traces.get(prediction.get('request_id'))
    changed = (source_identity != runtime_identity()
        or protocol['index_manifest_sha256'] != digest(args.index / 'manifest.json')
        or protocol['benchmark_sha256'] != digest(args.benchmark)
        or protocol['profile_sha256'] != digest(args.profile)
        or protocol['collector_sha256'] != digest(__file__))
    errors = sum(bool(p['structural_errors']) for p in predictions)
    timeouts = sum(p.get('timeout', False) or p.get('http_status') == 504 or
                   (isinstance(p.get('response'), dict) and (p['response'].get('error_code') == 'provider_timeout'
                    or p['response'].get('provider_status', {}).get('error_code') == 'provider_timeout'))
                   for p in predictions)
    summary = {'http_requests': len(predictions), 'expected_http_requests': protocol['expected_http_requests'],
        'complete': len(predictions) == protocol['expected_http_requests'] and not stopped,
        'structural_errors': errors, 'timeouts': timeouts,
        'p95_seconds': percentile([p['elapsed_seconds'] for p in predictions]),
        'cache_hits': sum(p.get('response', {}).get('cache_hit') is True for p in predictions),
        'source_changed_during_run': changed, 'semantic_quality': 'review_required'}
    summary['provider_inference_successes'] = sum(
        (p.get('timing') or {}).get('stage_calls', {}).get('provider_inference_success', 0) for p in predictions)
    summary['provider_model_versions'] = sorted({name.removeprefix('provider_model.') for p in predictions
        for name in (p.get('timing') or {}).get('stage_calls', {}) if name.startswith('provider_model.')})
    summary['peak_rss_fraction'] = (memory['peak_rss_bytes'] / memory['total_ram_bytes']
        if memory.get('peak_rss_bytes') and not memory.get('error') else None)
    summary['transport_pass'] = (summary['complete'] and not changed and errors == 0
        and summary['p95_seconds'] <= args.p95_limit and timeouts / len(predictions) <= args.timeout_rate_limit)
    summary['r01_pass'] = (summary['transport_pass'] and len(predictions) >= 100
        and summary['provider_inference_successes'] >= 54 and summary['peak_rss_fraction'] is not None
        and summary['peak_rss_fraction'] <= protocol['rss_limit_fraction'])
    result.update(status='complete' if not stopped else 'stopped', summary=summary)
    save(args.output, result)
    print(json.dumps(summary), flush=True)
    return 0 if (summary['r01_pass'] if args.require_r01 else summary['transport_pass']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
