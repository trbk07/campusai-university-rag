"""Verify and review the saved Phase 8 Chat-assisted WSGI regression.

No generation, network, human signatures or live-runtime claims. Content labels
are carried forward only when published text exactly matches its reviewed input.
"""
from __future__ import annotations

from datetime import datetime, timezone
import argparse
import json
from pathlib import Path

from campusai.rag.grounding import validate_citation
from campusai.rag.schemas import validate_release_response, validate_response
from evaluation.phase8.replay_chat_baseline import (
    ROOT, INDEX, BENCHMARK, CHAT, SUMMARY, PREFLIGHT, correct_annotations, read_rows, sha, write_json,
    load_reviewed_inputs,
)
from evaluation.phase8.score_temporal_product_outputs import (
    _bootstrap_ci, _load_index, _validate_execution_manifest, _index_tree_sha256,
)

OUTPUT = ROOT / 'evaluation/results/phase8-chat-replay-final-20261012'


def review(output=OUTPUT):
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT):
        raise ValueError('review output must stay within the project')
    predictions = read_rows(output / 'predictions.jsonl')
    rows = read_rows(output / 'benchmark-scoring-annotations.jsonl')
    by_id = {row['qid']: row for row in rows}
    index = _load_index(INDEX)
    expected_overlay, corrections = correct_annotations(read_rows(BENCHMARK), index)
    if rows != expected_overlay:
        raise ValueError('scoring overlay differs from independent source correction')
    receipt, _ = _validate_execution_manifest(output / 'execution.json',
        benchmark_path=output / 'benchmark-scoring-annotations.jsonl',
        predictions_path=output / 'predictions.jsonl', index_manifest_path=INDEX / 'manifest.json',
        index_tree_sha256=_index_tree_sha256(INDEX))
    if (receipt['mode'] != 'RECORDED_CHAT_WSGI_REPLAY_NOT_LIVE_PROVIDER'
            or receipt['provider_requests_sent'] != 0 or receipt['network_disabled'] is not True):
        raise ValueError('unexpected execution policy')
    if [p['qid'] for p in predictions] != [row['qid'] for row in rows] or len(by_id) != len(rows):
        raise ValueError('prediction population/order differs from benchmark')
    inputs = receipt.get('reviewed_inputs', {})
    chat_path = ROOT / inputs.get('chat', CHAT.relative_to(ROOT).as_posix())
    summary_path = ROOT / inputs.get('summary', SUMMARY.relative_to(ROOT).as_posix())
    preflight_path = ROOT / inputs.get('preflight', PREFLIGHT.relative_to(ROOT).as_posix())
    _packet, _rows, chat, summary = load_reviewed_inputs(preflight_path, chat_path, summary_path)
    if (receipt['bindings']['recorded_chat_sha256'] != sha(chat_path)
            or receipt['bindings']['original_preflight_sha256'] != sha(preflight_path)
            or (inputs and receipt['bindings'].get('chat_review_summary_sha256') != sha(summary_path))):
        raise ValueError('execution does not bind selected Chat review inputs')
    labels = {p['qid']: p for p in summary['cases']}
    quality_path = output / 'quality.json'
    quality = json.loads(quality_path.read_text(encoding='utf-8'))
    if (quality['runtime']['execution_manifest_sha256'] != sha(output / 'execution.json')
            or quality['scorer_sha256'] != sha(ROOT / 'evaluation/phase8/score_temporal_product_outputs.py')):
        raise ValueError('quality report receipt/scorer mismatch')
    cases, misses, gold_differences = [], [], []
    quotes = coordinate_passes = schema_passes = supported_claims = 0
    correct_answers = {}
    for p in predictions:
        qid = p['qid']
        internal, public = p['internal_response'], p['public_response']
        schema_ok = (validate_response(internal, include_internal=True)[0]
                     and validate_release_response(public)[0])
        if not schema_ok:
            raise ValueError('invalid published contract: ' + qid)
        schema_passes += 1
        for citation in public['citations']:
            checked = validate_citation(citation, index[citation['doc_id'], citation['chunk_id']], require_quote=True)
            if not checked.valid:
                raise ValueError('invalid citation: ' + qid)
            quotes += 1
            coordinate_passes += 1
            gold_ids = {e.get('chunk_id') for claim in by_id[qid].get('gold_claims', [])
                        for e in claim.get('evidence', [])}
            if citation['chunk_id'] not in gold_ids:
                gold_differences.append({'qid': qid, 'cited_chunk': citation['chunk_id'],
                    'gold_chunks': sorted(gold_ids), 'source_quote_valid': True})
        if qid in chat:
            original = chat[qid]['response']
            unchanged = (not public['abstained'] and public['answer'] == original['answer']
                         and [c['text'] for c in public['claims']] == [c['text'] for c in original['claims']])
            accepted = labels[qid]['decision'] == 'ACCEPT_CONTENT' and unchanged
            if any(c['status'] != 'supported' for c in internal['claims']):
                accepted = False
            supported_claims += sum(c['status'] == 'supported' for c in internal['claims']) if not public['abstained'] else 0
            correct_answers[qid] = float(accepted)
            cases.append({'qid': qid, 'decision': 'ACCEPT_PUBLISHED_CONTENT' if accepted else 'REJECT_PUBLISHED_CONTENT',
                'basis': 'Exact published answer/claim text equals the independently source-reviewed Chat input; application support and source quotes verified.',
                'review_path': labels[qid]['review_path'], 'review_sha256': sha(ROOT / labels[qid]['review_path']),
                'content_unchanged': unchanged, 'normalized_input': chat[qid]['normalization_applied']})
            if not accepted:
                misses.append({'qid': qid, 'question': by_id[qid]['question'],
                               'reason': internal.get('abstention_reason') or 'published_content_drift'})
        elif by_id[qid]['answerable']:
            correct_answers[qid] = 0.0
            misses.append({'qid': qid, 'question': by_id[qid]['question'],
                           'reason': internal.get('abstention_reason')})
    negatives = [p for p in predictions if not by_id[p['qid']]['answerable']]
    if set(chat) != {p['qid'] for p in predictions if p['mode'] == 'recorded_chat_replay'}:
        raise ValueError('recorded generation cohort changed')
    baseline = read_rows(ROOT / 'evaluation/results/phase8-chat-replay-baseline-20261012/predictions.jsonl')
    report = {
        'schema_version': 1, 'status': 'AUTOMATED_BASELINE_REVIEW_COMPLETE_EXIT_NOT_MET',
        'reviewed_at': datetime.now(timezone.utc).isoformat(), 'reviewer': 'Codex - Automated AI Review',
        'phase8_pass': False, 'officially_approved': False, 'fresh_validation': False,
        'scope': f"{len(predictions)} actual WSGI requests: {receipt['local_requests']} native local branches and {len(chat)} recorded Chat responses (normalization disclosed per case); no live provider generation.",
        'counts': {'requests': len(predictions), 'local': receipt['local_requests'],
            'recorded_chat': len(chat), 'published_content_accepted': int(sum(correct_answers.values())),
            'answerable': len(correct_answers), 'unanswerable': len(negatives),
            'correct_negative_abstentions': sum(p['public_response']['abstained'] for p in negatives),
            'schema_valid': schema_passes, 'source_quote_coordinate_valid': coordinate_passes,
            'public_citations': quotes, 'supported_published_claims': supported_claims,
            'source_verified_annotation_corrections': len(corrections),
            'false_model_abstentions_before_fix': sum(p['mode'] == 'recorded_chat_replay' and p['public_response']['abstained'] for p in baseline),
            'false_model_abstentions_after_fix': sum(p['mode'] == 'recorded_chat_replay' and p['public_response']['abstained'] for p in predictions),
            'provider_requests_sent': 0},
        'automated_semantic_correctness': {'value': sum(correct_answers.values()) / len(correct_answers),
            'numerator': int(sum(correct_answers.values())), 'denominator': len(correct_answers),
            'label_origin': 'owner-delegated automated AI content review, NOT human labels',
            'ci95': _bootstrap_ci(rows, correct_answers, 'automated_semantic_correctness', iterations=2000)},
        'cases': cases, 'weak_answerable_cases': misses, 'valid_source_citation_outside_exact_gold': gold_differences,
        'raw_format': {'valid': summary['counts']['raw_schema_valid'],
                       'invalid': summary['counts']['raw_schema_invalid'],
                       'normalized_schema_valid': len(chat),
                       'policy': 'Escaping-only copies; original format failures remain failures.'},
        'grounding_measurement_limits': {
            'lexical_proxy': 'Legacy claim matching uses claim_id or token Jaccard >=0.35 against English/broad gold claims. Its grounding/leakage numbers are lexical proxies, NOT independently established semantic error rates; retained without threshold changes.',
            'observed_proxy': {key: quality['metrics'][key] for key in (
                'grounded_claim_precision', 'grounded_claim_recall', 'unsupported_claim_leakage')},
            'separate_source_review': f'{int(sum(correct_answers.values()))} unchanged published answers were independently AI reviewed against question, structured gold and source; {supported_claims} published claims have runtime support and valid citations. AI review is not human approval.',
            'gold_citation_limit': f'{len(gold_differences)} valid source citations differ from exact gold chunk identity. Exact-gold citation precision/recall are separate from source-coordinate/quote validity.'},
        'resolved_issues': ['43 derived semester annotations independently source-verified in a separate overlay; frozen v5 preserved.',
            'Exact multiline JSON-array source quotes accepted without joining rows or changing cells.',
            'Named-course credit column proof and Vietnamese minimum-percentage idiom remove 71 false application abstentions.',
            'Citation scoring excludes hidden diagnostics and includes missing gold links; lexical matching remains a separately disclosed proxy.',
            'Self-contained named subjects resolve local pronouns; distinct legal instrument identifiers no longer create false numerical conflicts. Three newly reachable outputs independently source-reviewed; prior 142 outputs unchanged.'],
        'unmeasured': {'live_provider_end_to_end_latency': 'No live generation in owner-selected Chat workflow.',
            'human_labeled_semantic_correctness': 'AI review is explicitly not human approval.',
            'abstention_reason_accuracy': 'No independently labeled gold reasons.',
            'actual_chat_model_identity': 'UI model label/settings not supplied.'},
        'exit': {'baseline_review_complete': True, 'live_runtime_exit_satisfied': False,
            'content_and_local_regression_pass': (not misses and all(p['public_response']['abstained'] for p in negatives)),
            'next_action': 'A bounded live product run is required to measure provider latency/format reliability; do not send requests automatically. Remaining weak cases are explicitly listed; no threshold or prompt tuning to manufacture PASS.'},
        'bindings': {str(path.relative_to(ROOT).as_posix()): sha(path) for path in [
            BENCHMARK, chat_path, summary_path, preflight_path, output / 'predictions.jsonl', output / 'execution.json',
            output / 'benchmark-scoring-annotations.jsonl', output / 'annotation-corrections.json', quality_path,
            ROOT / 'evaluation/results/phase8-chat-replay-baseline-20261012/baseline-review.json',
            ROOT / 'evaluation/results/phase8-chat-replay-baseline-20261012/quality-public-metrics.json',
            ROOT / 'evaluation/results/phase8-final-checks-20261012.xml',
            ROOT / 'evaluation/results/phase8-app-regression-20261012.xml',
            ROOT / 'evaluation/results/phase8-metric-final-20261012.xml',
            ROOT / 'evaluation/results/phase8-benchmark-validation-20261012.xml',
            ROOT / 'evaluation/results/phase8-chat-complete-tests-20261012.xml',
            ROOT / 'evaluation/results/phase8-remaining-fix-tests-20261012.xml',
            ROOT / 'evaluation/results/phase8-followup-regression-20261012.xml', Path(__file__)]},
    }
    write_json(output / 'baseline-review.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=OUTPUT)
    result = review(parser.parse_args().output_dir)
    print(json.dumps({'status': result['status'], **result['counts']}, indent=2))
