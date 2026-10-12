"""Zero-network WSGI regression with recorded owner-mediated Chat responses.

Measures application processing with instant recorded model output, never live
provider latency. Frozen inputs and raw Chat failures remain immutable evidence.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time
from unittest.mock import patch

import psutil

from campusai.web import make_wsgi_app
from evaluation.common.release_artifacts import source_identity
from evaluation.phase8.prepare_product_run import _NoCache, _request
from evaluation.phase8.score_temporal_product_outputs import _index_tree_sha256, _load_index

ROOT = Path(__file__).resolve().parents[2]
BENCHMARK = ROOT / 'evaluation/phase8/benchmark_candidate_v5.jsonl'
PREFLIGHT = ROOT / 'evaluation/results/phase8-product-preflight-v5.json'
CHAT = ROOT / 'evaluation/results/phase8-gemini-chat-responses-v5.jsonl'
SUMMARY = ROOT / 'evaluation/results/phase8-gemini-chat-content-summary-v5.json'
INDEX = ROOT / '.tmp/hybrid-index'
DEFAULT_OUTPUT = ROOT / 'evaluation/results/phase8-chat-replay-baseline-20261012'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8-sig').splitlines() if line.strip()]


def write_json(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def correct_annotations(rows, index):
    """Source-check semester labels without reading any model response."""
    corrected = deepcopy(rows)
    changes = []
    for row in corrected:
        if not row.get('answerable') or '-semester-' not in row['qid']:
            continue
        expected = row['expected_claims'][0]
        fact = row['source_validation']['facts'][0]
        source = index[(fact['doc_id'], fact['chunk_id'])]
        table = json.loads(source.content[source.content.index('{"headers"'):])
        cells = table['rows'][fact['table_row']]
        digest = hashlib.sha256(json.dumps({'cells': cells}, ensure_ascii=False,
            sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        if digest != fact['cells_sha256'] or cells[1] != expected['course_name']:
            raise ValueError('source row binding mismatch: ' + row['qid'])
        semester = None
        for preceding in table['rows'][:fact['table_row'] + 1]:
            for cell in preceding:
                match = re.fullmatch(r'\s*Semester\s*(\d+)\s*', cell)
                if match:
                    semester = int(match[1])
        if semester != expected['semester'] or int(cells[2]) != expected['credits']:
            raise ValueError('semester/credits disagree with source: ' + row['qid'])
        text = f"{expected['course_name']} is listed in semester {semester}."
        before = row['gold_claims'][0]['text']
        if text != before:
            row['gold_claims'][0]['text'] = text
            changes.append({'qid': row['qid'], 'before': before, 'after': text,
                'proof': {'doc_id': fact['doc_id'], 'chunk_id': fact['chunk_id'],
                    'page': source.page, 'table_row': fact['table_row'],
                    'cells_sha256': digest, 'semester_from_preceding_heading': semester}})
    return corrected, changes


class ChatReplay:
    model = 'recorded-owner-chat-output'
    generation_config = {}

    def __init__(self, outputs):
        self.outputs = outputs
        self.current = None
        self.calls = 0

    def generate_json(self, prompt, schema=None, **_options):
        case = self.current
        if not case or prompt != case['prompt'] or schema != case['schema']:
            raise ValueError('recorded Chat input differs from actual application prompt/schema')
        self.calls += 1
        if self.calls != 1:
            raise ValueError('unexpected multiple model calls for one case')
        return deepcopy(self.outputs[case['qid']]['response'])

    def close(self):
        pass


def load_reviewed_inputs(preflight_path=PREFLIGHT, chat_path=CHAT, summary_path=SUMMARY):
    paths = [Path(path).resolve() for path in (preflight_path, chat_path, summary_path)]
    if any(not path.is_relative_to(ROOT) for path in paths):
        raise ValueError('reviewed inputs must stay within the project')
    preflight_path, chat_path, summary_path = paths
    packet = json.loads(preflight_path.read_text(encoding='utf-8-sig'))
    summary = json.loads(summary_path.read_text(encoding='utf-8'))
    for path in (preflight_path, chat_path, BENCHMARK):
        if summary['bindings'].get(path.relative_to(ROOT).as_posix()) != sha(path):
            raise ValueError('selected input is not bound by content review: ' + path.name)
    for path, digest in summary['bindings'].items():
        bound = (ROOT / path).resolve()
        if not bound.is_relative_to(ROOT) or sha(bound) != digest:
            raise ValueError('Chat review binding changed: ' + path)
    if sha(BENCHMARK) != packet['benchmark']['sha256']:
        raise ValueError('frozen benchmark changed')
    rows = read_rows(BENCHMARK)
    if [case['qid'] for case in packet['cases']] != [row['qid'] for row in rows]:
        raise ValueError('preflight benchmark population/order changed')
    raw_outputs = read_rows(chat_path)
    outputs = {row['qid']: row for row in raw_outputs}
    labels = {row['qid']: row for row in summary['cases']}
    expected = {case['qid'] for case in packet['cases'] if case['planned_provider_call']}
    if (len(outputs) != len(raw_outputs) or set(outputs) != expected
            or len(labels) != len(summary['cases']) or set(labels) != expected):
        raise ValueError('Chat generation/review cohort mismatch')
    if any(row['decision'] != 'ACCEPT_CONTENT' for row in labels.values()):
        raise ValueError('unaccepted Chat content cannot enter accepted replay')
    return packet, rows, outputs, summary


def run(output=DEFAULT_OUTPUT, *, preflight_path=PREFLIGHT, chat_path=CHAT, summary_path=SUMMARY):
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT) or output.exists():
        raise ValueError('output must be a new directory within the project')
    preflight_path, chat_path, summary_path = [Path(path).resolve()
        for path in (preflight_path, chat_path, summary_path)]
    packet, rows, outputs, _summary = load_reviewed_inputs(preflight_path, chat_path, summary_path)
    if _index_tree_sha256(INDEX) != packet['index']['tree_sha256']:
        raise ValueError('original retrieval index changed')
    corrected, changes = correct_annotations(rows, _load_index(INDEX))
    output.mkdir(parents=True)
    corrected_path = output / 'benchmark-scoring-annotations.jsonl'
    corrected_path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in corrected), encoding='utf-8')
    write_json(output / 'annotation-corrections.json', {'status': 'SOURCE_VERIFIED_SCORING_OVERLAY',
        'frozen_benchmark_sha256': sha(BENCHMARK), 'scoring_benchmark_sha256': sha(corrected_path),
        'reviewer': 'Codex - Automated AI Source Review', 'changes': changes,
        'policy': 'Only derived semester claim text changes. Questions, qids, structured gold, evidence, splits and thresholds unchanged. Exposed regression; original frozen file preserved.'})
    profile = dict(packet['profile'])
    profile['CAMPUSAI_STORE_DIR'] = str(ROOT / '.tmp/phase8-chat-replay-store')
    client = ChatReplay(outputs)
    before = source_identity(ROOT)
    started_at = datetime.now(timezone.utc).isoformat()
    predictions = []
    peak = 0
    startup_ms = 0
    def deny_network(*_args, **_kwargs):
        raise RuntimeError('network disabled: owner Chat replay, no API calls allowed')
    from scripts.operations.serve import build_application
    with patch.dict(os.environ, profile), \
            patch('scripts.operations.serve.create_llm', return_value=client), \
            patch('urllib.request.urlopen', side_effect=deny_network), \
            patch('socket.create_connection', side_effect=deny_network), \
            patch('socket.socket.connect', side_effect=deny_network):
        import torch
        torch.set_num_threads(8)
        started = time.perf_counter()
        app = build_application()
        startup_ms = (time.perf_counter() - started) * 1000
        try:
            service = app.query_service
            service.cache.close()
            service.cache = _NoCache()
            service.retriever.query_cache_size = 0
            captured = []
            ask = service.ask
            def capture(*args, **kwargs):
                answer = ask(*args, **kwargs)
                captured.append(answer.to_dict())
                return answer
            service.ask = capture
            web = make_wsgi_app(app)
            with (output / 'predictions.jsonl').open('x', encoding='utf-8') as stream:
                for number, case in enumerate(packet['cases']):
                    client.current = case
                    client.calls = 0
                    captured.clear()
                    started = time.perf_counter()
                    status, response = _request(web, case['request'])
                    elapsed = (time.perf_counter() - started) * 1000
                    if status != '200 OK' or response.get('ok') is not True or len(captured) != 1:
                        raise ValueError('WSGI capture failed: ' + case['qid'])
                    if client.calls != int(case['planned_provider_call']):
                        raise ValueError('application routing changed: ' + case['qid'])
                    pred = {'qid': case['qid'], 'internal_response': captured[0],
                        'public_response': response['answer'], 'retrieved_evidence': [x.to_dict() for x in service.last_retrieval],
                        'mode': 'recorded_chat_replay' if client.calls else 'actual_local_branch',
                        'normalization_applied_to_chat_input': outputs[case['qid']]['normalization_applied'] if client.calls else False,
                        'request_latency_ms': round(elapsed, 3), 'cold_start': number == 0,
                        'startup_ms': round(startup_ms if number == 0 else 0, 3),
                        'latency_ms': round(elapsed + (startup_ms if number == 0 else 0), 3),
                        'runtime_id': 'phase8-recorded-chat-replay-20261012'}
                    predictions.append(pred)
                    stream.write(json.dumps(pred, ensure_ascii=False) + '\n')
                    stream.flush()
                    memory = psutil.Process().memory_info()
                    peak = max(peak, getattr(memory, 'peak_wset', memory.rss))
                    if (number + 1) % 25 == 0:
                        print(json.dumps({'completed': number + 1, 'total': len(rows), 'api_calls': 0}), flush=True)
        finally:
            app.close()
    if source_identity(ROOT) != before:
        raise ValueError('source drift during recorded Chat replay')
    if _index_tree_sha256(INDEX) != packet['index']['tree_sha256']:
        raise ValueError('index drift during replay')
    receipt = {'schema_version': 1, 'status': 'completed', 'mode': 'RECORDED_CHAT_WSGI_REPLAY_NOT_LIVE_PROVIDER',
        'started_at': started_at, 'completed_at': datetime.now(timezone.utc).isoformat(),
        'requests': len(predictions), 'local_requests': sum(p['mode'] == 'actual_local_branch' for p in predictions),
        'chat_replay_requests': sum(p['mode'] == 'recorded_chat_replay' for p in predictions),
        'source_identity': before, 'profile': profile, 'peak_working_set_bytes': peak,
        'measurement_method': 'OS process peak_wset (RSS fallback). WSGI request timing; cold includes app startup. Recorded Chat output returns instantly: these are local processing timings, NEVER live-provider or end-user Chat latency.',
        'provider_requests_sent': 0, 'network_disabled': True, 'phase8_pass': False,
        'bindings': {'benchmark_sha256': sha(corrected_path), 'predictions_sha256': sha(output / 'predictions.jsonl'),
            'index_manifest_sha256': sha(INDEX / 'manifest.json'), 'index_tree_sha256': _index_tree_sha256(INDEX),
            'original_frozen_benchmark_sha256': sha(BENCHMARK), 'recorded_chat_sha256': sha(chat_path),
            'original_preflight_sha256': sha(preflight_path), 'chat_review_summary_sha256': sha(summary_path),
            'llm_config_sha256': sha(ROOT / 'configs/product_llm.yaml')},
        'reviewed_inputs': {'preflight': preflight_path.relative_to(ROOT).as_posix(),
            'chat': chat_path.relative_to(ROOT).as_posix(), 'summary': summary_path.relative_to(ROOT).as_posix()}}
    write_json(output / 'execution.json', receipt)
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--preflight', type=Path, default=PREFLIGHT)
    parser.add_argument('--chat', type=Path, default=CHAT)
    parser.add_argument('--summary', type=Path, default=SUMMARY)
    args = parser.parse_args()
    receipt = run(args.output_dir, preflight_path=args.preflight, chat_path=args.chat, summary_path=args.summary)
    print(json.dumps({key: receipt[key] for key in ['status', 'requests', 'local_requests', 'chat_replay_requests', 'provider_requests_sent']}, indent=2))
