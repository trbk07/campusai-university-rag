"""Bind explicit negative dev source/context decisions without creating human reviews."""
from datetime import datetime, timezone
import hashlib
import re
import unicodedata

from campusai.retrieval.tokenizer_vi import source_body
from evaluation.benchmarks.human_benchmark_intake import digest_record

POLICY_TERMS = (r'hoc\s+bong|scholarship|ho\s+tro\s+hoc\s+tap|financial\s+aid',
                r'canh\s+bao|academic\s+warning|hoc\s+cai\s+thien|retak|grade\s+replacement',
                r'diem\s+trung\s+binh|gpa|dang\s+k[yi]|registration|minimum\s+credits',
                r'ngoai\s+ngu|ielts|english\s+proficiency|credits\s*per\s*semester')


def validate_review(review, rows, evidence, index_hash):
    stamp = datetime.fromisoformat(review['reviewed_at'])
    if (stamp.tzinfo is None or stamp > datetime.now(timezone.utc)
            or review.get('status') != 'source_context_reviewed_dev_only'
            or review.get('analyst') != 'Codex AI assistant'
            or review.get('owner_manual_row_review_claim') is not False
            or review.get('independent_human_review_claim') is not False
            or review.get('index_sha256') != index_hash or not review.get('method')):
        raise ValueError('negative review identity, time, method or source mismatch')
    targets = {f'human-candidate-{i:04d}' for i in range(1, 46)}
    by_id = {row['qid']: row for row in rows}
    if len(by_id) != len(rows) or not targets <= set(by_id) or any(row.get('split') != 'dev' for row in rows):
        raise ValueError('missing/duplicate negative review inputs')
    reviewed = {}
    for group in review['groups']:
        if (not group.get('category') or not group.get('reason')
                or group.get('expected_behavior') not in {'abstain', 'clarify_or_abstain'}):
            raise ValueError('negative decision requires explicit category, rationale and behavior')
        for number in group['qids']:
            qid = f'human-candidate-{number:04d}'
            if qid in reviewed or qid not in targets:
                raise ValueError('duplicate or out-of-scope negative decision')
            row = by_id[qid]
            if (row.get('split') != 'dev' or row.get('answerable') is not False
                    or row.get('gold_evidence') or row.get('context')
                    or row.get('selected_text') or row.get('document_context') not in
                    (None, {}, {'scope': 'seed_corpus_upload_fixture', 'uploaded_documents': []})
                    or row.get('filters') or not row.get('doc_ids') or row.get('release_eligible') is not False):
                raise ValueError('negative source/context eligibility changed')
            sources = sorted((doc, chunk, source) for (doc, chunk), source in evidence.items() if doc in row['doc_ids'])
            if {doc for doc, _, _ in sources} != set(row['doc_ids']):
                raise ValueError('negative source scope incomplete')
            hits = []
            bindings = []
            for doc, chunk, source in sources:
                body = source_body(source)
                normalized = ' '.join(''.join(c for c in unicodedata.normalize('NFD', body.casefold())
                                             if not unicodedata.combining(c)).replace('đ', 'd').split())
                digest = hashlib.sha256(body.encode()).hexdigest()
                bindings.append({'doc_id': doc, 'chunk_id': chunk, 'page': source['page'], 'body_sha256': digest})
                if any(re.search(pattern, normalized) for pattern in POLICY_TERMS):
                    hits.append(bindings[-1])
            reviewed[qid] = {'mode': 'explicit_scoped_source_context_negative_review',
                'record_sha256': digest_record(row), 'category': group['category'], 'reason': group['reason'],
                'expected_behavior': group['expected_behavior'], 'source_chunks': len(sources),
                'source_scope_sha256': digest_record(bindings), 'policy_term_matches': hits,
                'method_limit': 'Term scan and source/context interpretation, not an exhaustive semantic absence theorem.'}
    if set(reviewed) != targets:
        raise ValueError('all 45 negative questions require a decision')
    return reviewed
