"""Source-checked, owner-directed dev questions about absent curriculum fields.

Only course facts already named in the retained parent dev split are used.
These questions are deliberately dev-only; no fresh heldout claim is made.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re

from campusai.retrieval.routing import detected_course_codes
from campusai.retrieval.tokenizer_vi import source_body
from evaluation.common.release_artifacts import read_json, sha256
from .human_benchmark_intake import digest_record
from .owner_generation import course_facts, generated_row, plain

FACETS = {
    'fee_waiver': r'\b(?:hoc phi|le phi|tuition|fees?|waiv\w*|mien phi|charges?|payment)\b',
    'exam_schedule': r'\b(?:lich thi|ngay thi|exam(?:ination)? (?:date|schedule|time))\b',
    'teaching_room': r'\b(?:phong hoc|giang duong|classrooms?|lecture room)\b',
}


def rows_at(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def absence_proof(facts: list[dict], facet: str, evidence: dict) -> dict:
    if facet not in FACETS or len(facts) != 2:
        raise ValueError('two source course facts and a supported absence facet required')
    actual = {digest_record(f) for f in course_facts(evidence)}
    if (any(digest_record(f) not in actual for f in facts)
            or len({f['code'] for f in facts}) != 2 or len({f['doc_id'] for f in facts}) != 1):
        raise ValueError('dev challenge course facts differ from source')
    doc = facts[0]['doc_id']
    scoped = {chunk: item for (d, chunk), item in evidence.items() if d == doc}
    if not scoped or any(item.get('metadata', {}).get('document_type') != 'curriculum'
                         for item in scoped.values()):
        raise ValueError('absence audit requires a scoped curriculum, not a mixed document')
    bodies = [source_body(item) for item in scoped.values()]
    normalized = plain(' '.join(bodies)).replace('đ', 'd')
    if re.search(FACETS[facet], normalized):
        raise ValueError('requested field has a source mention; absence cannot be asserted')
    return {'method': 'scoped_curriculum_body_field_absence_v1', 'facet': facet,
            'checked_pattern': FACETS[facet], 'doc_ids': [doc], 'source_chunks': len(scoped),
            # Retain hashes of original source serialization for existing v1
            # proofs; absence itself is checked on decoded source cells above.
            'body_sha256': {chunk: digest_record({'body': source_body(item, decode_tables=False)})
                            for chunk, item in sorted(scoped.items())},
            'meaning': 'The supplied curriculum contains course identities and credits but no requested policy/schedule/room field. No institution-wide fact is inferred.'}


def question(spec: dict) -> str:
    a, b = spec['facts']
    courses = f"{a['name']} ({a['code']}) và {b['name']} ({b['code']})"
    if spec['facet'] == 'fee_waiver':
        return (f'Theo chương trình này, nếu đăng ký học cùng {courses} thì có được miễn '
                'lệ phí đăng ký riêng cho hai học phần này không? Mình cần điều kiện miễn phí cụ thể.')
    if spec['facet'] == 'exam_schedule':
        return (f'Nếu mình thi {courses} trong cùng học kỳ, hai môn có trùng ngày thi không '
                'và giờ thi của từng môn được ấn định thế nào trong tài liệu này?')
    if spec['facet'] == 'teaching_room':
        return (f'Mình học {courses} cùng kỳ, hai môn tổ chức ở phòng hoặc giảng đường nào '
                'và có phải đổi phòng giữa hai tiết học không theo chương trình này?')
    raise ValueError('unknown dev absence facet')


def extension_row(spec: dict, authorization: dict) -> dict:
    # Reuse the declared owner/AI provenance; the semantic fields below describe
    # an absent-field request rather than a positive credit calculation.
    row = generated_row({**spec, 'kind': 'sum'}, authorization)
    row.update(question=question(spec), answerable=False, gold_evidence=[], expected_claims=[],
               expected_behavior='abstain', source_validation=spec,
               template_group='dev-absent-curriculum-field-' + spec['facet'],
               tags=['natural', 'table', 'exact_code', 'multi_hop', 'hard', 'negative', 'abstention'],
               allocation_reason='dev-only source facts already named in parent dev; no new heldout claim')
    return row


def load_dev_extension(benchmark: Path, index: Path, policy: dict, evidence: dict) -> tuple[dict | None, dict]:
    auth_path = benchmark/'phase7_dev_generation_authorization.json'
    if not auth_path.exists():
        return None, {}
    auth = read_json(auth_path)
    stamp = datetime.fromisoformat(auth['recorded_at'])
    if (auth.get('profile') != 'personal_owner_source_checked_ai'
            or auth.get('owner_identity') != policy.get('owner_identity')
            or auth.get('approval_source') != 'project_owner_chat_instruction'
            or auth.get('approval_statement') != 't duyệt hết nên bạn cứ nhập tên tác giải là t'
            or auth.get('generation_statement') != 'nếu k có thì tự tạo đi, t cho phép'
            or auth.get('independent_human_review_claim') is not False
            or auth.get('dev_only') is not True or auth.get('new_heldout_claim') is not False
            or stamp.tzinfo is None or stamp > datetime.now(timezone.utc)
            or auth.get('review_policy_sha256') != sha256(benchmark/'phase7_review_policy.json')
            or auth.get('index_sha256') != sha256(index/'manifest.json')
            or auth.get('parent_confirmation_sha256') != sha256(benchmark/'phase7_owner_confirmation.json')):
        raise ValueError('invalid dev extension authorization or source binding')
    bank_path = benchmark/'owner_generated_dev_source_bank.json'
    parent_path = benchmark/'dev_extension_parent_dev.jsonl'
    if (auth.get('source_bank_sha256') != sha256(bank_path)
            or auth.get('parent_dev_sha256') != sha256(parent_path)):
        raise ValueError('dev extension source bank or retained parent changed')
    parent = rows_at(parent_path)
    from .owner_review import load_confirmation, confirmed_row
    confirmation, original = load_confirmation(benchmark)
    expected_parent = [{**confirmed_row(row, confirmation), 'split': 'dev'} for row in original]
    if parent != expected_parent:
        raise ValueError('dev extension anchors are not the confirmed parent dev records')
    dev_codes = {code for row in parent for code in detected_course_codes(row['question'])}
    bank = read_json(bank_path)
    if bank.get('dev_only') is not True or not isinstance(bank.get('records'), list) or not bank['records']:
        raise ValueError('dev-only source bank required')
    expected = {}
    for spec in bank['records']:
        if (spec.get('kind') != 'dev_absent_field' or spec.get('split') != 'dev'
                or not str(spec.get('qid', '')).startswith('human-dev-evidence-')
                or any(f['code'] not in dev_codes for f in spec['facts'])
                or spec.get('absence_proof') != absence_proof(spec['facts'], spec['facet'], evidence)):
            raise ValueError('dev extension absent-field proof or allocation differs from source')
        row = extension_row(spec, auth)
        if row['qid'] in expected:
            raise ValueError('duplicate dev extension qid')
        expected[row['qid']] = row
    return auth, expected
