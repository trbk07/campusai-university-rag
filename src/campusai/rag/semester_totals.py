"""Read explicit semester subtotals, preserving physical source scope and units."""
import json
import re
from collections import defaultdict

from .course_credits import folded
from .multi_hop_evidence import table


_NUMBERS = dict(zip('mot hai ba bon nam sau bay tam chin muoi'.split(), range(1, 11)))
_NUMBERS.update({'tu': 4, 'dau': 1, 'mo dau': 1})
_SEMESTER = re.compile(r'\b(?:hoc ky|ky|hk|semester|term)\s*(?:thu\s+)?('
    + '|'.join(sorted(_NUMBERS, key=len, reverse=True)) + r'|\d{1,2})\b')
_SCOPE = re.compile(r'\b(?:chuong trinh(?: lien ket)?|curriculum|'
    r'(?:the )?(?:(?:selected|uploaded) )?(?:programme|program|table)|'
    r'trong bang(?: (?:minh|em|toi) chon)?|trong tai lieu)\b')


def requested_semesters(question):
    # History is not source evidence. This path requires explicit semesters
    # in the current utterance, and accepts only a complete subtotal request.
    text = folded(question.partition('\nContext topic (untrusted user input): ')[0]).strip(' .?!')
    numbers = []
    def slot(match):
        number = int(match[1]) if match[1].isdigit() else _NUMBERS[match[1]]
        numbers.append(number)
        return ' @ '
    text = _SEMESTER.sub(slot, text)
    text = ' '.join(_SCOPE.sub(' ', text).split())
    text = re.sub(r' (?:vay|nhi|a)$', '', text)
    slots = r'@(?: (?:and|va|voi) @)?'
    quantity = r'(?:tong(?: so)? )?(?:(?:co|hoc|om|can hoc|phai hoc) )?(?:may|bao nhieu|bao nhiu|bn) (?:tin(?: chi)?|tc)'
    patterns = (
        slots + r' (?:thi )?' + quantity,
        r'(?:what (?:is|are) the )?(?:total |sum of )?credits (?:for|in) ' + slots,
        r'how many credits (?:are listed )?(?:for|in) ' + slots,
        slots + r' (?:total )?credits(?: la bao nhieu)?',
        r'khoi luong hoc tap cua ' + slots + r'(?: la gi)?',
    )
    if (not numbers or len(numbers) > 2 or len(numbers) != len(set(numbers))
            or any(not 1 <= n <= 20 for n in numbers)
            or not any(re.fullmatch(pattern, text) for pattern in patterns)):
        return None
    return tuple(numbers)


def semester_subtotals(result):
    """Bind each labelled subtotal to its nearest literal marker in this chunk.

    No scope is inherited from metadata, a previous chunk or a guessed header.
    Course rows and their alternative options are never summed.
    """
    if result.content_type != 'table' or not (value := table(result.content)):
        return []
    rows, headers = value['rows'], value['headers']
    credit_cols = [i for i, h in enumerate(headers) if folded(h) in {'credits', 'so tin chi'}]
    if len(credit_cols) > 1:
        return []
    found, active = [], None
    for index, row in enumerate(rows):
        if not isinstance(row, list) or len(row) != len(headers) or any(not isinstance(c, str) for c in row):
            # Unknown row structure can hide a scope switch.
            active = None
            continue
        cells = [(i, c.strip()) for i, c in enumerate(row) if c.strip()]
        if len(cells) == 1:
            marker = re.fullmatch(r'(?:semester|hoc ky)\s*(\d{1,2})', folded(cells[0][1]))
            if marker:
                active = (int(marker[1]), index)
                continue
        if any(re.match(r'^(?:semester|hoc ky)(?:\s|\d|$)', folded(c)) for _, c in cells):
            active = None
        labels = [(i, c) for i, c in cells if re.fullmatch(
            r'credits\s*per semester|tong(?: so)? tin chi(?: hoc ky)?', folded(c))]
        if active is None or len(labels) != 1:
            continue
        other = [(i, c) for i, c in cells if i != labels[0][0]]
        valid = (len(other) == 1 and other[0][1].isascii() and other[0][1].isdigit()
                 and len(other[0][1]) <= 4
                 and (not credit_cols or other[0][0] == credit_cols[0]))
        found.append((active[0], int(other[0][1]) if valid else None, active[1], index, rows))
    return found


def deterministic_semester_total(question, results, language='vi', *, calibrator=None):
    semesters = requested_semesters(question)
    if semesters is None or not results or len({r.doc_id for r in results}) != 1:
        return None
    candidates = defaultdict(list)
    for result in results:
        for number, value, start, end, rows in semester_subtotals(result):
            if number in semesters:
                candidates[number].append((value, result, start, end, rows))
    parts = []
    for number in semesters:
        values = {p[0] for p in candidates[number]}
        if len(values) != 1 or None in values:
            return None
        parts.append((number, *candidates[number][0]))
    from .grounding import Citation, GroundedAnswer, validate_citation
    from .claims import Claim
    from .confidence import score_confidence
    selected = defaultdict(set)
    records = {}
    for _number, _value, result, start, end, _rows in parts:
        selected[result.chunk_id].update((start, end))
        records[result.chunk_id] = result
    citations = []
    for chunk, indices in selected.items():
        result = records[chunk]
        rows = table(result.content)['rows']
        # These are separately selected original rows, not a contiguous quote.
        # The scope relation was checked above against every intervening row.
        quote = json.dumps([rows[i] for i in sorted(indices)], ensure_ascii=False)
        citation = Citation(chunk, result.doc_id, result.page, quote,
            ' > '.join(result.metadata.get('heading_path', [])), result.metadata.get('source_name', ''),
            tuple(result.metadata.get('page_range', [result.page, result.page])),
            result.metadata.get('table_id', ''), result.metadata.get('source_hash', ''))
        if len(quote) > 1200 or not validate_citation(citation, result, require_quote=True).valid:
            return None
        citations.append(citation)
    english = language.casefold().startswith('en')
    claims = []
    for number, value, result, *_ in parts:
        text = (f'Semester {number} has {value} credits.' if english else
                f'Học kỳ {number} có {value} tín chỉ.')
        # An explicit source subtotal projection, independently checked above.
        claims.append(Claim(str(number), text, 'numeric_fact', 1, (result.chunk_id,),
                            'supported', 1., (result.chunk_id,), False))
    if len(parts) > 1:
        ids = tuple(selected)
        total = sum(p[1] for p in parts)
        names = (' and ' if english else ' và ').join(str(n) for n in semesters)
        text = (f'Total credits for semesters {names} are {total} credits.' if english else
                f'Tổng số tín chỉ của học kỳ {names} là {total} tín chỉ.')
        claims.append(Claim('total', text, 'calculation', len(ids), ids, 'supported', 1., ids, False))
    confidence = score_confidence(retrieval_support=max(0., min(1., max(r.score for r in records.values()))),
        claim_entailment=1., citation_completeness=1., calibrator=calibrator)
    return GroundedAnswer(answer=' '.join(c.text for c in claims), citations=tuple(citations),
        confidence=confidence.label, abstained=False, claims=tuple(claims), evidence_status='found',
        confidence_score=confidence.score, raw_confidence_score=confidence.raw_score,
        policy_version=confidence.policy_version)
