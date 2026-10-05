"""Prepare exactly validated legacy records as successor dev material, without a freeze."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path

from evaluation.benchmarks.dev_inheritance import (
    consumed_candidate_rows, file_bindings, inheritance_audit, rows_at, validate_inheritance,
)
from evaluation.common.release_artifacts import read_json, sha256, write_json

ROOT=Path(__file__).resolve().parents[2]


def prepare(source: Path, old_index: Path, new_index: Path, report: Path,
            extension: Path, destination: Path, *, root: Path=ROOT) -> dict:
    if destination.exists():
        raise ValueError('retain prior preparation; choose an absent destination')
    config=read_json(root/'configs/phase7_release_cycle.json')
    if (root/config['benchmark_dir']).resolve() != source.resolve():
        raise ValueError('source must be the active consumed benchmark cycle')
    relative=lambda path:path.resolve().relative_to(root.resolve()).as_posix()
    policy=read_json(source/'phase7_review_policy.json')
    parents=[]
    consumed=consumed_candidate_rows(source,report,sha256(old_index/'manifest.json'))
    parents.append({'mode':'consumed_candidate_splits','benchmark_dir':relative(source),
        'index_dir':relative(old_index),'benchmark_files':file_bindings(source),
        'index_files':file_bindings(old_index),'candidate_report':relative(report),
        'candidate_report_sha256':sha256(report),'qids':sorted(row['qid'] for row in consumed)})
    extras=[row for row in rows_at(extension/'human_retrieval_dev.jsonl')
            if row.get('source_validation',{}).get('kind')=='dev_absent_field']
    parents.append({'mode':'dev_only_absent_fields','benchmark_dir':relative(extension),
        'index_dir':relative(old_index),'benchmark_files':file_bindings(extension),
        'index_files':file_bindings(old_index),'qids':sorted(row['qid'] for row in extras)})
    manifest={'schema_version':1,'status':'validated_dev_inheritance','release_eligible':False,
        'profile':'legacy_source_checked_dev_inheritance_v1','recorded_at':datetime.now(timezone.utc).isoformat(),
        'owner_identity':policy['owner_identity'],'dev_only':True,'new_heldout_claim':False,
        'index_sha256':sha256(new_index/'manifest.json'),'records':len(consumed)+len(extras),'parents':parents,
        'meaning':'Preserve original review, author/AI origin, authorization timestamps and source index bindings. Only split changes to dev after exact exposure/origin checks; no fresh questions or heldout eligibility.'}
    bundle=validate_inheritance(manifest,new_index,policy,root=root)
    rows=list(bundle['rows'].values())
    destination.mkdir(parents=True)
    write_json(destination/'phase7_dev_inheritance.json',manifest)
    for filename,records in [('inherited_dev_records.jsonl',rows),('inherited_review_audit.jsonl',inheritance_audit(bundle))]:
        (destination/filename).write_text(''.join(json.dumps(row,ensure_ascii=False,sort_keys=True)+'\n' for row in records),encoding='utf8')
    summary={'schema_version':1,'status':'validated_dev_inheritance','release_eligible':False,
        'dev_only':True,'new_heldout_claim':False,'records':len(rows),'consumed_cycle_records':len(consumed),
        'previous_dev_only_absence_records':len(extras),'authorship_counts':dict(Counter(row['author_type'] for row in rows)),
        'original_split_counts':dict(Counter(origin['original_split'] for origin in bundle['origins'].values())),
        'current_split_counts':dict(Counter(row['split'] for row in rows)),
        'manifest_sha256':sha256(destination/'phase7_dev_inheritance.json'),
        'records_sha256':sha256(destination/'inherited_dev_records.jsonl'),
        'audit_sha256':sha256(destination/'inherited_review_audit.jsonl'),
        'historical_authorizations_validated':len(bundle['authorizations']),
        'old_index_sha256':sha256(old_index/'manifest.json'),'new_index_sha256':sha256(new_index/'manifest.json'),
        'next':'Integrate exact dev inheritance with fresh source-checked questions and audited connected groups; freeze and measure release gates in order.'}
    write_json(destination/'preflight.json',summary)
    return summary


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--old-index',type=Path,required=True)
    parser.add_argument('--new-index',type=Path,required=True)
    parser.add_argument('--candidate-report',type=Path,required=True)
    parser.add_argument('--dev-extension',type=Path,required=True)
    parser.add_argument('--destination',type=Path,required=True)
    args=parser.parse_args(argv)
    print(json.dumps(prepare(args.source,args.old_index,args.new_index,args.candidate_report,
                             args.dev_extension,args.destination),ensure_ascii=False,indent=2))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
