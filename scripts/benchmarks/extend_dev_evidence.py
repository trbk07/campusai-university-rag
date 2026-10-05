"""Extend a new benchmark cycle with audited dev-only absent-field questions."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import shutil

from campusai.retrieval.routing import detected_course_codes
from evaluation.benchmarks.connected_groups import connected_groups
from evaluation.benchmarks.dev_evidence_extension import FACETS, absence_proof, rows_at
from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence, exposure_registry_errors, validate_rows
from evaluation.benchmarks.owner_generation import course_facts, load_generation, generated_audit
from evaluation.benchmarks.owner_review import load_confirmation
from evaluation.common.release_artifacts import read_json, write_json, sha256
from evaluation.reranker.supplemental_gates import review_audit_errors
from scripts.benchmarks.revise_dev_difficulty import write_rows


def create(source: Path, destination: Path, index: Path) -> dict:
    if destination.exists():
        raise ValueError('use an absent benchmark cycle; do not overwrite frozen inputs')
    confirmation, originals = load_confirmation(source)
    parent = rows_at(source/'human_retrieval_dev.jsonl')
    old = rows_at(source/'human_retrieval.jsonl')
    if {r['qid'] for r in parent} != {r['qid'] for r in originals}:
        raise ValueError('extension requires the confirmed parent owner dev split')
    if any(r['split'] != 'dev' for r in parent):
        raise ValueError('only parent dev facts may be extended')
    evidence = frozen_evidence(index)
    by_doc = defaultdict(dict)
    dev_codes = {code for row in parent for code in detected_course_codes(row['question'])}
    for fact in course_facts(evidence):
        if fact['code'] in dev_codes:
            by_doc[fact['doc_id']].setdefault(fact['code'], fact)
    specs = []
    for doc, facts in sorted(by_doc.items()):
        ordered = sorted(facts.values(), key=lambda f: f['code'])
        for number in range(0, len(ordered)-1, 2):
            pair = ordered[number:number+2]
            # Facets form declared template families for grouped OOF; merely
            # varying course names must not pretend to create independent folds.
            choices = list(FACETS)
            offset = len(specs) % len(choices)
            for facet in choices[offset:] + choices[:offset]:
                try:
                    proof = absence_proof(pair, facet, evidence)
                except ValueError:
                    continue
                specs.append({'qid':f'human-dev-evidence-{len(specs)+1:03d}',
                              'kind':'dev_absent_field', 'split':'dev', 'facet':facet, 'facts':pair,
                              'family':'dev-curriculum-field-'+'-'.join(f['code'] for f in pair),
                              'absence_proof':proof})
                break
    if len(specs) < 8 or len({s['facet'] for s in specs}) < 3:
        raise ValueError('not enough source-proved dev challenges across three field families')
    # All original owner, generation, metadata-audit and heldout bytes are
    # retained. Only named canonical/lineage successors are then written.
    shutil.copytree(source, destination)
    shutil.copyfile(source/'human_retrieval_dev.jsonl', destination/'dev_extension_parent_dev.jsonl')
    write_json(destination/'owner_generated_dev_source_bank.json', {'schema_version':1,'dev_only':True,'records':specs})
    auth = {'schema_version':1,'profile':'personal_owner_source_checked_ai',
            'owner_identity':confirmation['owner_identity'],'approval_source':'project_owner_chat_instruction',
            'approval_statement':'t duyệt hết nên bạn cứ nhập tên tác giải là t',
            'generation_statement':'nếu k có thì tự tạo đi, t cho phép',
            'recorded_at':datetime.now(timezone.utc).isoformat(),'independent_human_review_claim':False,
            'dev_only':True,'new_heldout_claim':False,
            'review_policy_sha256':sha256(destination/'phase7_review_policy.json'),
            'index_sha256':sha256(index/'manifest.json'),
            'parent_confirmation_sha256':sha256(destination/'phase7_owner_confirmation.json'),
            'parent_dev_sha256':sha256(destination/'dev_extension_parent_dev.jsonl'),
            'source_bank_sha256':sha256(destination/'owner_generated_dev_source_bank.json'),
            'timestamp_meaning':'recorded now under standing owner authorization; no historical review or independent reviewer asserted'}
    write_json(destination/'phase7_dev_generation_authorization.json', auth)
    authorization, expected = load_generation(destination, index)
    additions = [row for row in expected.values() if row['qid'].startswith('human-dev-evidence-')]
    rows = old + additions
    groups = connected_groups(rows)
    write_rows(destination/'human_retrieval.jsonl', rows)
    write_rows(destination/'human_candidate_pool.jsonl', rows)
    write_rows(destination/'human_retrieval_dev.jsonl', parent + additions)
    audit = rows_at(source/'human_retrieval_review_audit.jsonl') + generated_audit(authorization, {r['qid']:r for r in additions})
    write_rows(destination/'human_retrieval_review_audit.jsonl', audit)
    lineage = read_json(destination/'human_candidate_lineage.json')
    lineage.update(dataset_sha256=sha256(destination/'human_candidate_pool.jsonl'),connected_groups=groups)
    lineage['qid_mapping'] += [{'qid':r['qid'],'candidate_id':r['candidate_id'],'source_record_id':r['qid']} for r in additions]
    write_json(destination/'human_candidate_lineage.json', lineage)
    registry = read_json(destination/'phase7_exposure_registry.json')
    entries = [{**entry,'connected_group':groups[entry['qid']]} for entry in registry['records']]
    entries += [{'qid':row['qid'],'connected_group':groups[row['qid']],
                 'status':'known_exposed_dev_source_fact_reuse','heldout_eligible':False,'authorship_inferred':False,
                 'basis':'new dev questions use source facts already named in the retained parent dev; not a historical question-exposure claim',
                 'dev_generation_authorization_sha256':sha256(destination/'phase7_dev_generation_authorization.json')}
                for row in additions]
    registry.update(dataset_sha256=sha256(destination/'human_candidate_pool.jsonl'),
                    lineage_sha256=sha256(destination/'human_candidate_lineage.json'),records=entries,
                    counts=dict(Counter(e['status'] for e in entries)))
    write_json(destination/'phase7_exposure_registry.json', registry)
    preflight = validate_rows(rows,evidence,owner_identity=confirmation['owner_identity'],generated_records=expected)
    errors = preflight['errors'] + review_audit_errors(rows,audit,index,owner_identity=confirmation['owner_identity'],
        owner_confirmation=confirmation,confirmed_sources=originals,
        generation_authorization=authorization,generated_records=expected)
    errors += exposure_registry_errors(rows,registry,source_pool=destination/'human_candidate_pool.jsonl',
        source_lineage=destination/'human_candidate_lineage.json',index_manifest=index/'manifest.json')
    heldout = {}
    for split in ('test','holdout'):
        name=f'human_retrieval_{split}.jsonl'
        if (source/name).read_bytes() != (destination/name).read_bytes():
            errors.append('heldout_bytes_changed:'+split)
        heldout[split]=sha256(destination/name)
    report={'schema_version':1,'status':'fail' if errors else 'pass','errors':sorted(set(errors)),
            'parent_benchmark_dir':source.as_posix(),'parent_dataset_sha256':sha256(source/'human_retrieval.jsonl'),
            'dev_additions':len(additions),'facets':dict(Counter(s['facet'] for s in specs)),
            'heldout_reused_unchanged':True,'new_heldout_claim':False,'heldout_sha256':heldout,
            'review_authority':'project_owner_standing_chat_instruction','independent_review_claim':False}
    write_json(destination/'dev_evidence_extension_preflight.json',report)
    if errors:
        raise ValueError('dev extension preflight failed: '+', '.join(sorted(set(errors))))
    return report


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--destination',type=Path,required=True)
    parser.add_argument('--index-dir',type=Path,default=Path('.tmp/hybrid-index'))
    args=parser.parse_args(argv)
    report=create(args.source,args.destination,args.index_dir)
    print(f"Dev additions: {report['dev_additions']}; heldout reused without byte changes.")
    return 0


if __name__=='__main__':
    raise SystemExit(main())
