"""Extend the prior source rubric with attributable scoped negative review."""
from __future__ import annotations

import argparse
from pathlib import Path
import json

from evaluation.benchmarks.dev_inheritance import rows_at
from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence
from evaluation.benchmarks.phase7_negative_review import validate_review
from evaluation.common.release_artifacts import read_json, sha256, write_json
from scripts.benchmarks.build_phase7_dev_rubric import build, BASE, INDEX


def reviewed_rubric():
    report = build()
    path = BASE / 'negative_review_decisions.json'
    review = read_json(path)
    dev = BASE / 'packet/human_retrieval_dev.jsonl'
    if review.get('dev_sha256') != sha256(dev):
        raise ValueError('negative decisions do not bind the current dev bytes')
    authority = Path(review['authorization_path'])
    authorization = read_json(authority)
    if (sha256(authority) != review['authorization_sha256']
            or not authorization.get('delegated_decision_approval_statement')
            or authorization.get('decision_analyst') != review['analyst']):
        raise ValueError('negative review authority mismatch')
    decisions = validate_review(review, rows_at(dev), frozen_evidence(INDEX), sha256(INDEX / 'manifest.json'))
    old_mode = 'inherited_f0_negative_label_not_new_corpus_semantic_audit'
    if report['review_modes'].pop(old_mode) != len(decisions):
        raise ValueError('negative coverage differs from the prior source rubric')
    report['review_modes']['explicit_scoped_source_context_negative_review'] = len(decisions)
    for qid, decision in decisions.items():
        report['row_reviews'][qid].update(decision)
    report.update(status='DEV_SOURCE_CLAIMS_AND_SCOPED_NEGATIVE_CONTEXT_REVIEWED',
                  negative_review_at=review['reviewed_at'], negative_review_method=review['method'])
    for bound in (path, authority, Path(__file__), Path('evaluation/benchmarks/phase7_negative_review.py')):
        report['bindings'][bound.as_posix()] = sha256(bound)
    report['limitations'][0] = ('45 historical negative labels now have explicit delegated AI source/context decisions. '
        'The method uses scoped source searches and interpretation; it does not claim a mechanical proof of every semantic absence or an independent human review.')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    report = reviewed_rubric()
    if args.verify:
        if read_json(args.output) != report:
            raise ValueError('reviewed rubric replay mismatch')
    elif args.output.exists():
        raise FileExistsError(args.output)
    else:
        write_json(args.output, report)
    print(json.dumps({key: report[key] for key in ('status', 'rows', 'claim_count', 'review_modes')}))


if __name__ == '__main__':
    main()
