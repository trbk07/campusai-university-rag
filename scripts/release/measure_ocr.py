"""Freeze and measure a local OCR workload; never send PDF data to a provider."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]


def percentile(values, probability=.95):
    """Nearest rank; do not interpolate away a slow observation."""
    if not values or not 0 < probability <= 1:
        raise ValueError('nonempty_samples_and_valid_probability_required')
    return sorted(values)[math.ceil(len(values) * probability) - 1]


def sample(value):
    path, separator, selection = value.rpartition('::')
    try:
        pages = [int(item) for item in selection.split(',')]
        if not separator or not pages or min(pages) < 1 or len(set(pages)) != len(pages):
            raise ValueError
    except ValueError:
        raise argparse.ArgumentTypeError('Use PDF_PATH::1,2,3 with unique physical pages') from None
    return Path(path), pages


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    for attempt in range(10):
        try:
            temporary.replace(path)
            return
        except PermissionError as error:
            # Windows readers can briefly deny rename/delete sharing. Retry
            # only committing the already-written checkpoint, never inference.
            if getattr(error, 'winerror', None) not in {5,32,33} or attempt==9:
                raise
            time.sleep(.1)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sample', action='append', type=sample, required=True)
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--scale', type=float, default=1.5)
    parser.add_argument('--timeout', type=float, default=120.)
    parser.add_argument('--page-p95-limit', type=float, default=3.)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if (not 1 <= args.repeats <= 10 or not 0 < args.scale <= 4
            or not 0 < args.timeout <= 120 or not 0 < args.page_p95_limit <= 120):
        parser.error('invalid_measurement_limits')
    if args.output.exists():
        parser.error('output_exists_keep_previous_measurement')
    import pymupdf
    from campusai.ingestion.ocr import ocr_pdf
    from campusai.ingestion.ocr_assets import validate_tesseract_assets
    from campusai.ingestion import tesseract_process
    # This protocol measures per-page completion intervals, which are only
    # identifiable in a serial worker. Production throughput uses the bounded
    # parallel scheduler and must be reported separately as batch latency.
    tesseract_process._PAGE_WORKER_LIMIT = 1

    identity = validate_tesseract_assets(args.data_dir)
    sources = []
    for path, pages in args.sample:
        with pymupdf.open(path) as pdf:
            if len(pages) > 50 or max(pages) > len(pdf):
                parser.error('physical_page_out_of_scope')
        sources.append({'path': str(path), 'sha256': digest(path), 'pages': pages})
    tracked = ['src/campusai/ingestion/' + name + '.py' for name in
               ('ocr', 'ocr_assets', 'tesseract_process', 'tesseract_worker')]
    tracked += ['scripts/release/measure_ocr.py', 'uv.lock']
    protocol = {'sources': sources, 'repeats': args.repeats, 'backend': 'tesseract',
        'scale': args.scale, 'timeout_seconds': args.timeout, 'page_workers': 1,
        'page_p95_limit_seconds': args.page_p95_limit, 'model': identity,
        'quantile_method': 'nearest_rank',
        'timing_scope': 'page completion intervals; first page includes worker startup; batch includes cleanup',
        'cache_scope': 'OS/model file caches uncontrolled; a fresh isolated worker per batch; no answer cache',
        'python': sys.version.split()[0], 'platform': platform.platform(), 'logical_cpus': os.cpu_count(),
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
        'source_sha256': {name: digest(ROOT / name) for name in tracked}}
    encoded = json.dumps(protocol, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
    result = {'status': 'running', 'protocol': protocol,
        'protocol_sha256': hashlib.sha256(encoded).hexdigest(), 'batches': []}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    save(args.output, result)  # Freeze selection and thresholds before the first OCR call.
    for repetition in range(args.repeats):
        for source in sources:
            batch = {'source_sha256': source['sha256'], 'repetition': repetition + 1, 'pages': []}
            started = previous = time.perf_counter()
            completed_count = 0
            def progress(completed, total):
                nonlocal previous, completed_count
                if completed <= completed_count:
                    return
                if total != len(source['pages']) or completed != completed_count + 1:
                    raise ValueError('nonsequential_ocr_progress')
                now = time.perf_counter()
                batch['pages'].append({'page': source['pages'][completed - 1],
                    'elapsed_seconds': round(now - previous, 6)})
                previous, completed_count = now, completed
            try:
                if digest(source['path']) != source['sha256']:
                    raise ValueError('source_changed_after_freeze')
                # Hash validation above is not part of the OCR latency.
                started = previous = time.perf_counter()
                recognized = ocr_pdf(source['path'], page_numbers=source['pages'],
                    max_pages=50, timeout_seconds=args.timeout, scale=args.scale,
                    data_dir=args.data_dir, backend='tesseract', include_layout=True, progress=progress)
                if [row['page'] for row in recognized.pages] != source['pages']:
                    raise ValueError('physical_pages_mismatch')
                if len(batch['pages']) != len(source['pages']):
                    raise ValueError('incomplete_ocr_progress')
                batch['status'] = 'success'
                batch['text_characters'] = sum(len(row['text']) for row in recognized.pages)
                batch['engine_identity'] = recognized.model_identity
            except Exception as error:
                batch.update(status='error', error_type=type(error).__name__)
            batch['elapsed_seconds'] = round(time.perf_counter() - started, 6)
            result['batches'].append(batch)
            save(args.output, result)
    durations = [page['elapsed_seconds'] for batch in result['batches'] for page in batch['pages']]
    errors = sum(batch['status'] != 'success' for batch in result['batches'])
    summary = {'batches': len(result['batches']), 'page_observations': len(durations), 'errors': errors,
        'p95_page_seconds': percentile(durations) if durations else None,
        'p95_batch_seconds': percentile([b['elapsed_seconds'] for b in result['batches']]),
        'expected_observations': args.repeats * sum(len(s['pages']) for s in sources)}
    summary['performance_pass'] = (errors == 0 and len(durations) == summary['expected_observations']
        and summary['p95_page_seconds'] <= args.page_p95_limit
        and max(b['elapsed_seconds'] for b in result['batches']) <= args.timeout)
    result.update(status='complete', summary=summary)
    save(args.output, result)
    print(json.dumps(summary, allow_nan=False))
    return 0 if summary['performance_pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
