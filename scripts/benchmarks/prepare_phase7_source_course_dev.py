"""Prepare explicit source-checked dev questions with preserved legacy dev origin.

No release freeze or heldout allocation occurs. Selection is supplied before
model measurement and all selected source subjects become exposed dev material.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from evaluation.benchmarks.dev_inheritance import validate_inheritance
from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence, validate_rows
from evaluation.benchmarks.owner_generation import generated_audit, load_generation, validate_generation
from evaluation.benchmarks.source_course_generation import absence_proof, export_matches
from evaluation.benchmarks.source_course_rows import source_course_rows
from evaluation.benchmarks.source_proposals import history_inventory
from evaluation.common.release_artifacts import read_json, sha256, write_json
from evaluation.reranker.supplemental_gates import review_audit_errors

ROOT = Path(__file__).resolve().parents[2]


def prepare(selection_path: Path, inheritance_path: Path, index: Path,
            policy_path: Path, destination: Path, history_dirs: list[Path], *, root: Path = ROOT) -> dict:
    if destination.exists():
        raise ValueError('preserve earlier preparations; choose an absent destination')
    if not history_dirs or any(not directory.is_dir() for directory in history_dirs):
        raise ValueError('all historical dataset directories must exist')
    policy=read_json(policy_path)
    evidence=frozen_evidence(index); index_hash=sha256(index/'manifest.json')
    inherited=validate_inheritance(read_json(inheritance_path),index,policy,root=root)
    history,datasets=history_inventory(history_dirs)
    history_packet={'recorded_at':datetime.now(timezone.utc).isoformat(),
                    'questions':history,'datasets':datasets,'inventory_complete':True,
                    'meaning':'Complete JSONL inventory for dev provenance; no new heldout eligibility.'}
    selection=read_json(selection_path)
    if (selection.get('schema_version') != 1 or selection.get('dev_only') is not True
            or selection.get('new_heldout_claim') is not False
            or not isinstance(selection.get('pairs'), list) or not selection['pairs']):
        raise ValueError('explicit dev-only course pair selection required')
    by_key={}
    for fact in source_course_rows(evidence):
        by_key.setdefault((fact['doc_id'],fact['code']),[]).append(fact)
    specs=[]; selected=set(); families=set()
    for pair in selection['pairs']:
        family=pair.get('family')
        courses=pair.get('courses')
        if (not isinstance(family,str) or not family.strip() or family in families
                or not isinstance(courses,list) or len(courses)!=2):
            raise ValueError('unique dev families with two named course choices required')
        families.add(family)
        facts=[]
        for course in courses:
            key=(course['doc_id'],course['code'])
            if key not in by_key or len(by_key[key]) != 1 or course['code'] in selected:
                raise ValueError('source course choice is missing or repeated')
            selected.add(course['code']); facts.append(by_key[key][0])
        # Families describe the actual paired subjects, not independent rows.
        for variant in range(4):
            language='vi' if variant % 2 == 0 else 'en'
            names=[course['display_names'][language] for course in courses]
            base={'family':family,'template_variant':variant,'include_codes':variant < 2,'dev_only':True}
            for number,fact in enumerate(facts):
                specs.append({**base,'qid':f'human-source-dev-{family}-credit-{number+1}-{variant+1}',
                    'kind':'source_course_credit','facts':[fact],'display_names':[names[number]]})
            specs.append({**base,'qid':f'human-source-dev-{family}-sum-{variant+1}',
                'kind':'source_course_sum','facts':facts,'display_names':names})
            for facet in ('fee_waiver','exam_schedule','teaching_room'):
                specs.append({**base,'qid':f'human-source-dev-{family}-{facet}-{variant+1}',
                    'kind':'source_course_absent_field','facts':facts,'display_names':names,
                    'facet':facet,'absence_proof':absence_proof(facts,facet,evidence,index_hash)})
    authorization={'profile':'personal_owner_source_checked_ai','owner_identity':policy['owner_identity'],
        'approval_source':'project_owner_chat_instruction',
        'approval_statement':'t duyệt hết nên bạn cứ nhập tên tác giải là t',
        'generation_statement':'nếu k có thì tự tạo đi, t cho phép',
        'independent_human_review_claim':False,'recorded_at':datetime.now(timezone.utc).isoformat(),
        'dev_only':True,'new_heldout_claim':False,'index_sha256':index_hash,
        'review_policy_sha256':sha256(policy_path),'selection_sha256':sha256(selection_path),
        'dev_inheritance_sha256':sha256(inheritance_path)}
    expected=validate_generation(authorization,specs,evidence,policy['owner_identity'],index_sha256=index_hash)
    if set(expected) & set(inherited['rows']):
        raise ValueError('new dev qids collide with inherited records')
    if any(sha256(item['path']) != item['sha256'] for item in datasets):
        raise ValueError('historical datasets changed during preparation')
    destination.mkdir(parents=True)
    shutil.copyfile(policy_path,destination/'phase7_review_policy.json')
    shutil.copyfile(selection_path,destination/'source_course_dev_selection.json')
    shutil.copyfile(inheritance_path,destination/'phase7_dev_inheritance.json')
    write_json(destination/'owner_generated_source_bank.json',{'schema_version':1,'dev_only':True,
        'new_heldout_claim':False,'records':specs})
    write_json(destination/'owner_generation_history_snapshot.json',history_packet)
    authorization.update(source_bank_sha256=sha256(destination/'owner_generated_source_bank.json'),
        history_snapshot_sha256=sha256(destination/'owner_generation_history_snapshot.json'))
    write_json(destination/'phase7_generation_authorization.json',authorization)
    auth,loaded=load_generation(destination,index)
    if {qid:row for qid,row in loaded.items() if qid in expected} != validate_generation(
            authorization,specs,evidence,policy['owner_identity'],index_sha256=index_hash):
        raise ValueError('production source-question loader replay differs')
    rows=list(loaded.values()); audit=generated_audit(auth,loaded)
    review_errors=review_audit_errors(rows,audit,index,owner_identity=policy['owner_identity'],
        generation_authorization=auth,generated_records=loaded)
    validation=validate_rows(rows,evidence,owner_identity=policy['owner_identity'],generated_records=loaded)
    if review_errors or any(error.startswith('row_') for error in validation['errors']):
        raise ValueError('dev source packet row/review validation failed')
    for name,records in [('human_retrieval_dev.jsonl',rows),('source_course_dev_records.jsonl',
                         [row for row in rows if row['qid'] in expected]),('human_review_audit.jsonl',audit)]:
        (destination/name).write_text(''.join(json.dumps(row,ensure_ascii=False,sort_keys=True)+'\n'
                                              for row in records),encoding='utf8')
    rejected=sum(not export_matches(row,{**row,'split':split}) for row in loaded.values()
                 if row['qid'] in expected for split in ('test','holdout'))
    assert rejected==2*len(expected)
    summary={'schema_version':1,'status':'validated_dev_source_packet','release_eligible':False,
        'dev_only':True,'new_heldout_claim':False,'index_sha256':index_hash,'records':len(rows),
        'inherited_records':len(inherited['rows']),'new_source_records':len(expected),
        'selected_course_codes':sorted(selected),'selected_course_families':len(families),
        'selected_document_ids':sorted({f['doc_id'] for spec in specs for f in spec['facts']}),
        'new_answerability_counts':dict(Counter(row['answerable'] for row in loaded.values() if row['qid'] in expected)),
        'history_question_occurrences':len(history),'history_datasets':len(datasets),
        'review_errors':review_errors,'row_errors':[e for e in validation['errors'] if e.startswith('row_')],
        'dev_only_split_reassignments_rejected':rejected,'dev_only_validation':validation,
        'source_bank_sha256':authorization['source_bank_sha256'],
        'generation_authorization_sha256':sha256(destination/'phase7_generation_authorization.json'),
        'meaning':'New source subjects are explicitly consumed for dev. No benchmark freeze, novel heldout approval or model scores.'}
    write_json(destination/'preflight.json',summary)
    return summary


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('selection','inheritance','index-dir','review-policy','destination'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--history-dir',type=Path,action='append',required=True)
    args=parser.parse_args(argv)
    summary=prepare(args.selection,args.inheritance,args.index_dir,args.review_policy,args.destination,args.history_dir)
    print(json.dumps({key:summary[key] for key in ('status','records','inherited_records','new_source_records',
        'selected_course_codes','selected_document_ids','review_errors','row_errors',
        'dev_only_split_reassignments_rejected')},ensure_ascii=False,indent=2))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
