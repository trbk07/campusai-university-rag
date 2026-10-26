"""Bounded natural single-course lookups from literal, headed source rows."""
import json
import re

from .course_credits import COURSE_CODE, course_code_key, folded, headed_credit_rows
from .multi_hop_evidence import find_premise, name_matches, prerequisite_codes, table


_CONTEXT = '\nContext topic (untrusted user input): '
_CREDIT = r'(?:may|bao nhieu|bn)\s+(?:tin(?: chi)?|tc)'
_TAIL = r'(?:\s+(?:vay|nhi|ban|a|the|ah|oi))*'


def _request(question):
    raw, _, topic = question.partition(_CONTEXT)
    text = folded(raw).strip(' .?!')
    if topic and re.search(r'\b(?:neu|if|unless|mien|waiver|transfer|chuyen nganh|so sanh|compare|comparison|versus)\b', folded(topic)):
        return None
    for pattern, fields in (
        (r'can hoc gi truoc va ' + _CREDIT + _TAIL, ('credits', 'prerequisites')),
        (r'(?:can )?hoc (?:gi truoc|truoc (?:nhung )?mon nao)' + _TAIL, ('prerequisites',)),
        (r'(?:(?:mon nay|hoc phan nay)\s+)?(?:co\s+)?' + _CREDIT + _TAIL, ('credits',)),
        (r'how many credits', ('credits',)),
    ):
        if topic and re.fullmatch(pattern, text):
            return fields, None, folded(topic)
    for pattern, fields in (
        (r'(?:(?:mon|hoc phan)\s+)?(.+?)\s+(?:co\s+)?' + _CREDIT + _TAIL, ('credits',)),
        (r'how many credits does (?:course )?(.+?) (?:have|carry)', ('credits',)),
        (r'what are (?:the )?prerequisites for (?:course )?(.+)', ('prerequisites',)),
        (r'what are (?:the )?prerequisites and credits for (?:course )?(.+)', ('credits', 'prerequisites')),
    ):
        match = re.fullmatch(pattern, text)
        if match:
            return fields, match[1].strip(' "\''), ''
    return None


def _target(results, name, topic):
    if name and re.fullmatch(COURSE_CODE, name, re.I):
        return course_code_key(name)
    matches = []
    for result in results:
        value = table(result.content)
        if not value:
            continue
        columns = [i for i, h in enumerate(value['headers']) if re.fullmatch(
            r'(?:hoc phan|ten hoc phan|course name|discipline)(?:\s*\(.*\))?', folded(h))]
        if len(columns) != 1:
            continue
        for code, _credits, row in headed_credit_rows(result.content) or []:
            if len(row) <= columns[0] or not isinstance(row[columns[0]], str):
                continue
            cell = row[columns[0]]
            if name:
                if name_matches(name, cell):
                    matches.append((code, 0, len(name)))
                continue
            lines = cell.splitlines()
            aliases = {' '.join(lines[:i]).rstrip().rstrip('*').rstrip()
                       for i in range(1, len(lines) + 1)}
            aliases.update(' '.join(lines[i:]) for i in range(len(lines)))
            for alias in aliases:
                if not alias or not name_matches(alias, cell):
                    continue
                for match in re.finditer(r'\b(?:mon|hoc phan|course|subject)\s+'
                                         + re.escape(folded(alias)) + r'(?=$|[\s.,;:!?])', topic):
                    matches.append((code, match.start(), match.end()))
    # A shorter name within the same explicitly named subject is not a second
    # course. Separate subject mentions and duplicate names remain ambiguous.
    maximal = [(code, start, end) for code, start, end in matches if not any(
        a <= start and end <= b and (a < start or end < b) for _, a, b in matches)]
    if not name and any(re.match(r'\s+(?:va|and|hay|or|voi|with)\b', topic[end:])
                        for _, _, end in maximal):
        return None
    codes = {code for code, _, _ in maximal}
    return next(iter(codes)) if len(codes) == 1 else None


def deterministic_course_lookup(question, results, language='vi', *, calibrator=None):
    request = _request(question)
    docs = {r.doc_id for r in results}
    if request is None or len(docs) != 1:
        return None
    fields, name, topic = request
    code = _target(results, name, topic)
    if not code:
        return None
    premise = find_premise(results, next(iter(docs)), code=code,
                           require_credits='credits' in fields)
    if premise is None:
        return None
    bridges = prerequisite_codes(premise) if 'prerequisites' in fields else ()
    if 'prerequisites' in fields and not bridges:
        return None
    english = language.casefold().startswith('en')
    facts = []
    if 'credits' in fields:
        facts.append(f'Course {code} has {premise.credits} credits.' if english else
                     f'Môn {code} có {premise.credits} tín chỉ.')
    facts.extend(f'Course {bridge} is a prerequisite of course {code}.' if english else
                 f'Môn {bridge} là môn tiên quyết của môn {code}.' for bridge in bridges)
    from .grounding import Citation, _grounding_finalize, validate_citation
    result = premise.result
    citation = Citation(result.chunk_id, result.doc_id, result.page,
        json.dumps(list(premise.row), ensure_ascii=False),
        ' > '.join(result.metadata.get('heading_path', [])), result.metadata.get('source_name', ''),
        tuple(result.metadata.get('page_range', [result.page, result.page])),
        result.metadata.get('table_id', ''), result.metadata.get('source_hash', ''))
    if len(citation.quote) > 1200 or not validate_citation(citation, result, require_quote=True).valid:
        return None
    claims = [{'claim_id': str(i), 'text': fact, 'citation_ids': [result.chunk_id]}
              for i, fact in enumerate(facts, 1)]
    answer = _grounding_finalize(' '.join(facts), (citation,), {'claims': claims},
                                [result], language, question=question, calibrator=calibrator)
    return answer if not answer.abstained else None
