"""Compare named-table candidate linkage on dev only; never emits a release PASS."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import sys
import time

from campusai.rag.context import benchmark_retrieval_request
from campusai.retrieval.calibration import RetrievalPolicy
from campusai.retrieval.hybrid import HybridRetriever
import campusai.retrieval.table_links as table_links
from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence
from evaluation.common.release_artifacts import sha256, source_identity, write_json
from evaluation.retrieval.evaluate_candidate_coverage import audit_outputs, coverage_errors

ROOT = Path(__file__).resolve().parents[2]


def dev_rows(path: Path) -> list[dict]:
    if path.name != 'human_retrieval_dev.jsonl':
        raise ValueError('only the explicit human dev split may be measured')
    rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    if not rows or any(row.get('split') != 'dev' for row in rows):
        raise ValueError('all inputs must be marked dev')
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dev', type=Path, required=True)
    parser.add_argument('--index-dir', type=Path, default=Path('.tmp/hybrid-index'))
    parser.add_argument('--phase6-calibration', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args(argv)
    rows = dev_rows(args.dev)
    if args.output_dir.exists():
        raise ValueError('use an absent study directory to preserve earlier evidence')
    evidence = frozen_evidence(args.index_dir)
    documents = sorted({doc for doc, _ in evidence})
    policy = RetrievalPolicy.from_report(args.phase6_calibration, expected_mode='hybrid_rrf')
    started = datetime.now(timezone.utc).isoformat()
    identity = source_identity(ROOT)
    original = table_links.linked_table_sources
    args.output_dir.mkdir(parents=True)
    parts = {}
    for label, enabled in [('existing_code_rows', False), ('named_curriculum_rows', True)]:
        def linked(query, records, cap, *, include_named_curriculum=False, named_exact_only=False):
            return original(query, records, cap,
                            include_named_curriculum=enabled and include_named_curriculum,
                            named_exact_only=named_exact_only)
        table_links.linked_table_sources = linked
        outputs = {}
        retriever = HybridRetriever(args.index_dir, query_cache_size=0, policies={'hybrid_rrf': policy})
        clock = time.perf_counter()
        try:
            for number, row in enumerate(rows, 1):
                values = retriever.generate_candidates(**benchmark_retrieval_request(row, documents),
                                                       top_k=40, mode='auto')
                outputs[row['qid']] = [value.to_dict() for value in values]
                if number % 50 == 0:
                    print(f'{label}: {number}/{len(rows)}', flush=True)
        finally:
            table_links.linked_table_sources = original
        metrics = audit_outputs(rows, outputs, documents, 40, evidence)
        raw = args.output_dir / (label + '.json.gz')
        with gzip.open(raw, 'wt', encoding='utf-8') as stream:
            json.dump(metrics, stream, ensure_ascii=False, allow_nan=False)
        compact = {key: value for key, value in metrics.items() if key not in {'per_query', 'candidate_misses'}}
        compact.update(raw_path=raw.name, raw_sha256=sha256(raw),
                       diagnostic_elapsed_seconds=time.perf_counter() - clock,
                       errors=coverage_errors(metrics, .95),
                       misses=[{'qid': item['qid'], 'expected_evidence': item['expected_evidence']}
                               for item in metrics['candidate_misses']])
        parts[label] = compact
    after = source_identity(ROOT)
    report = {'schema_version': 1, 'status': 'diagnostic', 'release_eligible': False,
              'purpose': 'dev-only candidate quality comparison; not M2 or latency acceptance',
              'command': sys.argv, 'started_at': started, 'ended_at': datetime.now(timezone.utc).isoformat(),
              'source_before': identity, 'source_after': after, 'source_stable': identity == after,
              'dataset_path': args.dev.as_posix(), 'dataset_sha256': sha256(args.dev),
              'index_sha256': sha256(args.index_dir / 'manifest.json'),
              'phase6_calibration_sha256': sha256(args.phase6_calibration), 'parts': parts}
    write_json(args.output_dir / 'comparison.json', report)
    print(json.dumps({label: {key: part[key] for key in ('records', 'answerable', 'all_gold_recall', 'errors')}
                      for label, part in parts.items()}, ensure_ascii=False, indent=2))
    return 0 if identity == after and not parts['named_curriculum_rows']['errors'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
