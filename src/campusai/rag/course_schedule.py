"""Complete bounded course-semester lists from explicit source columns."""
import json
import re

from .course_credits import COURSE_CODE, course_code_key, folded
from .multi_hop_evidence import table


def _subjects(question):
    text = folded(question).strip(' .?!')
    text = re.sub(r'\bai\b', 'tri tue nhan tao', text)
    text = re.sub(r'\bnlp\b', 'xu ly ngon ngu tu nhien', text)
    match = re.fullmatch(r'(.+?) (?:hoc (?:o )?)?(?:hoc ky|ky|hk) (?:nao|may)(?: vay| nhi)?', text)
    if not match:
        return None
    names = re.sub(r' trong (?:huong dan|lo trinh|chuong trinh)(?: (?:thac si|cao hoc))?(?: [a-z]{2,5})?$', '', match[1])
    names = re.sub(r'^(?:cac |hai )?(?:mon|hoc phan) ', '', names)
    parts = re.split(r'\s+(?:voi|va|and)\s+|\s*[/&]\s*', names)
    if not 2 <= len(parts) <= 4 or any(not part.strip() for part in parts):
        return None
    return parts


def _column(headers, pattern):
    columns = [i for i, value in enumerate(headers) if re.fullmatch(pattern, folded(value))]
    return columns[0] if len(columns) == 1 else None


def _matches(subject, code, label):
    if re.fullmatch(COURSE_CODE, subject, re.I):
        return course_code_key(subject) == code
    # Preserve complete translated titles, including wrapped English lines.
    # A literal substring inside a different course title is not an identity.
    lines = label.splitlines()
    aliases = {' '.join(lines[:i]) for i in range(1, len(lines) + 1)}
    aliases.update(' '.join(lines[i:]) for i in range(len(lines)))
    return any(re.fullmatch(re.escape(subject) + r'(?: va ung dung| and applications)?', folded(alias))
               for alias in aliases)


def lookup_course_schedule(question, documents, *, doc_ids, language='vi', calibrator=None):
    if (doc_ids is None or len(doc_ids) != 1 or len(documents) != 1
            or documents[0]['doc_id'] != doc_ids[0]):
        return None
    subjects = _subjects(question)
    if subjects is None:
        return None
    inventory = []
    for item in documents[0]['items']:
        if item.get('content_type') != 'table':
            continue
        data = table(item['content'])
        if not data:
            return None
        code = _column(data['headers'], r'(?:course code|ma (?:so )?hoc phan)')
        name = _column(data['headers'], r'(?:discipline|course name|subject name|(?:ten )?hoc phan)(?:\s*\(.*\))?')
        semester = _column(data['headers'], r'(?:hoc ky|semester|term)')
        if None in (code, name, semester):
            return None
        for row in data['rows']:
            if (not isinstance(row, list) or len(row) != len(data['headers'])
                    or any(not isinstance(cell, str) for cell in row)):
                return None
            if re.search(COURSE_CODE, row[code], re.I):
                inventory.append((item, row, row[code], row[name], row[semester]))
    selected = []
    for subject in subjects:
        records = [record for record in inventory if _matches(subject, course_code_key(record[2]), record[3])]
        if not records or len({course_code_key(r[2]) for r in records}) != 1:
            return None
        identity = course_code_key(records[0][2])
        # Inspect every occurrence, including rows whose conflicting name no
        # longer matches the requested phrase and lower-ranked table chunks.
        records = [r for r in inventory if course_code_key(r[2]) == identity]
        if any(not re.fullmatch(COURSE_CODE, r[2].strip(), re.I)
               or not r[3].strip() or not re.fullmatch(r'[1-9][0-9]?', r[4].strip()) for r in records):
            return None
        if any(re.search(r'\b(?:if|unless|neu|ngoai tru|tuy chon|co the|hoac|or)\b', folded(' '.join(r[1])))
               for r in records):
            return None
        if len({(folded(r[3]), int(r[4])) for r in records}) != 1:
            return None
        selected.append(records[0])
    if len({course_code_key(r[2]) for r in selected}) != len(subjects):
        return None
    from .grounding import Citation, GroundedAnswer, validate_citation
    from .claims import Claim
    from .confidence import score_confidence
    from ..retrieval.hybrid import RetrievalResult
    results, citations, claims, facts = {}, [], [], []
    for number, (item, row, code, label, semester) in enumerate(selected, 1):
        code = course_code_key(code); label = ' '.join(label.split())
        fact = (f'Course {code} ({label}) is in semester {int(semester)}.' if language.casefold().startswith('en')
                else f'Học phần {code} ({label}) học ở học kỳ {int(semester)}.')
        facts.append(fact)
        claims.append(Claim(str(number), fact, 'fact', 1, (item['chunk_id'],), 'supported', 1., (item['chunk_id'],), False))
        results[item['chunk_id']] = RetrievalResult(item['chunk_id'], doc_ids[0], item['page'], item['content'],
            'table', 1., 'source_course_schedule', item.get('metadata', {}))
    for key, result in results.items():
        rows = [r[1] for r in selected if r[0]['chunk_id'] == key]
        quote = json.dumps(rows[0] if len(rows) == 1 else rows, ensure_ascii=False)
        meta = result.metadata
        citation = Citation(key, result.doc_id, result.page, quote, ' > '.join(meta.get('heading_path', [])),
            meta.get('source_name', ''), tuple(meta.get('page_range', [result.page, result.page])),
            meta.get('table_id', ''), meta.get('source_hash', ''))
        if len(quote) > 1200 or not validate_citation(citation, result, require_quote=True).valid:
            return None
        citations.append(citation)
    confidence = score_confidence(retrieval_support=1., claim_entailment=1., citation_completeness=1., calibrator=calibrator)
    return GroundedAnswer(' '.join(facts), tuple(citations), confidence.label, False, claims=tuple(claims),
        evidence_status='found', confidence_score=confidence.score, raw_confidence_score=confidence.raw_score,
        policy_version=confidence.policy_version), list(results.values())
