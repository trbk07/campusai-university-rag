"""Prove course-credit arithmetic using explicitly headed source rows."""
from __future__ import annotations

import json
import re

from .course_credits import COURSE_CODE, course_code_key, folded, headed_credit_rows

CODE = COURSE_CODE
CODE_LIST = CODE + r'(?:\s*(?:,|\+|va|and)\s*' + CODE + r')+'


def deterministic_single_credit(question, results, language, *, calibrator=None):
    """Answer a bounded single-column lookup from a unique headed source row.

    Match the complete request, so extra facts, conditions and instructions
    cannot disappear when a local source lookup answers it.
    """
    text = folded(question).strip()
    text = re.sub(r'^use only (?:the )?uploaded [\w.-]+\.pdf\.\s*', '', text)
    text = re.sub(r'^read (?:the )?[^:;.!?]{1,60}\brow:\s*', '', text).strip(' .?!')
    if re.search(r'\b(?:and|or|but|if|unless|not|current|latest|today|with|without)\b', text):
        return None
    if re.search(r'\b(?:19|20|21)\d{2}\b', text):
        return None
    scope = r'(?: in (?:the )?[\w -]{1,100}(?:table|progression|curriculum))?'
    patterns = (r'how many credits does (' + CODE + r') (?:carry|have)' + scope,
                r'how many credits are (?:assigned|allocated) to (' + CODE + r')' + scope,
                r'(?:mon |hoc phan )?(' + CODE + r') co bao nhieu tin chi')
    match = next((m for pattern in patterns if (m := re.fullmatch(pattern, text))), None)
    if match is None:
        return None
    code = course_code_key(match[1])
    parts = source_sum((code,), results)
    if not parts:
        return None
    _code, value, result, row = parts[0]
    from .grounding import Citation, validate_citation, _grounding_finalize
    quote = json.dumps(row, ensure_ascii=False)
    if len(quote) > 1200:
        return None
    citation = Citation(result.chunk_id, result.doc_id, result.page, quote,
                        ' > '.join(result.metadata.get('heading_path', [])),
                        result.metadata.get('source_name', ''),
                        tuple(result.metadata.get('page_range', [result.page, result.page])),
                        result.metadata.get('table_id', ''), result.metadata.get('source_hash', ''))
    if not validate_citation(citation, result, require_quote=True).valid:
        return None
    answer = f'Course {code} has {value} credits.'
    if not language.casefold().startswith('en'):
        # Keep the established bilingual claim support grammar.
        answer = f'M\u00f4n {code} c\u00f3 {value} t\u00edn ch\u1ec9.'
    payload = {'claims': [{'claim_id': '1', 'text': answer, 'type': 'numeric_fact',
                           'citation_ids': [result.chunk_id]}]}
    return _grounding_finalize(answer, (citation,), payload, results, language, calibrator=calibrator)


def requested_sum_codes(question):
    text = folded(question).strip(' ?.!')
    patterns = [r'tong(?: so)? tin chi(?: cua)? (' + CODE_LIST + r')(?: la bao nhieu)?',
                r'(?:what is the )?(?:total|sum)(?: number)?(?: of)? credits(?: for| of) (' + CODE_LIST + r')']
    match = next((m for pattern in patterns if (m := re.fullmatch(pattern, text))), None)
    if not match:
        return None
    codes = [course_code_key(code) for code in re.findall(CODE, match[1])]
    if len(codes) > 10 or len(codes) != len(set(codes)):
        return ()
    return tuple(codes)


def source_sum(codes, evidence):
    if not codes:
        return None
    parts = []
    for code in codes:
        matches = [(record, value, row) for record in evidence
                   for found, value, row in (headed_credit_rows(record.content) or []) if found == code]
        values = {value for _record, value, _row in matches}
        if len(values) != 1 or None in values:
            return None
        record, value, row = matches[0]
        parts.append((code, value, record, row))
    return parts


def credit_sum_claim_support(text, evidence):
    normalized = folded(text)
    match = (re.fullmatch(r'tong so tin chi cua (' + CODE_LIST + r') la (\d+)[.!]?', normalized)
             or re.fullmatch(r'total credits for (' + CODE_LIST + r') are (\d+)[.!]?', normalized))
    if not match:
        return None
    codes = tuple(course_code_key(code) for code in re.findall(CODE, match[1]))
    if len(codes) != len(set(codes)) or len(codes) > 10:
        return (False, ())
    parts = source_sum(codes, evidence)
    if parts is None:
        return (False, ())
    return (sum(value for _code, value, _record, _row in parts) == int(match[2]),
            tuple(dict.fromkeys(record.chunk_id for _code, _value, record, _row in parts)))


def credit_difference_claim_support(text, evidence):
    """Check both ordered operands from the two directly cited source rows."""
    value = folded(text)
    match = (re.fullmatch(r'credit difference for (' + CODE + r') minus (' + CODE
        + r') is (\d{1,6})\s*-\s*(\d{1,6})\s*=\s*(-?\d{1,6}) credits?[.!]?', value)
        or re.fullmatch(r'chenh lech tin chi cua (' + CODE + r') tru (' + CODE
        + r') la (\d{1,6})\s*-\s*(\d{1,6})\s*=\s*(-?\d{1,6}) tin chi[.!]?', value))
    if not match:
        if re.search(r'\b(?:difference|chenh lech)\b', value) and re.search(r'\b(?:credits?|tin chi)\b', value):
            return False, ()
        return None
    if len(evidence) != 2 or evidence[0].chunk_id == evidence[1].chunk_id:
        return False, ()
    left, right = course_code_key(match[1]), course_code_key(match[2])
    if left == right and evidence[0].doc_id == evidence[1].doc_id:
        return False, ()
    operands = [int(match[3]), int(match[4])]
    for code, record, operand in zip((left, right), evidence, operands):
        rows = headed_credit_rows(record.content)
        values = {v for found, v, _row in (rows or []) if found == code}
        if values != {operand}:
            return False, ()
    return (operands[0] - operands[1] == int(match[5]), tuple(r.chunk_id for r in evidence))


def deterministic_credit_sum(question, results, language='vi', *, calibrator=None):
    """Return None for unrelated intent; insufficient sums fail closed."""
    codes = requested_sum_codes(question)
    if codes is None:
        return None
    # Lazy imports keep the source arithmetic independent of the answer types.
    from .grounding import Citation, _abstention, _grounding_finalize, validate_citation
    parts = source_sum(codes, results)
    if parts is None:
        return _abstention('no_relevant_evidence')
    citations, claims = {}, []
    english = language.casefold().startswith('en')
    for index, (code, value, record, row) in enumerate(parts, 1):
        cite = Citation(record.chunk_id, record.doc_id, record.page,
                        json.dumps(row, ensure_ascii=False),
                        ' > '.join(record.metadata.get('heading_path', [])),
                        record.metadata.get('source_name', ''),
                        tuple(record.metadata.get('page_range', [record.page, record.page])),
                        record.metadata.get('table_id', ''), record.metadata.get('source_hash', ''))
        if not validate_citation(cite, record, require_quote=True).valid:
            return _abstention('citation_not_in_evidence')
        citations[record.chunk_id] = cite
        claims.append({'claim_id':str(index), 'text':f'Course {code} has {value} credits.' if english else f'Môn {code} có {value} tín chỉ.',
                       'citation_ids':[record.chunk_id], 'type':'numeric_fact'})
    total = sum(value for _code, value, _record, _row in parts)
    text = (f"Total credits for {' and '.join(codes)} are {total}." if english
            else f"Tổng số tín chỉ của {' và '.join(codes)} là {total}.")
    claims.append({'claim_id':'total', 'text':text, 'citation_ids':list(citations),
                   'required_citations':len(citations), 'type':'calculation'})
    answer = ' '.join(claim['text'] for claim in claims)
    return _grounding_finalize(answer, tuple(citations.values()), {'claims':claims}, results, language,
                               calibrator=calibrator)
