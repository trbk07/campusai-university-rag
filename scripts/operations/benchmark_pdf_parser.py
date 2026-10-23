"""Local-only PDF parser latency/RSS measurement; never calls a model provider."""
from concurrent.futures import ThreadPoolExecutor
import argparse
import hashlib
import json
from pathlib import Path
import threading
import time

import psutil
from campusai.ingestion.docling_parser import parse_pdf


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdfs', nargs='+', type=Path)
    parser.add_argument('--workers', type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.workers <= 5:
        parser.error('workers must be between 1 and 5')
    process = psutil.Process()
    initial = process.memory_info().rss
    samples = [initial]
    stop = threading.Event()
    def sample():
        while not stop.wait(.01):
            samples.append(process.memory_info().rss)
    sampler = threading.Thread(target=sample, daemon=True)
    sampler.start()
    started = time.perf_counter()
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            results = list(pool.map(parse_pdf, args.pdfs))
        elapsed = time.perf_counter() - started
    finally:
        stop.set(); sampler.join()
    print(json.dumps({'workers': args.workers, 'seconds': round(elapsed, 4),
        'initial_rss_bytes': initial, 'peak_sampled_rss_bytes': max(samples),
        'documents': [{'name': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'bytes': path.stat().st_size, 'pages': len(pages),
            'text_characters': sum(len(page['text']) for page in pages)}
            for path, pages in zip(args.pdfs, results)]}))


if __name__ == '__main__':
    main()
