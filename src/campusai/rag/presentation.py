"""Reject exact contradictions between visible output and supported claim records.

This is a bounded marker check, not a semantic entailment model. It preserves
cross-language prose while checking numbers, course IDs, units and directly
opposed wording. List labels and display citation numbers are not factual values.
"""
from collections import defaultdict
import json
from decimal import Decimal
from datetime import date
import re
import unicodedata

from .claims import CODE_RE, normalize_text
from .course_credits import COURSE_CODE, course_code_key

NUMBER = re.compile(r'(?<!\w)\d+(?:[.,]\d+)?')
UNIT = re.compile(r'(?<!\w)(\d+(?:[.,]\d+)?)\s*(%|percent\b|phan tram\b|credits?\b|tin chi\b|vnd\b|usd\b|dollars?\b|dong\b)')
NEGATION = re.compile(r'\b(?:not|khong)\b')
COURSE_MARKER = re.compile(r'(?<!\w)' + COURSE_CODE + r'(?!\w)', re.I)
LOCATION_VALUE = r'[0-9]+(?:\.[0-9]+)*(?:\([a-z]\))?'
LOCATION = re.compile(r'\b(article|dieu|section|muc|chapter|chuong|page|trang)\s+('+LOCATION_VALUE+r')(?![\w(]|\.\d)')
VISIBLE_LOCATION = re.compile(r'\b(article|điều|dieu|section|mục|muc|chapter|chương|chuong|page|trang)\s+('+LOCATION_VALUE+r')(?![\w(]|\.\d)',re.I)
SEMESTER_LOCATION = re.compile(r'\b(?:semester|(?:học\s+)?k[ỳì]|(?:hoc\s+)?k[yi])\s*'
                               r'(?:(?:thứ|thu)\s*)?(\d{1,2})\b',re.I)
CALENDAR_DATE = re.compile(r'(?<!\w)(?:(\d{4})-(\d{1,2})-(\d{1,2})|(\d{1,2})/(\d{1,2})/(\d{4}))(?!\w)')
CLOCK_TIME = re.compile(r'(?<!\w)([0-9]{1,2})(?::|h)([0-9]{2})(?!\w)', re.I)
MONTHS = {name: index for index, name in enumerate(('january','february','march','april','may',
    'june','july','august','september','october','november','december'), 1)}
NAMED_DATE = re.compile(r'\b('+'|'.join(MONTHS)+r')\s+(\d{1,2}),?\s+(\d{4})\b|'
    r'\b(\d{1,2})\s+('+'|'.join(MONTHS)+r')\s+(\d{4})\b', re.I)
VIETNAMESE_DATE = re.compile(r'\b(?:ngày|ngay)\s+(\d{1,2})\s+'
    r'(?:tháng|thang)\s+(\d{1,2})\s+(?:năm|nam)\s+(\d{4})\b', re.I)


def calendar_presentation(text):
    """Canonicalize valid, explicit whole dates/times, retaining their identity."""
    markers = set()
    def dated(year, month, day, original):
        try: value = date(int(year), int(month), int(day)).isoformat()
        except ValueError:
            markers.add(('invalid_date', original.casefold()))
            return original
        markers.add(('date', value))
        return value
    def numeric(match):
        y,m,d,day,month,year=match.groups()
        return dated(y or year, m or month, d or day, match[0])
    def named(match):
        month,day,year,d,m,y=match.groups()
        return dated(year or y, MONTHS[(month or m).casefold()], day or d, match[0])
    def vietnamese(match):
        day,month,year=match.groups()
        return dated(year,month,day,match[0])
    def clock(match):
        hour,minute=map(int,match.groups())
        if hour > 23 or minute > 59:
            markers.add(('invalid_time', match[0].casefold()))
            return match[0]
        value=f'{hour:02d}:{minute:02d}'
        markers.add(('time',value))
        return value
    text=unicodedata.normalize('NFC',text)
    text=VIETNAMESE_DATE.sub(vietnamese,text)
    text=CALENDAR_DATE.sub(numeric,text)
    text=NAMED_DATE.sub(named,text)
    return CLOCK_TIME.sub(clock,text),markers


def location_key(kind, value):
    return ({'dieu':'article','muc':'section','chuong':'chapter','trang':'page'}.get(kind,kind),value)


def location_proofs(citations, registry):
    """Actual cited page and explicit source headings, not arbitrary numbers."""
    from ..retrieval.tokenizer_vi import source_body
    proven=set()
    for citation in citations:
        proven.add(('page',str(citation.page)))
        record=registry.get(citation.chunk_id)
        if record is None:continue
        body=source_body({'content':record.content},decode_tables=False)
        for line in body.splitlines():
            match=LOCATION.match(folded(line))
            if match:proven.add(location_key(*match.groups()))
        if record.content_type=='table':
            try:
                quoted=json.loads(citation.quote)
                source=json.loads(body[body.index('{"headers"'):])
            except (ValueError,TypeError):
                continue
            selected=(quoted.get('rows',[]) if isinstance(quoted,dict) else
                      [quoted] if isinstance(quoted,list) and all(isinstance(c,str) for c in quoted) else quoted)
            if not isinstance(selected,list):continue
            # These quotes have already passed the citation/row validator.
            # Only selected literal markers or an explicit semester-column
            # cell prove a location; unrelated source rows cannot supply it.
            columns=[i for i,h in enumerate(source.get('headers',[])) if isinstance(h,str)
                     and ' '.join(folded(h).split()) in {'semester','term','hoc ky'}]
            for row in selected:
                if not isinstance(row,list) or any(not isinstance(c,str) for c in row):continue
                cells=[c.strip() for c in row if c.strip()]
                marker=SEMESTER_LOCATION.fullmatch(cells[0]) if len(cells)==1 else None
                if marker:proven.add(('semester',str(int(marker[1]))))
                if len(columns)==1 and len(row)>columns[0] and re.fullmatch(r'[0-9]{1,2}',row[columns[0]]):
                    proven.add(('semester',str(int(row[columns[0]]))))
            if isinstance(quoted,dict) and isinstance(quoted.get('scope'),str):
                marker=SEMESTER_LOCATION.fullmatch(quoted['scope'])
                if marker and any(line.strip()=='Table scope: '+quoted['scope'] for line in record.content.splitlines()):
                    proven.add(('semester',str(int(marker[1]))))
    return proven


def folded(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.casefold())
                   if not unicodedata.combining(c)).replace('đ', 'd')


def number(value):
    return Decimal(value.replace(',', '.'))


def prose(text):
    text = re.sub(r'^\s*\d+[.)]\s+', '', text, flags=re.M)
    return re.sub(r'\[\d+\]', '', text)


def quantities(text):
    result = defaultdict(set)
    for value, unit in UNIT.findall(folded(text)):
        unit = ('credits' if unit in {'credit', 'credits', 'tin chi'} else
                'percent' if unit in {'%', 'percent', 'phan tram'} else
                'vnd' if unit in {'dong', 'vnd'} else 'usd')
        result[number(value)].add(unit)
    return result


_SCOPE_CUES = re.compile(
    r"\b(?:admission|cohort|intake|academic year|school year|curriculum|programme|program|"
    r"issued|published|effective|version|regulations?|policy|quy che|quy dinh|ban hanh|nam hoc|khoa tuyen sinh|khoa|ap dung|"
    r"dieu chinh|cap nhat)\b",
    re.I,
)
_SCOPE_CUES_AFTER = re.compile(
    r"^\s*(?:curriculum|programme|program|academic year|school year|"
    r"regulations?|policy|(?:(?:undergraduate|graduate|postgraduate)\s+)?admissions?\s+(?:notice|plan|quota|intake|regulations?))\b",
    re.I,
)
_VERIFICATION_QUESTION = re.compile(
    r"\b(?:is that correct|is this correct|is that right|is this right|am i right|"
    r"co dung khong|dung khong|co chinh xac khong)\b",
    re.I,
)
_AFFIRMATIVE = re.compile(r"^\s*(?:yes|correct|that is correct|that's correct|đúng|chính xác)\b", re.I)
_NEGATIVE_CORRECTION = re.compile(r"\b(?:no|not correct|incorrect|không đúng|sai)\b", re.I)
_QUESTION_SCOPE_NUMBER = re.compile(
    r"\b(admission\s+cohort|cohort|semester|term|article|dieu|section|muc|chapter|chuong|page|trang)\s+("+LOCATION_VALUE+r")(?![\w(]|\.\d)",
    re.I,
)


def _scoped_years(text):
    """Return only years explicitly used as document/cohort scope labels."""
    normalized = folded(normalize_text(str(text or "")))
    years = set()
    for match in re.finditer(r"(?<![\w/.-])(?:19|20)\d{2}(?![\w/-])", normalized):
        if re.match(r"\.\d{1,2}[.-]\d{1,2}(?!\d)", normalized[match.end():]):
            continue
        prefix = normalized[max(0, match.start() - 64):match.start()]
        suffix = normalized[match.end():match.end() + 32]
        if _SCOPE_CUES.search(prefix) or _SCOPE_CUES_AFTER.search(suffix):
            years.add(int(match[0]))
    return years


def _scope_number_key(label, value):
    label = folded(normalize_text(label)).replace(" ", " ")
    if label == "admission cohort":
        label = "cohort"
    if label == "term":
        label = "semester"
    if label in {'article', 'dieu', 'section', 'muc', 'chapter', 'chuong', 'page', 'trang'}:
        label = location_key(label, value)[0]
    return label, re.sub(r'\d+', lambda match: str(int(match[0])), value.casefold())


def _question_scope_numbers(text):
    normalized = folded(normalize_text(str(text or "")))
    return {_scope_number_key(match[1], match[2]) for match in _QUESTION_SCOPE_NUMBER.finditer(normalized)}


def _affirmative_disagrees_with_review_value(question, answer, support):
    """Reject a confident yes when a reviewed credit value disproves the premise."""
    normalized_question = normalize_text(str(question or ""))
    normalized_answer = normalize_text(str(answer or ""))
    if (not _VERIFICATION_QUESTION.search(normalized_question)
            or not _AFFIRMATIVE.search(normalized_answer)
            or _NEGATIVE_CORRECTION.search(normalized_answer)):
        return False
    premise = quantities(normalized_question)
    reviewed = quantities(support)
    for value, units in premise.items():
        for unit in units:
            reviewed_values = {candidate for candidate, candidate_units in reviewed.items()
                               if unit in candidate_units}
            if reviewed_values and value not in reviewed_values:
                return True
    return False


def canonical_code_spacing(text, compact_anchors):
    """Normalize source-style codes without merging ordinary words and numbers."""
    def replace(match):
        value = match[0]
        key = course_code_key(value)
        prefix = re.split(r'\d', value, maxsplit=1)[0].strip()
        explicit = re.search(r'\b(?:course|code|mon|hoc phan)\s*$', folded(text[:match.start()]))
        if not re.search(r'\s', value) or prefix.isupper() or key.casefold() in compact_anchors or explicit:
            return key
        return value
    return COURSE_MARKER.sub(replace, text)


def code_markers(text):
    # Retain complete dotted namespaces as well as the existing broad compact IDs.
    return {code.casefold() for code in CODE_RE.findall(text)} | {
        course_code_key(m[0]).casefold() for m in COURSE_MARKER.finditer(text) if not re.search(r'\s', m[0])}


def presentation_conflicts(answer, claims, *, locations=(), question=None, source_scope_codes=()):
    """Only supported claims supply allowable visible markers, not random source numbers."""
    supported = [claim.text for claim in claims if claim.status == 'supported']
    if not supported:
        return True
    visible = prose(answer)
    shared_scope_numbers = _question_scope_numbers(question) & _question_scope_numbers(visible)
    # Remove only a proved location label. Its number must never become an
    # allowable factual quantity elsewhere in the sentence (e.g.9 credits).
    def mask_location(match):
        key = location_key(folded(match[1]),match[2])
        return ' ' if key in locations or key in shared_scope_numbers else match[0]
    if locations:
        visible=VISIBLE_LOCATION.sub(mask_location,visible)
        visible=SEMESTER_LOCATION.sub(lambda m:' ' if ('semester',str(int(m[1]))) in locations else m[0],visible)
    visible = _QUESTION_SCOPE_NUMBER.sub(
        lambda match: ' ' if _scope_number_key(match[1], match[2]) in shared_scope_numbers else match[0],
        visible,
    )
    visible, visible_calendar = calendar_presentation(visible)
    canonical_supported = [calendar_presentation(text) for text in supported]
    if visible_calendar - set().union(*(markers for _, markers in canonical_supported)):
        return True
    supported = [text for text, _ in canonical_supported]
    if locations:
        supported = [SEMESTER_LOCATION.sub(lambda m:' ' if ('semester',str(int(m[1]))) in locations else m[0],text)
                     for text in supported]
    support = '\n'.join(supported)
    # A scoped cohort/document year may be repeated in the prose answer while
    # the verification claim correctly omits it. Allow only the same year,
    # only when both question and answer label it as scope, and never a date.
    allowed_scope_years = _scoped_years(question) & _scoped_years(visible)
    if _affirmative_disagrees_with_review_value(question, visible, support):
        return True
    anchors = code_markers(visible) | code_markers(support)
    visible = canonical_code_spacing(visible, anchors)
    supported = [canonical_code_spacing(text, anchors) for text in supported]
    support = '\n'.join(supported)
    # An identifier repeated as question scope is permitted only when the
    # physically validated cited passage also names it. It cannot authorize a
    # different ID or an arbitrary number elsewhere in the answer.
    scope_codes = code_markers(str(question or '')) & set(source_scope_codes)
    if code_markers(visible) - code_markers(support) - scope_codes:
        return True
    visible_numbers = {number(v) for v in NUMBER.findall(visible)}
    supported_numbers = {number(v) for v in NUMBER.findall(support)}
    ungrounded_numbers = visible_numbers - supported_numbers - {number(str(year)) for year in allowed_scope_years}
    if ungrounded_numbers:
        return True
    known_units = quantities(support)
    for value, units in quantities(visible).items():
        if known_units.get(value) and not units <= known_units[value]:
            return True
    # Opposite negation of the same explicit clause is a contradiction. Do not
    # guess polarity across unrelated clauses or infer it from vocabulary alone.
    for clause in re.split(r'[.!?。！？]\s*|\n+', visible):
        normalized = normalize_text(folded(clause)).strip(' .!?')
        if not normalized:
            continue
        base = ' '.join(NEGATION.sub('', normalized).split())
        for claim in supported:
            original = normalize_text(folded(claim)).strip(' .!?')
            if base == ' '.join(NEGATION.sub('', original).split()) and bool(NEGATION.search(normalized)) != bool(NEGATION.search(original)):
                return True
    return False
