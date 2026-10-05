"""Bind source proposals to real PDF bytes, physical index and historical datasets."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence
from evaluation.benchmarks.source_proposals import history_inventory, screen_source_facts
from evaluation.common.release_artifacts import read_json, sha256, verify_index_files, write_json


def audit(index: Path, source_manifest: Path, history_dirs: list[Path], output: Path) -> dict:
    if output.exists():
        raise ValueError('preserve historical audits; choose an absent output path')
    if not history_dirs or any(not path.is_dir() for path in history_dirs):
        raise ValueError('every historical dataset directory must exist')
    if not verify_index_files(index):
        raise ValueError('physical index verification failed')
    evidence = frozen_evidence(index)
    manifest = read_json(source_manifest)
    documents = set()
    for entry in manifest['documents']:
        pdf = source_manifest.parent/entry['filename']
        if sha256(pdf) != entry['sha256']:
            raise ValueError('source PDF bytes changed: ' + entry['filename'])
        if entry['status'] == 'succeeded':
            doc = entry['doc_id']
            if doc != entry['sha256'] or not any(key[0] == doc for key in evidence):
                raise ValueError('source document is not physically indexed')
            documents.add(doc)
        elif any(key[0] == entry['doc_id'] for key in evidence):
            raise ValueError('excluded source document was included in the index')
    questions, datasets = history_inventory(history_dirs)
    before = {item['path']: item['sha256'] for item in datasets}
    report = screen_source_facts(evidence, documents, questions)
    if any(sha256(path) != digest for path, digest in before.items()):
        raise ValueError('historical dataset changed during source audit')
    report.update(schema_version=1, recorded_at=datetime.now(timezone.utc).isoformat(),
                  source_manifest_sha256=sha256(source_manifest),
                  index_sha256=sha256(index/'manifest.json'),
                  source_documents=sorted(documents), history_datasets=datasets,
                  history_question_occurrences=len(questions),
                  history_directory_inventory_complete=True,
                  history_semantic_approval_complete=False)
    write_json(output, report)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index-dir', type=Path, required=True)
    parser.add_argument('--source-manifest', type=Path, required=True)
    parser.add_argument('--history-dir', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    report = audit(args.index_dir, args.source_manifest, args.history_dir, args.output)
    print(json.dumps({key: report[key] for key in ('status', 'explicit_course_rows', 'proposed_rows',
                     'proposed_connected_groups', 'history_question_occurrences', 'index_sha256')}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
