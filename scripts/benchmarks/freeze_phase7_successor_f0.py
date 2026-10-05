"""Lock reviewed successor groups and dev eligibility before any model tuning.

This is F0 only. It does not publish an F1 release dataset, run held-out inference,
rebind historical Phase 6 reports or claim that release gates have passed.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import shutil

from campusai.rag.context import benchmark_request, resolve_query
from evaluation.benchmarks.connected_groups import connected_groups
from evaluation.benchmarks.dev_inheritance import file_bindings, rows_at
from evaluation.benchmarks.freeze_human_benchmark import exposure_registry_errors, frozen_evidence, validate_rows
from evaluation.benchmarks.owner_generation import load_generation
from evaluation.common.release_artifacts import read_json, sha256, write_json
from evaluation.reranker.supplemental_gates import review_audit_errors

ROOT = Path(__file__).resolve().parents[2]
APPROVAL = "I explicitly approve the decisions you make for this Phase and authorize you to proceed without asking me to review each item manually."


def publish(path: Path, value) -> None:
    if path.exists():
        raise FileExistsError(path)
    write_json(path, value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--benchmark-dir', type=Path, required=True)
    parser.add_argument('--index-dir', type=Path, required=True)
    parser.add_argument('--results-dir', type=Path, required=True)
    parser.add_argument('--source-allocation', type=Path, required=True)
    args = parser.parse_args()
    bench, output, index = args.benchmark_dir, args.results_dir, args.index_dir
    output.mkdir(parents=True, exist_ok=True)
    if (output / 'p7-03_successor_f0_owner_signoff.json').exists():
        raise ValueError('F0 already signed; never rewrite a frozen allocation')
    preflight = read_json(bench / 'preflight.json')
    allocation = read_json(args.source_allocation)
    if preflight['status'] != 'PASS_DRAFT_VALIDATION' or allocation['owner_authorization_statement'] != APPROVAL:
        raise ValueError('validated draft and actual delegated owner approval required')
    auth, expected = load_generation(bench, index)
    rows = rows_at(bench / 'human_retrieval.draft.jsonl')
    evidence = frozen_evidence(index)
    audit = rows_at(bench / 'human_retrieval_review_audit.draft.jsonl')
    errors = review_audit_errors(rows, audit, index, owner_identity=auth['owner_identity'],
                                generation_authorization=auth, generated_records=expected)
    validation = validate_rows(rows, evidence, owner_identity=auth['owner_identity'], generated_records=expected)
    if errors or validation['errors']:
        raise ValueError({'review': errors, 'validation': validation['errors']})
    inherited = auth['_validated_dev_inheritance']['rows']
    groups = connected_groups(rows)
    if any(row['split'] != 'dev' for row in rows if row['qid'] in inherited):
        raise ValueError('consumed parent questions left dev')
    primary = {split: {groups[row['qid']] for row in rows if row['split'] == split}
               for split in ('test', 'holdout')}
    if any(len(values) < 10 for values in primary.values()) or primary['test'] & primary['holdout']:
        raise ValueError('primary groups are insufficient or cross-split')
    context_review = []
    for row in rows:
        if 'contextual' not in row['tags']:
            continue
        request = benchmark_request(row, [])
        resolved = resolve_query(request['question'], history=request['history'],
                                 selected_text=request['selected_text'], requires_context=request.get('requires_context', False))
        topic = request['selected_text'] or next((turn['content'] for turn in reversed(request['history'])
                                                  if turn['role'] == 'user'), None)
        if not topic or not resolved.contextual or resolved.needs_clarification or topic not in resolved.resolved:
            raise ValueError('actual contextual topic is not preserved: ' + row['qid'])
        gold = []
        for coordinate in row['gold_evidence']:
            item = evidence[coordinate['doc_id'], coordinate['chunk_id']]
            if item['page'] != coordinate['page'] or coordinate['doc_id'] not in request['doc_ids']:
                raise ValueError('context gold is outside the supplied scope')
            gold.append({**coordinate, 'source_content_sha256': hashlib.sha256(item['content'].encode()).hexdigest()})
        context_review.append({'qid': row['qid'], 'split': row['split'], 'request': request,
                               'resolved_query': resolved.resolved, 'gold_source_bindings': gold,
                               'topic_preserved': True, 'selection_trusted_as_evidence': False,
                               'meaning': 'Input/provenance review only; not retrieval or LLM quality measurement.'})
    if len(context_review) < 15:
        raise ValueError('15 actual contextual inputs have not been reviewed')
    publish(output / 'p7-03_successor_context_review.json', {
        'status': 'PASS_INPUT_SOURCE_REVIEW', 'decision_analyst': 'Codex AI assistant',
        'owner_authorization_statement': APPROVAL, 'independent_review_claim': False,
        'index_sha256': sha256(index / 'manifest.json'), 'cases': context_review,
        'context_runtime_sha256': sha256(ROOT / 'src/campusai/rag/context.py')})
    dev_groups = sorted({groups[row['qid']] for row in rows if row['split'] == 'dev'})
    folds = {group: int(hashlib.sha256(group.encode()).hexdigest(), 16) % 3 for group in dev_groups}
    cases, fold_support = [], defaultdict(Counter)
    for row in rows:
        if row['split'] != 'dev':
            continue
        group, gold = groups[row['qid']], row['gold_evidence']
        labels = [('sufficient', gold)] if row['answerable'] else [('absence', [])]
        if row['answerable'] and len(gold) > 1:
            labels.append(('partial', gold[:1]))
        for label, presented in labels:
            fold = folds[group]
            cases.append({'qid': row['qid'], 'connected_group': group, 'fold': fold,
                          'support_class': label, 'presented_source_coordinates': presented,
                          'all_required_gold_coordinates': gold})
            fold_support[fold][label] += 1
    if any(not all(fold_support[fold][label] > 0 for label in ('absence', 'partial', 'sufficient')) for fold in range(3)):
        raise ValueError('dev folds lack a required evidence support class')
    publish(bench / 'phase7_f0_dev_eligibility.json', {
        'schema_version': 1, 'status': 'PASS_F0_DEV_ELIGIBILITY', 'dev_only': True,
        'index_sha256': sha256(index / 'manifest.json'), 'fold_seed': 'connected_group_sha256_modulo_3',
        'group_folds': folds, 'fold_support': {str(fold): dict(counts) for fold, counts in fold_support.items()},
        'cases': cases, 'meaning': 'Source-grounded evidence-set construction, not measured predictions. '
        'A partial case deliberately omits required gold; all cases from one group stay in one fold.'})
    pool = bench / 'human_candidate_pool.jsonl'
    if pool.exists():
        raise FileExistsError(pool)
    shutil.copyfile(bench / 'human_retrieval.draft.jsonl', pool)
    publish(bench / 'human_candidate_lineage.json', {
        'schema_version': 1, 'status': 'pass', 'dataset_sha256': sha256(pool),
        'index_sha256': sha256(index / 'manifest.json'), 'connected_groups': groups,
        'source_allocation_sha256': sha256(args.source_allocation)})
    source_decisions = [ROOT / 'evaluation/results/phase7-completion-20261004' / name for name in
                        ('p7-03_semantic_exposure_decisions-v2.json', 'p7-03_qh2025_semantic_exposure_decisions.json')]
    history = read_json(bench / 'owner_generation_history_snapshot.json')
    for source in history['datasets']:
        if sha256(ROOT / source['path']) != source['sha256']:
            raise ValueError('sealed historical question input changed')
    study = bench / 'phase7_successor_construction_study.json'
    publish(study, {'schema_version': 1, 'purpose': 'source/question review before F0; no heldout inference',
                    'recorded_at': datetime.now(timezone.utc).isoformat(), 'model_measurements': [],
                    'history_snapshot_sha256': sha256(bench / 'owner_generation_history_snapshot.json'),
                    'source_semantic_decisions': [{'path': path.relative_to(ROOT).as_posix(), 'sha256': sha256(path)}
                                                  for path in source_decisions],
                    'source_allocation_sha256': sha256(args.source_allocation),
                    'source_row_binding_migration_sha256': sha256(bench / 'source_row_binding_migration.json'),
                    'question_generation_authorization_sha256': sha256(bench / 'phase7_generation_authorization.json'),
                    'question_novelty_check': 'production load_generation exact/Jaccard plus approved subject-level semantic history review',
                    'history_scope': 'Complete hash-verified repository archive identified in the source review queue; no external/unrecorded history is asserted.'})
    registry = []
    for row in rows:
        is_inherited = row['qid'] in inherited
        registry.append({'qid': row['qid'], 'connected_group': groups[row['qid']],
                         'status': 'known_exposed_parent_candidate_measurement' if is_inherited else 'unexposed_audited',
                         'heldout_eligible': not is_inherited,
                         'history_audit': {'complete': True, 'archive_reference':
                                           (bench / 'owner_generation_history_snapshot.json').as_posix(),
                                           'archive_sha256': sha256(bench / 'owner_generation_history_snapshot.json'),
                                           'study_manifest_sha256': sha256(study),
                                           'decision_analyst': 'Codex AI assistant',
                                           'approval_authority': 'project_owner', 'independent_review_claim': False}})
    registry_packet = {'status': 'pass', 'dataset_sha256': sha256(pool),
                       'lineage_sha256': sha256(bench / 'human_candidate_lineage.json'),
                       'index_sha256': sha256(index / 'manifest.json'), 'records': registry}
    publish(bench / 'phase7_exposure_registry.json', registry_packet)
    registry_errors = exposure_registry_errors(rows, registry_packet, source_pool=pool,
                                               source_lineage=bench / 'human_candidate_lineage.json',
                                               index_manifest=index / 'manifest.json')
    if registry_errors:
        raise ValueError(registry_errors)
    publish(output / 'p7-03_successor_f0_validation.json', {
        'schema_version': 1, 'status': 'PASS_F0', 'release_eligible': False,
        'row_validation': validation, 'review_errors': errors, 'exposure_errors': registry_errors,
        'primary_independent_groups': {split: len(values) for split, values in primary.items()},
        'contextual_inputs_reviewed': len(context_review), 'consumed_parent_records_dev_only': len(inherited),
        'dev_fold_support': {str(fold): dict(counts) for fold, counts in fold_support.items()},
        'phase5_grounding_minima_note': 'The 120/130/150 per-split minima in benchmark_schema.py apply to '
        'Phase 5 claim/answer releases, not this Phase 7 human retrieval schema. No threshold was changed.',
        'negative_statistics_note': 'Repeated missing-field proofs share document-level absence structure. '
        '13 negative questions are not a population FPR upper-bound claim.',
        'f1_dependencies': ['honest Phase 6 successor baseline for expanded index, preserving original reports',
                            'P7-06/P7-08 real provider pilot and target measurements',
                            'P7-09 feasible dev study; F1 before heldout inference']})
    publish(output / 'p7-03_successor_f0_owner_signoff.json', {
        'schema_version': 1, 'task': 'P7-03/F0', 'status': 'OWNER_AUTHORIZED_SUCCESSOR_F0_FROZEN',
        'recorded_at': datetime.now(timezone.utc).isoformat(), 'f0_split_frozen': True,
        'f1_release_frozen': False, 'release_eligible': False, 'decision_analyst': 'Codex AI assistant',
        'approval_authority': 'project_owner', 'owner_identity': auth['owner_identity'],
        'owner_authorization_statement': APPROVAL, 'owner_manual_row_review_claim': False,
        'independent_review_claim': False, 'benchmark_dir': bench.as_posix(), 'index_dir': index.as_posix(),
        'index_sha256': sha256(index / 'manifest.json'), 'benchmark_files': file_bindings(bench),
        'context_review_sha256': sha256(output / 'p7-03_successor_context_review.json'),
        'validation_sha256': sha256(output / 'p7-03_successor_f0_validation.json'),
        'split_assignments': {row['qid']: row['split'] for row in rows}, 'connected_groups': groups,
        'scope': 'Locks successor reviewed questions/groups and dev eligibility only. '
        'No heldout performance measurement or historical Phase 6 report is rewritten.'})
    print({'status': 'PASS_F0', 'records': len(rows), 'contextual_inputs': len(context_review),
           'primary_groups': {split: len(values) for split, values in primary.items()},
           'fold_support': {fold: dict(counts) for fold, counts in fold_support.items()}})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
