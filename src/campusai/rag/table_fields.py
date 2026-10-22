"""Bounded admission-table lookups with explicit identity and value columns."""
from __future__ import annotations

import json
import re

from .course_credits import folded
from ..retrieval.tokenizer_vi import source_body

IDENTIFIER = r'[a-z]{1,5}\d{1,5}'


def admission_field_request(question):
    text = folded(question).strip()
    text = re.sub(r'^(?:use only (?:the )?uploaded|chi dung tai lieu da tai len) [\w.-]+\.pdf\.\s*', '', text)
    if re.search(r'\b(?:ignore|reveal|password|secret|also|unless|if|current|latest|without|under|foundation|preparatory|transfer|dung|mat khau|du bi)\b', text):
        return None
    labels = re.findall(r'\(([^()]*)\)', text)
    if any(re.search(r'\b(?:what|how|which|show|tell|give|confirm|neu|hay|va cho)\b', label) for label in labels):
        return None
    text = re.sub(r'\([^()]*\)', '', text)
    if any(c in text for c in '();\n'):
        return None
    text = ' '.join(text.strip(' .?!').split())
    if re.search(r'\b(?:and|or|but|va|hoac|voi|then)\b', text):
        return None
    patterns = (
        ('discipline', r'which national discipline code is listed for (?:admission )?programme (' + IDENTIFIER + r')'),
        ('quota', r'what is the (?:proposed )?admission quota for (' + IDENTIFIER + r')(?: [a-z -]{1,80})?(?: in the programme table)?'),
        ('quota', r'chi tieu tuyen sinh(?: du kien)?(?: nam (?:19|20)\d{2})? cua ma (' + IDENTIFIER + r') la bao nhieu'),
    )
    for kind, pattern in patterns:
        match = re.fullmatch(pattern, text)
        if match:
            return kind, match[1].upper(), tuple(re.findall(r'\b(?:19|20)\d{2}\b', text))
    return None


def admission_rows(content):
    start = content.find('{"headers"')
    if start < 0:
        return None
    try:
        table = json.loads(content[start:])
    except (ValueError, TypeError):
        return None
    if not isinstance(table, dict) or not isinstance(table.get('headers'), list) or not isinstance(table.get('rows'), list):
        return None
    if any(not isinstance(h, str) for h in table['headers']):
        return None
    headers = [folded(h) for h in table['headers']]
    identity = [i for i, h in enumerate(headers) if h in {'ma xet tuyen', 'admission code', 'programme code'}]
    discipline = [i for i, h in enumerate(headers) if re.fullmatch(r'ma nganh[1-9]?', h) or h == 'national discipline code']
    quota = [i for i, h in enumerate(headers) if h in {'chi tieu', 'chi tieu du kien', 'admission quota'}]
    # General programme tables have a national discipline column. A separate
    # foundation/transfer allocation with the same code is a different scope.
    if len(identity) != 1 or len(discipline) != 1 or len(quota) != 1 or len({*identity, *discipline, *quota}) != 3:
        return None
    result = []
    for row in table['rows']:
        if not isinstance(row, list) or len(row) != len(headers) or any(not isinstance(c, str) for c in row):
            continue
        code = row[identity[0]].strip().upper()
        if re.fullmatch(IDENTIFIER, code, re.I):
            result.append((code, row[discipline[0]].strip(), row[quota[0]].strip(), row))
    return result


def admission_candidates(question, records):
    """None means no applicable schema; [] proves no row in those tables."""
    request = admission_field_request(question)
    if request is None:
        return None
    matching, applicable = [], False
    for key, item in records.items():
        if item.get('content_type') != 'table':
            continue
        rows = admission_rows(item.get('content', ''))
        if rows is None:
            continue
        applicable = True
        if any(code == request[1] for code, *_ in rows):
            matching.append(key)
    if applicable and not matching:
        return []
    if applicable and request[2]:
        scope = admission_year_sources(records.values(), request[2])
        if not scope:
            return []
        matching.extend(key for key, item in records.items() if item in scope)
    return list(dict.fromkeys(matching)) if applicable else None


def admission_year_sources(items, years):
    """A document heading proves its admission year; filenames do not."""
    found = []
    observed = set()
    for item in items:
        if item.get('page') != 1 or item.get('content_type') != 'text':
            continue
        body = folded(source_body(item, decode_tables=False))
        match = re.match(r'^(?:thong tin|de an|ke hoach) tuyen sinh nam ((?:19|20)\d{2})\b', body)
        if match:
            observed.add(match[1])
            found.append(item)
    return found if observed == set(years) else []


def deterministic_admission_field(question, results, language, *, calibrator=None):
    request = admission_field_request(question)
    if request is None or len({r.doc_id for r in results}) != 1:
        return None
    named = {name.casefold() for name in re.findall(r'[\w.-]+\.pdf\b', question, re.I)}
    available = {str(r.metadata.get('source_name', '')).casefold() for r in results}
    if named and not named <= available:
        return None
    kind, code, years = request
    if years and not admission_year_sources(({'page': r.page, 'content': r.content,
        'content_type': r.content_type} for r in results), years):
        return None
    matches = [(r, row, discipline if kind == 'discipline' else quota)
               for r in results if r.content_type == 'table'
               for found, discipline, quota, row in (admission_rows(r.content) or []) if found == code]
    if not matches:
        return None
    from .grounding import Citation, GroundedAnswer, _abstention, validate_citation
    from .claims import Claim
    from .confidence import score_confidence
    values = {value for _, _, value in matches}
    if len(values) != 1:
        return _abstention('conflicting_evidence', language=language)
    value = next(iter(values))
    if not value.isascii() or not value.isdigit() or not 1 <= len(value) <= (9 if kind == 'discipline' else 6):
        return _abstention('unsupported_claim', language=language)
    result, row, _ = matches[0]
    quote = json.dumps(row, ensure_ascii=False)
    if len(quote) > 1200:
        return _abstention('context_budget_exceeded', language=language)
    citation = Citation(result.chunk_id, result.doc_id, result.page, quote,
        ' > '.join(result.metadata.get('heading_path', [])), result.metadata.get('source_name', ''),
        tuple(result.metadata.get('page_range', [result.page, result.page])),
        result.metadata.get('table_id', ''), result.metadata.get('source_hash', ''))
    if not validate_citation(citation, result, require_quote=True).valid:
        return _abstention('invalid_citation', language=language)
    if language.casefold().startswith('en'):
        answer = f'Programme {code} has ' + (f'national discipline code {value}.' if kind == 'discipline' else f'an admission quota of {value}.')
    else:
        answer = (f'Mã ngành của mã xét tuyển {code} là {value}.' if kind == 'discipline'
                  else f'Chỉ tiêu tuyển sinh của mã {code} là {value}.')
    # This is a checked source-column projection, not a provider support label.
    claim = Claim('1', answer, 'numeric_fact', 1, (result.chunk_id,), 'supported', 1.0, (result.chunk_id,), False)
    confidence = score_confidence(retrieval_support=max(0., min(1., result.score)),
        claim_entailment=1., citation_completeness=1., calibrator=calibrator)
    return GroundedAnswer(answer=answer, citations=(citation,), confidence=confidence.label,
        abstained=False, claims=(claim,), evidence_status='found', confidence_score=confidence.score,
        raw_confidence_score=confidence.raw_score, policy_version=confidence.policy_version)


_CURRICULUM_BLOCKS = {
    'general': (r'khối kiến thức chung', r'\b(?:general|common) knowledge block\b'),
    'field': (r'khối kiến thức theo lĩnh vực', r'\bfield knowledge block\b'),
    'discipline': (r'khối kiến thức theo khối ngành', r'\bknowledge block by discipline\b'),
    'discipline_group': (r'khối kiến thức theo nhóm ngành', r'\bknowledge block by discipline group\b'),
    'major': (r'khối kiến thức ngành', r'\bmajor knowledge block\b'),
}


def _curriculum_block_request(question):
    text = folded(question)
    if (not re.search(r'\b(?:credit|credits|tin chi)\b', text)
            or re.search(r'\b(?:ignore|reveal|password|secret|latest|current|mat khau)\b', text)):
        return None
    matches = [kind for kind, (_source_label, english_label) in _CURRICULUM_BLOCKS.items()
               if re.search(english_label, text)]
    if len(matches) == 1:
        return matches[0]
    # Accented Vietnamese labels are normalized by ``folded`` above.
    vi_labels = {
        'general': r'khoi kien thuc chung',
        'field': r'khoi kien thuc theo linh vuc',
        'discipline': r'khoi kien thuc theo khoi nganh',
        'discipline_group': r'khoi kien thuc theo nhom nganh',
        'major': r'khoi kien thuc nganh',
    }
    matches = [kind for kind, label in vi_labels.items() if re.search(label, text)]
    return matches[0] if len(matches) == 1 else None


def deterministic_curriculum_block_total(question, results, language, *, calibrator=None):
    """Answer a narrowly named programme-summary total from its labelled source line."""
    kind = _curriculum_block_request(question)
    if kind is None or not results or len({result.doc_id for result in results}) != 1:
        return None
    named = {name.casefold() for name in re.findall(r'[\w.-]+\.pdf\b', question, re.I)}
    available = {str(result.metadata.get('source_name', '')).casefold() for result in results}
    if named and not named <= available:
        return None
    label = _CURRICULUM_BLOCKS[kind][0]
    matches = []
    for result in results:
        if result.content_type != 'text':
            continue
        body = source_body({'content': result.content}, decode_tables=False)
        match = re.search(r'(?P<quote>[-\u2022*]?\s*' + label
                          + r'\s*:\s*\n\s*(?P<value>\d{1,3})\s*(?:tín\s*chỉ|credits?))',
                          body, re.I)
        if match:
            matches.append((result, match.group('value'), match.group('quote').strip()))
    if not matches:
        return None
    values = {value for _result, value, _quote in matches}
    from .grounding import Citation, GroundedAnswer, _abstention, validate_citation
    from .claims import Claim
    from .confidence import score_confidence
    if len(values) != 1:
        return _abstention('conflicting_evidence', language=language)
    result, value, quote = max(matches, key=lambda item: item[0].score)
    citation = Citation(result.chunk_id, result.doc_id, result.page, quote,
        ' > '.join(result.metadata.get('heading_path', [])), result.metadata.get('source_name', ''),
        tuple(result.metadata.get('page_range', [result.page, result.page])),
        result.metadata.get('table_id', ''), result.metadata.get('source_hash', ''))
    if not validate_citation(citation, result, require_quote=True).valid:
        return _abstention('invalid_citation', language=language)
    assertions = re.findall(r'(?<!\w)\d{1,3}(?!\w)', question)
    asserted = assertions[0] if len(assertions) == 1 else None
    matches_assertion = asserted is None or asserted == value
    label_en = {'general':'general knowledge block','field':'field knowledge block',
        'discipline':'knowledge block by discipline','discipline_group':'knowledge block by discipline group',
        'major':'major knowledge block'}[kind]
    if language.casefold().startswith('en'):
        answer = (f"The {label_en} requires {value} credits." if asserted is None
                  else (f"Yes. The source lists {value} credits for the {label_en}." if matches_assertion
                        else f"No. The source lists {value} credits for the {label_en}, not {asserted}."))
    else:
        label_vi = {'general':'khối kiến thức chung','field':'khối kiến thức theo lĩnh vực',
            'discipline':'khối kiến thức theo khối ngành','discipline_group':'khối kiến thức theo nhóm ngành',
            'major':'khối kiến thức ngành'}[kind]
        answer = (f'Tài liệu ghi {label_vi} là {value} tín chỉ.' if asserted is None
                  else (f'Đúng. Tài liệu ghi {label_vi} là {value} tín chỉ.' if matches_assertion
                        else f'Không. Tài liệu ghi {label_vi} là {value} tín chỉ, không phải {asserted}.'))
    confidence = score_confidence(retrieval_support=max(0., min(1., result.score)),
        claim_entailment=1., citation_completeness=1., calibrator=calibrator)
    claim = Claim('curriculum-block-total', quote, 'numeric_fact', 1, (result.chunk_id,),
        'supported', 1.0, (result.chunk_id,), False)
    return GroundedAnswer(answer=answer, citations=(citation,), confidence=confidence.label,
        abstained=False, claims=(claim,), evidence_status='found', confidence_score=confidence.score,
        raw_confidence_score=confidence.raw_score, policy_version=confidence.policy_version)
