"""Questions bound to explicit curriculum column roles and scoped source proofs.

This schema validates facts and exports. It does not approve historical exposure
or allocate heldout data. Owner/AI provenance uses the standing review profile.
"""
from __future__ import annotations

import hashlib
import re

from campusai.retrieval.tokenizer_vi import source_body
from .human_benchmark_intake import digest_record
from .source_course_rows import source_course_rows
from .source_proposals import alias_key, course_aliases

KINDS = frozenset({'source_course_credit', 'source_course_sum', 'source_course_absent_field',
                   'source_course_compare', 'source_course_absent_field_single'})
FACETS = {
    'fee_waiver': r'\b(?:hoc phi|le phi|tuition|fees?|waiv\w*|mien phi|charges?|payment)\b',
    'exam_schedule': r'\b(?:lich thi|ngay thi|gio thi|ca thi|thoi gian thi|exam(?:ination)?(?:s)?(?: date| schedule| time)?)\b',
    'teaching_room': r'\b(?:phong hoc|giang duong|classrooms?|lecture rooms?)\b',
}


def _facts_match(facts: list[dict], evidence: dict, actual: set[str] | None = None,
                 *, distinct_documents: bool = False) -> None:
    actual = actual if actual is not None else {digest_record(f) for f in source_course_rows(evidence)}
    if (not isinstance(facts, list) or not facts or any(not isinstance(f, dict) for f in facts)
            or any(digest_record(f) not in actual for f in facts)
            or len({f['doc_id'] if distinct_documents else f['code'] for f in facts}) != len(facts)):
        raise ValueError('explicit course facts differ from frozen source')


def absence_proof(facts: list[dict], facet: str, evidence: dict, index_sha256: str,
                  *, actual: set[str] | None = None) -> dict:
    """Check every decoded source chunk in every requested curriculum document."""
    return _absence_proof(facts, facet, evidence, index_sha256, actual=actual, count=2)


def single_course_absence_proof(facts: list[dict], facet: str, evidence: dict, index_sha256: str,
                               *, actual: set[str] | None = None) -> dict:
    """Bind a single-course negative to the complete supplied curriculum."""
    return _absence_proof(facts, facet, evidence, index_sha256, actual=actual, count=1)


def _absence_proof(facts: list[dict], facet: str, evidence: dict, index_sha256: str,
                   *, actual: set[str] | None, count: int) -> dict:
    _facts_match(facts, evidence, actual)
    if (not isinstance(facet, str) or facet not in FACETS or len(facts) != count or not isinstance(index_sha256, str)
            or not re.fullmatch(r'[a-f0-9]{64}', index_sha256)):
        raise ValueError('required course fact count, supported facet and physical index binding required')
    docs = sorted({f['doc_id'] for f in facts})
    scoped = {key: item for key, item in evidence.items() if key[0] in docs}
    if (not scoped or any(item.get('metadata', {}).get('document_type') != 'curriculum'
                          for item in scoped.values())):
        raise ValueError('field absence requires complete scoped curriculum documents')
    bodies = {key: source_body(item) for key, item in scoped.items()}
    if any(re.search(FACETS[facet], alias_key(body)) for body in bodies.values()):
        raise ValueError('source mentions the requested field; absence cannot be asserted')
    method = ('explicit_course_scoped_field_absence_v1' if count == 2
              else 'explicit_single_course_scoped_field_absence_v1')
    return {'method': method, 'facet': facet,
            'index_sha256': index_sha256, 'doc_ids': docs, 'source_chunks': len(scoped),
            'checked_pattern': FACETS[facet],
            'body_sha256': {doc: {chunk: hashlib.sha256(body.encode('utf8')).hexdigest()
                                 for (d, chunk), body in sorted(bodies.items()) if d == doc}
                            for doc in docs},
            'meaning': 'Only the supplied curriculum documents lack this requested field. '
                       'No institution-wide policy, current schedule or room assignment is inferred.'}


def course_context(fact: dict, evidence: dict) -> dict:
    metadata = evidence[fact['doc_id'], fact['chunk_id']].get('metadata', {})
    program, source = metadata.get('program'), metadata.get('source_name')
    if not isinstance(program, str) or not program.strip() or not isinstance(source, str) or not source.strip():
        raise ValueError('source context needs verified program and source name')
    version = metadata.get('version')
    label = program + (f" ({version})" if version else f" ({source})")
    return {'doc_id': fact['doc_id'], 'program': program,
            'version': version, 'source_name': source, 'label': label}


def comparison_contexts(facts: list[dict], evidence: dict) -> list[dict]:
    """Use frozen metadata to identify two sources, without asserting equivalence."""
    _facts_match(facts, evidence, distinct_documents=True)
    if len(facts) != 2:
        raise ValueError('comparison requires two distinct source documents')
    contexts = [course_context(fact, evidence) for fact in facts]
    if contexts[0]['label'] == contexts[1]['label']:
        raise ValueError('comparison sources cannot be identified unambiguously')
    return contexts


def validate_spec(spec: dict, evidence: dict, index_sha256: str,
                  *, actual: set[str] | None = None) -> None:
    allowed = {'qid','family','kind','facts','display_names','template_variant',
               'include_codes','facet','absence_proof','dev_only','comparison_contexts',
               'context_mode','context_binding'}
    if (not isinstance(spec, dict) or set(spec) - allowed or spec.get('kind') not in KINDS
            or not isinstance(spec.get('qid'), str) or not spec['qid'].startswith('human-') or len(spec['qid']) <= 6
            or not isinstance(spec.get('family'), str) or not spec['family'].strip()
            or type(spec.get('template_variant')) is not int or spec['template_variant'] not in range(4)
            or type(spec.get('include_codes')) is not bool or type(spec.get('dev_only')) is not bool):
        raise ValueError('invalid explicit source question schema')
    if not isinstance(index_sha256, str) or not re.fullmatch(r'[a-f0-9]{64}', index_sha256):
        raise ValueError('physical index binding required for explicit source questions')
    facts = spec.get('facts')
    comparison = spec['kind'] == 'source_course_compare'
    _facts_match(facts, evidence, actual, distinct_documents=comparison)
    if any(evidence[(f['doc_id'],f['chunk_id'])].get('metadata', {}).get('document_type') != 'curriculum'
           for f in facts):
        raise ValueError('source question requires a curriculum document')
    count = 1 if spec['kind'] in {'source_course_credit', 'source_course_absent_field_single'} else 2
    names = spec.get('display_names')
    if (len(facts) != count or not isinstance(names, list) or len(names) != count
            or any(not isinstance(name, str) or alias_key(name) not in course_aliases(fact)
                   for name, fact in zip(names, facts))):
        raise ValueError('question course count or displayed name differs from source')
    if spec['kind'] in {'source_course_absent_field', 'source_course_absent_field_single'}:
        prove = single_course_absence_proof if count == 1 else absence_proof
        proof = prove(facts, spec.get('facet'), evidence, index_sha256, actual=actual)
        if spec.get('absence_proof') != proof:
            raise ValueError('scoped absent-field proof changed')
    elif 'facet' in spec or 'absence_proof' in spec:
        raise ValueError('positive source question cannot carry an absence assertion')
    if comparison:
        if spec.get('comparison_contexts') != comparison_contexts(facts, evidence):
            raise ValueError('comparison context differs from frozen source')
    elif 'comparison_contexts' in spec:
        raise ValueError('non-comparison question cannot carry comparison context')
    if 'context_mode' in spec or 'context_binding' in spec:
        if (spec['kind'] != 'source_course_credit' or spec['include_codes'] is not True
                or spec.get('context_mode') not in {'history', 'selection'}
                or spec.get('context_binding') != course_context(facts[0], evidence)):
            raise ValueError('contextual course request differs from frozen source topic')


def render_question(spec: dict) -> str:
    names = [f"{name} ({fact['code']})" if spec['include_codes'] else name
             for name, fact in zip(spec['display_names'], spec['facts'])]
    variant, kind = spec['template_variant'], spec['kind']
    a = names[0]
    if kind == 'source_course_credit':
        if spec.get('context_mode'):
            return f"{spec['facts'][0]['code']}: môn này mấy tín chỉ trong chương trình đang chọn?"
        return (
            f'Tra bảng học phần trong tài liệu được cung cấp: môn {a} có bao nhiêu tín chỉ?',
            f'How many credits does the supplied curriculum assign to {a}?',
            f'Mình cần biết số tín chỉ của {a}; hãy lấy giá trị từ bảng trong tài liệu này.',
            f'Locate {a} in the supplied course table and report its credit count.',
        )[variant]
    if kind == 'source_course_absent_field_single':
        vi, en = {
            'fee_waiver': ('điều kiện miễn lệ phí đăng ký', 'registration fee waiver conditions'),
            'exam_schedule': ('ngày và giờ thi', 'exam date and time'),
            'teaching_room': ('phòng học được phân công', 'assigned classroom'),
        }[spec['facet']]
        return (
            f'Chỉ dựa vào tài liệu chương trình được cung cấp, {vi} của {a} là gì?',
            f'Using only the supplied curriculum, what is the {en} for {a}?',
            f'Mình tra {a} trong tài liệu chương trình này; tài liệu ghi {vi} cụ thể thế nào?',
            f'Does the provided curriculum specify the {en} for {a}? Give that information if it does.',
        )[variant]
    b = names[1]
    if kind == 'source_course_compare':
        left, right = [context['label'] for context in spec['comparison_contexts']]
        return (
            f'Tra riêng dòng {a} trong {left} và dòng {b} trong {right}. Mỗi dòng ghi mấy tín chỉ, và giá trị ở tài liệu thứ hai trừ tài liệu thứ nhất bằng bao nhiêu?',
            f'Compare the credit entry for {a} in {left} with {b} in {right}. Report each value and the second minus the first.',
            f'Mình đang đối chiếu hai tài liệu: {left} có {a}, còn {right} có {b}. Hãy lấy tín chỉ từng dòng rồi tính chênh lệch giá trị sau trừ trước.',
            f'Use both sources: {a} from {left}, and {b} from {right}. What credits does each row show, and what is their difference (second minus first)?',
        )[variant]
    if kind == 'source_course_sum':
        return (
            f'Theo các dòng học phần trong tài liệu được cung cấp, {a} và {b} mỗi môn có bao nhiêu tín chỉ, và cộng hai môn được bao nhiêu?',
            f'Using the supplied course rows, give the credits for {a} and {b} separately, then calculate their combined total.',
            f'Mình chọn cả {a} lẫn {b}. Hãy tra số tín chỉ từng môn trong tài liệu này và tính tổng của hai môn.',
            f'Find {a} and {b} in the provided curricula. What credit count is listed for each, and what is their sum?',
        )[variant]
    if kind == 'source_course_absent_field':
        fields = {
            'fee_waiver': ('điều kiện miễn lệ phí đăng ký', 'conditions for waiving course registration fees'),
            'exam_schedule': ('ngày và giờ thi', 'exam dates and times'),
            'teaching_room': ('phòng học được phân công', 'assigned teaching rooms'),
        }
        vi, en = fields[spec['facet']]
        return (
            f'Tài liệu chương trình được cung cấp quy định {vi} cho {a} và {b} cụ thể thế nào?',
            f'According to the supplied curricula, what are the {en} for {a} and {b}?',
            f'Mình đang tra tài liệu chương trình này cho {a} và {b}; tài liệu ghi {vi} của từng môn là gì?',
            f'Use only the provided curriculum documents to state the {en} for each of {a} and {b}.',
        )[variant]
    raise ValueError('unsupported explicit source question kind')


def generated_row(spec: dict, authorization: dict) -> dict:
    # Reuse attribution and gold/claim construction without replacing the
    # legacy fact schema or weakening its historical digest checks.
    from .owner_generation import generated_row as legacy_row
    positive = spec['kind'] not in {'source_course_absent_field', 'source_course_absent_field_single'}
    base_kind = 'credit' if len(spec['facts']) == 1 else 'sum'
    row = legacy_row({**spec, 'kind': base_kind}, authorization)
    hard = base_kind == 'sum'
    tags = ['natural','table','hard','multi_hop'] if hard else ['natural','table','easy']
    if spec['include_codes']:
        tags.append('exact_code')
    if not positive:
        tags.extend(['negative','abstention'])
    row.update(question=render_question(spec), source_validation=spec, tags=tags,
               answerable=positive, expected_behavior='answer_grounded' if positive else 'abstain',
               gold_evidence=row['gold_evidence'] if positive else [],
               expected_claims=row['expected_claims'] if positive else [])
    if spec['kind'] == 'source_course_compare':
        row['tags'].append('multi_document')
        row['expected_claims'] = [
            {**{key: fact[key] for key in ('doc_id', 'chunk_id', 'page', 'credits')},
             'course_code': fact['code']}
            for fact in spec['facts']]
        row['expected_claims'].append({'credit_difference_second_minus_first':
                                       spec['facts'][1]['credits'] - spec['facts'][0]['credits']})
    if spec.get('context_mode'):
        topic = f"Mình đang xem {spec['context_binding']['label']}; dòng học phần {names_for_context(spec)}."
        row.update(requires_context=True)
        if spec['context_mode'] == 'selection':
            row['selected_text'] = topic
        else:
            row['history'] = [{'role': 'user', 'content': topic}]
        row['tags'].extend(['contextual', 'contextual_followup'])
    return row


def names_for_context(spec: dict) -> str:
    return f"{spec['display_names'][0]} ({spec['facts'][0]['code']})"


def export_matches(expected: dict, row: dict) -> bool:
    """New dev-only source records may never be exported to heldout splits."""
    if expected.get('source_validation', {}).get('dev_only') is True and row.get('split') != 'dev':
        return False
    return {**expected, 'split': row.get('split')} == row
