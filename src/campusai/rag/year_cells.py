"""Literal row/year/column checks for scalar year-headed tables.

This is a veto, not a substitute for ordinary claim and citation validation.
No locale conversion, inferred units, arithmetic or rewritten source cells.
"""
from dataclasses import dataclass
import json
import re

from .course_credits import folded

_YEAR = re.compile(r'(?<!\w)(?:19|20)\d{2}(?!\w)')
_NUMBER = r'\(?[+\-−]?(?:\d[\d.,]*\d|\d)\)?(?:\s*%)?'
_SCALAR = re.compile(r'[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?%?')
_WORD = re.compile(r'[^\W_]+')
_CONNECTORS = set(('in for the of is was are were has have equals equal to value amount '
                   'at by year during a an it this recorded reported nam trong vao cua '
                   'la co gia tri bang so lieu duoc ghi nhan').split())


@dataclass(frozen=True)
class CellBinding:
    supported: bool
    row: int | None = None
    column: int | None = None


def _mask(text, spans):
    chars = list(text)
    for start, end in spans:
        chars[start:end] = ' ' * (end - start)
    return ''.join(chars)


def _scalar(value):
    value = re.sub(r'\s+%', '%', value.strip().replace('−', '-'))
    if value.startswith('(') and value.endswith(')'):
        value = '-' + value[1:-1]
    return value.lstrip('+') if _SCALAR.fullmatch(value) else None


def _rows(text, labels):
    matches = []
    for index, label in enumerate(labels):
        label = re.sub(r'[.·…]{2,}\s*$', '', folded(label)).strip()
        words = _WORD.findall(label)
        if not words:
            continue
        pattern = r'(?<!\w)' + r'[\W_]+'.join(map(re.escape, words)) + r'(?!\w)'
        matches.extend((index, m.span()) for m in re.finditer(pattern, text))
    # ABC must not also select the ABC reserve or CDQ ABC reserve row.
    return [(i, span) for i, span in matches if not any(
        other[0] <= span[0] and span[1] <= other[1] and other != span
        for _, other in matches)]


def _amount(text):
    spans = set()
    patterns = [r'\b(?:is|was|are|were|has|have|equals|la|co|bang)\s+(' + _NUMBER + r')',
                r'\b(?:value|amount)\s+of\s+(' + _NUMBER + r')',
                r'[:=]\s*(' + _NUMBER + r')',
                r'^\s*(' + _NUMBER + r')\s*[.]?\s*$',
                r'\|\s*(' + _NUMBER + r')\s*[.]?\s*$']
    for pattern in patterns:
        spans.update(m.span(1) for m in re.finditer(pattern, text))
    return next(iter(spans)) if len(spans) == 1 else None


def binding(text: str, content: str, question: str = '') -> CellBinding | None:
    """None means outside this format; False means an unproved scalar claim."""
    if len(content) > 256_000:
        return None
    start = content.find('{"headers"')
    try:
        table = json.loads(content[start:]) if start >= 0 else None
    except ValueError:
        return None
    if not isinstance(table, dict):
        return None
    headers, rows = table.get('headers'), table.get('rows')
    if (not isinstance(headers, list) or not 3 <= len(headers) <= 32
            or not all(isinstance(h, str) for h in headers)
            or not isinstance(rows, list) or not 1 <= len(rows) <= 512):
        return None
    years = [list(_YEAR.finditer(folded(h))) for h in headers]
    columns = [i for i in range(1, len(headers)) if len(years[i]) == 1]
    if len({years[i][0][0] for i in columns}) < 2:
        return None
    if any(not isinstance(row, list) or len(row) != len(headers)
           or not all(isinstance(c, str) for c in row) or not row[0].strip() for row in rows):
        return CellBinding(False)
    if any(_scalar(cell) is None for row in rows for cell in row[1:]):
        return None
    value, query = folded(text), folded(question)
    own = _rows(value, [row[0] for row in rows])
    requested = _rows(query, [row[0] for row in rows])
    amount = _amount(value)
    outside_value = _mask(value, [span for _, span in own] + ([amount] if amount else []))
    asserted_years = list(_YEAR.finditer(outside_value))
    requested_years = set(_YEAR.findall(_mask(query, [span for _, span in requested])))
    if not (own or requested) or not (asserted_years or requested_years):
        return None
    invalid = CellBinding(False)
    row_ids = {i for i, _ in own} or {i for i, _ in requested}
    if len(row_ids) != 1 or amount is None or len(asserted_years) > 1:
        return invalid
    row = next(iter(row_ids))
    if requested and row not in {i for i, _ in requested}:
        return invalid
    if not asserted_years and len(requested_years) != 1:
        return invalid
    year = asserted_years[0][0] if asserted_years else next(iter(requested_years))
    if requested_years and year not in requested_years:
        return invalid
    fields = {i: set(_WORD.findall(_YEAR.sub(' ', folded(headers[i])))) for i in columns}

    def named_fields(phrase):
        words = set(_WORD.findall(phrase))
        found = {frozenset(field) for field in fields.values() if field and field <= words}
        return {field for field in found if not any(field < other for other in found)}

    own_fields = named_fields(outside_value)
    query_fields = named_fields(_mask(query, [span for _, span in requested]))
    target = own_fields or query_fields
    if len(target) > 1 or (own_fields and query_fields and not own_fields <= query_fields):
        return invalid
    choices = [i for i in columns if years[i][0][0] == year
               and (not target or frozenset(fields[i]) in target)]
    if len(choices) != 1:
        return invalid
    column = choices[0]
    if _scalar(value[amount[0]:amount[1]]) != _scalar(rows[row][column]):
        return invalid
    remaining = _mask(value, [span for _, span in own] + [amount]
                      + [m.span() for m in asserted_years])
    remaining = _WORD.sub(lambda m: ' ' * len(m[0]) if m[0] in fields[column] else m[0], remaining)
    if set(_WORD.findall(remaining)) - _CONNECTORS:
        return invalid
    if re.sub(r'[\w\s.,:;|=()\-]', '', remaining):
        return invalid
    return CellBinding(True, row, column)
