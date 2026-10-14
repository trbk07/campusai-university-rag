"""Owner-mediated Chat quality collection; no API, no live latency claims."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

from jsonschema import Draft202012Validator

from evaluation.common.release_artifacts import read_json, sha256, source_identity, write_json
from scripts.benchmarks import product_primary as primary

ROOT = primary.ROOT
OUTPUT = ROOT / 'evaluation/phase7/chat-quality-20261013'
RAW = ROOT / '.local_artifacts/experiment_runs/phase7-chat-quality-20261013'
INSTRUCTIONS = """Hãy xử lý từng INPUT độc lập, chỉ dùng nguồn trong prompt của INPUT đó.
Không dùng web, kiến thức ngoài hoặc dữ liệu của INPUT khác. Không bỏ sót INPUT.
Thực hiện đúng yêu cầu và JSON Schema riêng của từng INPUT; không suy đoán khi
thiếu bằng chứng. Không rút gọn câu trả lời chỉ để vừa giới hạn đầu ra.
Trả về JSONL: mỗi dòng là {"case_id":"ID", "response":{...}}.
Giữ nguyên case_id. response phải tuân thủ schema tương ứng, gồm citation và claims
nếu schema yêu cầu. Escape dấu nháy/ký tự xuống dòng trong quote để JSON parse được.
Nếu có công cụ tạo file, hãy dùng JSON serializer và xuất một file UTF-8 .jsonl.
Nếu bị giới hạn đầu ra, dừng ở cuối một record hoàn chỉnh, ghi riêng ID chưa xử lý;
không đánh dấu câu bị cắt là hoàn tất. Không thêm đáp án hay giải thích ngoài JSONL.
"""


def within(path):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError('output must stay inside the project')
    return path


def collect_cases(packet):
    """Use opaque IDs; exported inputs contain no arm labels, gold or rubric."""
    cases = []
    for step in packet['schedule']:
        arm, qid = step['arm'], step['qid']
        case = packet['cases'][arm][qid]
        body = case['provider_body']
        if not body:
            continue
        prompt = body['contents'][0]['parts'][0]['text']
        schema = body['generationConfig']['responseSchema']
        cases.append({'case_id': f'p7-chat-{len(cases)+1:03}', 'arm': arm, 'qid': qid,
            'prompt': prompt, 'schema': schema, 'body_sha256': digest_body(body)})
    return cases


def digest_body(body):
    import hashlib
    return hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def export(packet_path, output=OUTPUT, max_cases=24):
    packet_path, output = Path(packet_path).resolve(), within(output)
    if output.exists() or not 1 <= max_cases <= 24:
        raise ValueError('export already exists or batch exceeds 24 cases')
    packet = read_json(packet_path)
    primary.validate_packet(packet)
    if packet['source_identity'] != source_identity(ROOT):
        raise ValueError('prepared source drift; do not export stale inputs')
    cases = collect_cases(packet)
    if len(cases) != packet['max_provider_calls']:
        raise ValueError('generation cohort incomplete')
    output.mkdir(parents=True)
    batches = []
    for offset in range(0, len(cases), max_cases):
        selected = cases[offset:offset + max_cases]
        path = output / f'batch-{len(batches)+1:02}.md'
        text = '# Gemini Chat quality inputs\n\n' + INSTRUCTIONS + '\n'
        text += f'INPUT count: {len(selected)}.\n\n'
        for case in selected:
            visible = {key: case[key] for key in ('case_id', 'prompt', 'schema')}
            text += '```json\n' + json.dumps(visible, ensure_ascii=False, indent=2) + '\n```\n\n'
        path.write_text(text, encoding='utf-8', newline='\n')
        batches.append({'path': path.relative_to(ROOT).as_posix(), 'sha256': sha256(path),
                        'case_ids': [case['case_id'] for case in selected], 'count': len(selected)})
    manifest = {'schema_version': 1, 'status': 'EXPORTED_NO_CHAT_OUTPUTS',
        'prepared_at': datetime.now(timezone.utc).isoformat(), 'source_identity': packet['source_identity'],
        'authority': 'Owner explicitly requested Phase 7 quality verification through Gemini Chat.',
        'mode': 'OWNER_MEDIATED_CHAT_NOT_LIVE_API', 'external_api_calls': 0,
        'billing_changes': False, 'model_ui_selection_requested': 'Gemini 3.8 Flash',
        'actual_chat_model_identity': 'Unverified; collect UI label/settings with outputs if available.',
        'paired_packet': {'path': packet_path.relative_to(ROOT).as_posix(), 'sha256': sha256(packet_path)},
        'rubric': packet['rubric'], 'thresholds_unchanged': True,
        'rows': len(packet['rows']), 'split_counts': dict(Counter(r['split'] for r in packet['rows'])),
        'model_inputs': len(cases), 'model_inputs_by_arm': dict(Counter(c['arm'] for c in cases)),
        'local_responses_by_arm': {a: sum(not c['provider_body'] for c in cc.values()) for a, cc in packet['cases'].items()},
        'batches': batches,
        'case_map': [{k: v for k, v in c.items() if k not in {'prompt', 'schema'}} for c in cases],
        'quality_accepted': False, 'fresh_validation': False,
        'limitations': ['Previously exposed 35 test / 33 holdout; not fresh validation.',
            'Chat generation settings/model identity are not API-verified.',
            'Chat content and recorded replay cannot qualify API latency, availability or live integrations.',
            'Outputs require source review and actual application replay before acceptance.']}
    write_json(output / 'manifest.json', manifest)
    return manifest


def load_export(output=OUTPUT):
    output = within(output)
    manifest = read_json(output / 'manifest.json')
    packet_path = ROOT / manifest['paired_packet']['path']
    if sha256(packet_path) != manifest['paired_packet']['sha256']:
        raise ValueError('paired preparation changed')
    packet = read_json(packet_path)
    if sha256(Path(manifest['rubric']['path'])) != manifest['rubric']['sha256']:
        raise ValueError('frozen source rubric changed')
    for batch in manifest['batches']:
        if sha256(ROOT / batch['path']) != batch['sha256']:
            raise ValueError('exported batch changed')
    return manifest, packet, {c['case_id']: c for c in collect_cases(packet)}


def json_schema(schema):
    """Translate Gemini's uppercase type spelling, without changing constraints."""
    if isinstance(schema, list):
        return [json_schema(item) for item in schema]
    if not isinstance(schema, dict):
        return schema
    result = {key: json_schema(value) for key, value in schema.items()}
    if isinstance(result.get('type'), str):
        result['type'] = result['type'].lower()
    elif isinstance(result.get('type'), list):
        result['type'] = [value.lower() if isinstance(value, str) else value
                          for value in result['type']]
    return result


def validate_records(text, cases, expected):
    records, issues, seen = [], [], set()
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            issues.append({'line': number, 'issue': 'invalid_json_no_automatic_repair'})
            continue
        if not isinstance(row, dict) or set(row) != {'case_id', 'response'}:
            issues.append({'line': number, 'issue': 'invalid_record_wrapper'})
            continue
        identifier = row['case_id']
        if not isinstance(identifier, str) or identifier not in expected or identifier in seen:
            issues.append({'line': number, 'issue': 'unknown_extra_or_duplicate_case_id'})
            continue
        seen.add(identifier)
        schema = json_schema(cases[identifier]['schema'])
        Draft202012Validator.check_schema(schema)
        errors = list(Draft202012Validator(schema).iter_errors(row['response']))
        if errors:
            issues.append({'case_id': identifier, 'issue': 'response_schema_invalid',
                           'schema_paths': [list(e.absolute_schema_path) for e in errors]})
            continue
        case = cases[identifier]
        records.append({'case_id': identifier, 'arm': case['arm'], 'qid': case['qid'],
                        'response': row['response'], 'body_sha256': case['body_sha256']})
    missing = sorted(set(expected) - {r['case_id'] for r in records})
    return records, issues, missing


def import_batch(input_path, batch_number, output=OUTPUT, received_dir=None):
    output = within(output)
    manifest, _packet, cases = load_export(output)
    if not 1 <= batch_number <= len(manifest['batches']):
        raise ValueError('unknown batch')
    # Preserve original bytes even when parsing fails; never silently fix quotes.
    target = within(received_dir or RAW) / f'batch-{batch_number:02}-received'
    target.mkdir(parents=True, exist_ok=False)
    raw = target / 'raw.txt'
    raw.write_bytes(Path(input_path).read_bytes())
    records, issues, missing = validate_records(raw.read_text(encoding='utf-8-sig'), cases,
                                               manifest['batches'][batch_number-1]['case_ids'])
    report = {'status': 'SCHEMA_COMPLETE_PENDING_SOURCE_REVIEW' if not issues and not missing else 'INCOMPLETE_OR_INVALID',
        'batch': batch_number, 'raw': {'path': raw.relative_to(ROOT).as_posix(), 'sha256': sha256(raw)},
        'export_manifest_sha256': sha256(output / 'manifest.json'),
        'responses': records, 'issues': issues, 'missing_case_ids': missing,
        'normalization_or_repair': False, 'quality_accepted': False,
        'actual_chat_model_identity': 'Owner-mediated; not verified by API metadata.'}
    write_json(target / 'validation.json', report)
    return report


def import_combined(input_path, output=OUTPUT):
    """Retain a combined submission and partition its exact lines by opaque ID."""
    manifest, _packet, cases = load_export(output)
    target = RAW / 'combined-received'
    target.mkdir(parents=True, exist_ok=False)
    raw = target / 'raw.txt'
    raw.write_bytes(Path(input_path).read_bytes())
    records, issues, missing = validate_records(raw.read_text(encoding='utf-8-sig'), cases, list(cases))
    report = {'status': 'SCHEMA_COMPLETE_PENDING_SOURCE_REVIEW' if not issues and not missing else 'INCOMPLETE_OR_INVALID',
        'raw': {'path': raw.relative_to(ROOT).as_posix(), 'sha256': sha256(raw)},
        'export_manifest_sha256': sha256(Path(output) / 'manifest.json'),
        'received_dir': target.relative_to(ROOT).as_posix(), 'valid_records': len(records),
        'issues': issues, 'missing_case_ids': missing, 'normalization_or_repair': False,
        'quality_accepted': False}
    if not issues and not missing:
        lines = {}
        for line in raw.read_bytes().splitlines(keepends=True):
            if line.strip():
                lines[json.loads(line.decode('utf-8-sig'))['case_id']] = line
        report['partitions'] = []
        for number, batch in enumerate(manifest['batches'], 1):
            part = target / f'batch-{number:02}-submitted.jsonl'
            part.write_bytes(b''.join(lines[identifier] for identifier in batch['case_ids']))
            result = import_batch(part, number, output, received_dir=target)
            report['partitions'].append({'batch': number, 'records': len(result['responses']),
                'path': part.relative_to(ROOT).as_posix(), 'sha256': sha256(part)})
    write_json(target / 'intake.json', report)
    return report


def replay(output=OUTPUT, received_dir=None):
    output = within(output)
    manifest, packet, cases = load_export(output)
    if source_identity(ROOT) != manifest['source_identity']:
        raise ValueError('source changed after Chat preparation')
    received_dir = within(received_dir or RAW)
    responses = []
    for number in range(1, len(manifest['batches'])+1):
        path = received_dir / f'batch-{number:02}-received/validation.json'
        report = read_json(path)
        if (report['status'] != 'SCHEMA_COMPLETE_PENDING_SOURCE_REVIEW'
                or report['export_manifest_sha256'] != sha256(output / 'manifest.json')
                or sha256(ROOT / report['raw']['path']) != report['raw']['sha256']):
            raise ValueError('Chat input incomplete, invalid or changed; no replay')
        # Reparse immutable raw input rather than trusting an edited validation report.
        rows, issues, missing = validate_records((ROOT / report['raw']['path']).read_text(encoding='utf-8-sig'),
                                                 cases, manifest['batches'][number-1]['case_ids'])
        if issues or missing or rows != report['responses']:
            raise ValueError('validated Chat responses changed')
        responses.extend(rows)
    folder = received_dir / 'recorded-replay'
    if folder.exists():
        attempt = 2
        while (received_dir / f'recorded-replay-{attempt}').exists():
            attempt += 1
        folder = received_dir / f'recorded-replay-{attempt}'
    folder.mkdir(parents=True, exist_ok=False)
    response_file = folder / 'responses.json'
    write_json(response_file, {'responses': responses, 'mode': manifest['mode']})
    setup = dict(packet, recorded_chat={'path': str(response_file), 'sha256': sha256(response_file)})
    setup_path = folder / 'setup.json'
    write_json(setup_path, setup)
    reports = {}
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    env.pop('GEMINI_API_KEY', None)
    for arm in ('baseline', 'current'):
        path = folder / (arm + '.json')
        run = subprocess.run([sys.executable, str(primary.WORKER), 'recorded', arm, str(setup_path), str(path)],
                             capture_output=True, text=True, encoding='utf-8', env=env)
        (folder / (arm + '.log')).write_text(run.stdout + run.stderr, encoding='utf-8')
        report = read_json(path)
        if run.returncode or report['external_provider_calls'] or len(report['observations']) != 68:
            raise ValueError('recorded application replay incomplete; retain failure evidence')
        reports[arm] = {'path': path.relative_to(ROOT).as_posix(), 'sha256': sha256(path), 'observations': 68}
    receipt = {'status': 'RECORDED_CHAT_REPLAY_COMPLETE_PENDING_SOURCE_REVIEW',
        'arms': reports, 'pairs': 68, 'external_api_calls': 0, 'quality_accepted': False,
        'live_latency_measured': False, 'chat_manifest_sha256': sha256(output / 'manifest.json')}
    write_json(output / 'replay-receipt.json', receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['export', 'import', 'replay'])
    parser.add_argument('--packet', type=Path, default=RAW / 'paired-preflight.json')
    parser.add_argument('--input', type=Path)
    parser.add_argument('--batch', type=int)
    parser.add_argument('--received-dir', type=Path)
    parser.add_argument('--export-dir', type=Path, default=OUTPUT)
    args = parser.parse_args()
    if args.action == 'export':
        result = export(args.packet, args.export_dir)
        print(json.dumps({k: result[k] for k in ('status', 'model_inputs', 'model_inputs_by_arm', 'batches')}, indent=2))
    elif args.action == 'import':
        if args.input is None:
            parser.error('import requires --input; omit --batch for a combined submission')
        result = import_batch(args.input, args.batch, args.export_dir) if args.batch is not None else import_combined(args.input, args.export_dir)
        print(json.dumps({k: result[k] for k in ('status', 'issues', 'missing_case_ids')}))
    else:
        print(json.dumps(replay(args.export_dir, received_dir=args.received_dir), indent=2))


if __name__ == '__main__':
    main()
