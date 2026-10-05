"""Prepare source-reviewed successor questions without running held-out models.

One credit question and one scoped absence question per approved subject family;
one comparison only when the family has two distinct source documents. Consumed
historical records are inherited as dev, preserving their real attribution.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from evaluation.benchmarks.connected_groups import connected_groups, normalized_question
from evaluation.benchmarks.dev_inheritance import file_bindings, rows_at, validate_inheritance
from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence, validate_rows
from evaluation.benchmarks.owner_generation import generated_audit, load_generation
from evaluation.benchmarks.source_course_generation import comparison_contexts, course_context, single_course_absence_proof
from evaluation.benchmarks.source_course_rows import source_course_rows
from evaluation.common.release_artifacts import read_json, sha256, write_json
from evaluation.reranker.supplemental_gates import review_audit_errors

ROOT = Path(__file__).resolve().parents[2]
OWNER_APPROVAL = "I explicitly approve the decisions you make for this Phase and authorize you to proceed without asking me to review each item manually."


def write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text(''.join(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n'
                            for row in rows), encoding='utf8')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('index-dir', 'allocation', 'history-queue', 'parent-benchmark', 'parent-index',
                'parent-candidate-report', 'destination'):
        parser.add_argument('--' + key, type=Path, required=True)
    args = parser.parse_args()
    if args.destination.exists():
        parser.error('refusing to overwrite an existing question preparation')
    allocation = read_json(args.allocation)
    if (allocation['status'] != 'OWNER_APPROVED_SOURCE_ALLOCATION_ONLY'
            or allocation['benchmark_f0_frozen'] is not False
            or allocation['owner_authorization_statement'] != OWNER_APPROVAL
            or allocation['independent_reviewer_claim'] is not False):
        raise ValueError('actual delegated owner source allocation is required')
    index_hash = sha256(args.index_dir / 'manifest.json')
    evidence = frozen_evidence(args.index_dir)
    facts = source_course_rows(evidence)
    policy_path = args.parent_benchmark / 'phase7_review_policy.json'
    policy = read_json(policy_path)
    if policy['owner_identity'] != allocation['owner_identity']:
        raise ValueError('source review and standing policy owner identity differ')
    parent_rows = rows_at(args.parent_benchmark / 'human_retrieval.jsonl')
    inheritance = {
        'schema_version': 1, 'profile': 'legacy_source_checked_dev_inheritance_v1',
        'recorded_at': datetime.now(timezone.utc).isoformat(), 'dev_only': True,
        'new_heldout_claim': False, 'owner_identity': policy['owner_identity'],
        'index_sha256': index_hash, 'records': len(parent_rows),
        'parents': [{'benchmark_dir': args.parent_benchmark.as_posix(),
                     'index_dir': args.parent_index.as_posix(),
                     'benchmark_files': file_bindings(args.parent_benchmark),
                     'index_files': file_bindings(args.parent_index),
                     'mode': 'consumed_candidate_splits',
                     'candidate_report': args.parent_candidate_report.as_posix(),
                     'candidate_report_sha256': sha256(args.parent_candidate_report),
                     'qids': sorted(row['qid'] for row in parent_rows)}],
        'meaning': 'All consumed parent dev/test/holdout records become dev; no fresh heldout claim.',
    }
    inherited = validate_inheritance(inheritance, args.index_dir, policy, root=ROOT)
    queue = read_json(args.history_queue)
    history, history_files = [], queue['inputs']['history_datasets']
    for item in history_files:
        path = ROOT / item['path']
        if sha256(path) != item['sha256']:
            raise ValueError('pre-generation history input changed: ' + item['path'])
        for number, row in enumerate(rows_at(path), 1):
            question = row.get('question', row.get('query', ''))
            if isinstance(question, str) and question.strip():
                history.append({'question': question, 'qid': row.get('qid'),
                                'dataset': item['path'], 'line': number})
    if len(history) != queue['inputs']['history_question_occurrences']:
        raise ValueError('pre-generation history inventory count differs')
    history_snapshot = {'recorded_at': datetime.now(timezone.utc).isoformat(),
                        'questions': history, 'datasets': history_files, 'inventory_complete': True,
                        'meaning': 'Hash-verified question-only historical inputs; no outcomes used.'}
    specs, assignments = [], {}
    contextual_counts = Counter()
    row_proofs = []
    for number, group in enumerate(allocation['assignments']):
        selected = []
        for original in group['source_rows'] + group.get('qh2025_source_additions', []):
            matches = [fact for fact in facts if all(fact[key] == original[key]
                       for key in ('doc_id', 'page', 'code', 'cells_sha256', 'credits'))]
            if len(matches) != 1:
                raise ValueError('approved physical source row cannot be rebound uniquely')
            if matches[0] not in selected:
                selected.append(matches[0])
            row_proofs.append({'before': original, 'after': matches[0],
                               'physical_cells_page_credits_unchanged': True,
                               'source_family': group['connected_group']})
        family = group['connected_group']
        selected.sort(key=lambda fact: (fact['doc_id'], fact['code']))
        representative = next((fact for fact in selected if fact['code'].startswith('UET.')), selected[0])
        base = {'family': family, 'template_variant': number % 4,
                'include_codes': True, 'dev_only': group['assignment'] == 'dev'}
        for kind, suffix in [('source_course_credit', 'credit'),
                             ('source_course_absent_field_single', 'exam-date')]:
            spec = {**base, 'qid': f'human-successor-{number + 1:02d}-{suffix}', 'kind': kind,
                    'facts': [representative], 'display_names': [representative['name']]}
            if suffix == 'exam-date':
                spec.update(facet='exam_schedule', absence_proof=single_course_absence_proof(
                    spec['facts'], 'exam_schedule', evidence, index_hash))
            elif contextual_counts[group['assignment']] < 5:
                position = contextual_counts[group['assignment']]
                spec.update(context_mode='history' if position % 2 else 'selection',
                            context_binding=course_context(representative, evidence))
                contextual_counts[group['assignment']] += 1
            specs.append(spec); assignments[spec['qid']] = group['assignment']
        if len({fact['doc_id'] for fact in selected}) == 2:
            contexts = comparison_contexts(selected, evidence)
            spec = {**base, 'qid': f'human-successor-{number + 1:02d}-compare',
                    'kind': 'source_course_compare', 'facts': selected,
                    'display_names': [fact['name'] for fact in selected], 'comparison_contexts': contexts}
            specs.append(spec); assignments[spec['qid']] = group['assignment']
    destination = args.destination
    destination.mkdir(parents=True)
    shutil.copyfile(policy_path, destination / 'phase7_review_policy.json')
    write_json(destination / 'phase7_dev_inheritance.json', inheritance)
    write_json(destination / 'owner_generation_history_snapshot.json', history_snapshot)
    write_json(destination / 'owner_generated_source_bank.json', {
        'schema_version': 1, 'purpose': 'source-reviewed successor construction before F0',
        'source_allocation_sha256': sha256(args.allocation), 'records': specs})
    # The standing profile retains its original authorization text. The actual
    # new delegated-review statement is recorded separately and never called
    # independent human review or manual review by the owner.
    authorization = {
        'profile': 'personal_owner_source_checked_ai', 'owner_identity': policy['owner_identity'],
        'approval_source': 'project_owner_chat_instruction',
        'approval_statement': 't duyệt hết nên bạn cứ nhập tên tác giải là t',
        'generation_statement': 'nếu k có thì tự tạo đi, t cho phép',
        'standing_authorization_reference': (args.parent_benchmark / 'phase7_generation_authorization.json').as_posix(),
        'delegated_decision_approval_statement': OWNER_APPROVAL,
        'decision_analyst': 'Codex AI assistant', 'owner_manual_row_review_claim': False,
        'independent_human_review_claim': False, 'recorded_at': datetime.now(timezone.utc).isoformat(),
        'index_sha256': index_hash, 'review_policy_sha256': sha256(policy_path),
        'source_bank_sha256': sha256(destination / 'owner_generated_source_bank.json'),
        'history_snapshot_sha256': sha256(destination / 'owner_generation_history_snapshot.json'),
        'dev_inheritance_sha256': sha256(destination / 'phase7_dev_inheritance.json'),
        'source_allocation_sha256': sha256(args.allocation),
    }
    write_json(destination / 'phase7_generation_authorization.json', authorization)
    auth, expected = load_generation(destination, args.index_dir)
    rows = [{**row, 'split': assignments[qid]} if qid in assignments else row
            for qid, row in sorted(expected.items())]
    # The existing audit contract binds the generated record before grouped
    # split assignment; export_matches permits only that split change. The
    # draft dataset and split proposal separately bind the assigned bytes.
    audit = generated_audit(auth, expected)
    audit_errors = review_audit_errors(rows, audit, args.index_dir,
                                     owner_identity=policy['owner_identity'],
                                     generation_authorization=auth, generated_records=expected)
    validation = validate_rows(rows, evidence, owner_identity=policy['owner_identity'],
                               generated_records=expected)
    groups = connected_groups(rows)
    group_splits = defaultdict(set)
    for row in rows:
        group_splits[groups[row['qid']]].add(row['split'])
    cross = {group: sorted(splits) for group, splits in group_splits.items() if len(splits) > 1}
    per_split = {}
    for split in ('dev', 'test', 'holdout'):
        subset = [row for row in rows if row['split'] == split]
        per_split[split] = {'records': len(subset), 'independent_connected_groups':
                           len({groups[row['qid']] for row in subset}),
                           'positive': sum(row['answerable'] for row in subset),
                           'negative': sum(not row['answerable'] for row in subset),
                           'positive_hard': sum(row['answerable'] and row['difficulty'] == 'hard' for row in subset),
                           'positive_easy': sum(row['answerable'] and row['difficulty'] == 'easy' for row in subset),
                           'actual_ambiguous': sum('ambiguous' in row['tags'] for row in subset),
                           'contextual': sum('contextual' in row['tags'] for row in subset)}
    for item in history_files:
        if sha256(ROOT / item['path']) != item['sha256']:
            raise ValueError('history changed during question construction')
    write_rows(destination / 'human_retrieval.draft.jsonl', rows)
    write_rows(destination / 'human_retrieval_review_audit.draft.jsonl', audit)
    write_json(destination / 'source_row_binding_migration.json', row_proofs)
    write_json(destination / 'source_split_proposal.json', {'index_sha256': index_hash,
        'benchmark_f0_frozen': False, 'source_allocation_sha256': sha256(args.allocation),
        'assignments': assignments, 'connected_groups': groups, 'cross_split_groups': cross})
    report = {'schema_version': 1, 'status': 'PASS_DRAFT_VALIDATION' if not validation['errors'] and not audit_errors else 'GAPS_REMAIN',
              'benchmark_f0_frozen': False, 'release_eligible': False,
              'recorded_at': datetime.now(timezone.utc).isoformat(), 'index_sha256': index_hash,
              'new_questions': len(specs), 'inherited_dev_records': len(inherited['rows']),
              'history_occurrences': len(history), 'history_files': len(history_files),
              'per_split': per_split, 'review_errors': audit_errors,
              'validation': validation, 'cross_split_groups': cross,
              'remaining': ['review contextual inputs/folds against the successor scope',
                            'reconcile all question-level semantic dependencies before F0',
                            'resolve honest Phase 6 baseline provenance for the expanded index before F1'],
              'builder_sha256': sha256(Path(__file__))}
    write_json(destination / 'preflight.json', report)
    print(json.dumps({key: report[key] for key in ('status', 'new_questions', 'inherited_dev_records', 'per_split', 'review_errors')}, ensure_ascii=True))
    print(json.dumps({'validation_errors': validation['errors']}, ensure_ascii=True))
    return 0 if not audit_errors and not any(error.startswith('row_') for error in validation['errors']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
