"""Literal row/year/column checks for scalar year-headed tables.

This is a veto, not a substitute for ordinary claim and citation validation.
No locale conversion, inferred units, arithmetic or rewritten source cells.
"""
from dataclasses import dataclass
from decimal import Decimal
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
_UNITS = [
    ('trillion', r'\btrillions?\b|\bnghin\s+ty\b'),
    ('billion', r'\bbillions?\b|\bbn\b|\bty\b'),
    ('million', r'\bmillions?\b|\btrieu\b'),
    ('thousand', r'\bthousands?\b|\bnghin\b|\bngan\b'),
    ('usd', r'\bus\s+dollars?\b|\busd\b|\bdollars?\b|\bdo\s+la(?:\s+my)?\b|\$'),
    ('vnd', r'\bvnd\b|\bdong\b'), ('eur', r'\beur\b|\beuros?\b'),
    ('percent', r'%|\bpercent(?:age)?\b|\bphan\s+tram\b')]


def _units(text):
    found = set()
    for name, pattern in _UNITS:
        if re.search(pattern, text):
            found.add(name)
            text = re.sub(pattern, ' ', text)
    return found, text


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


def binding(text: str, content: str, question: str = '', *, numeric_cells: bool = False) -> CellBinding | None:
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
        return _scalar_binding(text, headers, rows, question) if numeric_cells else None
    if any(not isinstance(row, list) or len(row) != len(headers)
           or not all(isinstance(c, str) for c in row) or not row[0].strip() for row in rows):
        return CellBinding(False)
    if any(_scalar(cell) is None for row in rows for cell in row[1:]):
        return CellBinding(False) if numeric_cells else None
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


def _scalar_binding(text, headers, rows, question):
    """Extra guard for locally verified optical scalar grids; never credits."""
    if any(folded(re.split(r'[（(]', header, maxsplit=1)[0]) in
           {'credit', 'credits', 'credit points', 'tin chi', 'so tin chi'} for header in headers):
        return None  # Existing typed course-credit/sum/difference proofs remain authoritative.
    invalid = CellBinding(False)
    if any(not isinstance(row, list) or len(row) != len(headers)
           or not all(isinstance(c, str) and c.strip() for c in row) for row in rows):
        return invalid
    identities = [i for i in range(len(headers)) if all(_scalar(row[i]) is None for row in rows)]
    if len(identities) != 1:
        return invalid
    identity = identities[0]
    if any(_scalar(cell) is None for row in rows for i, cell in enumerate(row) if i != identity):
        return invalid
    value, query = folded(text), folded(question)
    own = _rows(value, [row[identity] for row in rows])
    requested = _rows(query, [row[identity] for row in rows])
    # Non-scalar descriptions/headers retain the ordinary validation path.
    if not any(char.isdigit() for char in _mask(value, [span for _, span in own])):
        return None
    amount = _amount(value)
    if amount is None:
        tail = re.search(r'(' + _NUMBER + r')\s*[.]?\s*$', value)
        amount = tail.span(1) if tail else None
    selected = {i for i, _ in own} or {i for i, _ in requested}
    if len(selected) != 1 or amount is None:
        return invalid
    row = next(iter(selected))
    if requested and row not in {i for i, _ in requested}:
        return invalid
    remainder = _mask(value, [span for _, span in own] + [amount])
    fields = {i: set(_WORD.findall(folded(re.split(r'[（(]', header, maxsplit=1)[0])))
              for i, header in enumerate(headers) if i != identity}
    def named(phrase):
        words = set(_WORD.findall(phrase))
        return {i for i, field in fields.items() if field and field <= words}
    asserted = named(remainder)
    requested_fields = named(_mask(query, [span for _, span in requested]))
    target = asserted or requested_fields
    if len(target) != 1 or asserted and requested_fields and not asserted <= requested_fields:
        return invalid
    column = next(iter(target))
    expected, actual = _scalar(rows[row][column]), _scalar(value[amount[0]:amount[1]])
    if actual != expected and not (actual and actual.endswith('%') and '%' in headers[column]
                                   and actual[:-1] == expected):
        return invalid
    units, remainder = _units(remainder)
    expected_units, header = _units(folded(headers[column]))
    if units and units != expected_units:
        return invalid
    full_header = set(_WORD.findall(header))
    qualifiers = full_header - fields[column] - _CONNECTORS
    extra = set(_WORD.findall(remainder)) - fields[column] - _CONNECTORS
    if extra and (not extra <= qualifiers or not qualifiers <= extra):
        return invalid
    remaining_symbols = re.sub(r'[\w\s.,:;|=()\-]', '', remainder)
    if remaining_symbols:
        return invalid
    return CellBinding(True, row, column)


def _quantity(value, *, public=False):
    scalar = _scalar(value)
    if scalar is None and public and re.fullmatch(r'[+\-−]?\d+,\d{1,2}%?', value):
        scalar = _scalar(value.replace(',', '.'))
    return Decimal(scalar.rstrip('%').replace(',', '')) if scalar is not None else None


def numeric_answer_units_valid(answer, claims, registry, question='', *, locations=()):
    """Visible units/scales must match the actual optical cells, not raw labels."""
    expected = {}
    additional = set()
    for claim in claims:
        typed = False
        for identity in claim.citation_ids:
            record = registry.get(identity)
            if record is None or record.numeric_cell_policy != 'ruled-ocr-numeric-v1':
                continue
            proof = binding(claim.text, record.content, question, numeric_cells=True)
            if proof is None or not proof.supported:
                continue
            typed = True
            table = json.loads(record.content[record.content.index('{"headers"'):])
            value = _scalar(table['rows'][proof.row][proof.column])
            units, _ = _units(folded(table['headers'][proof.column]))
            expected.setdefault(_quantity(value), []).append(units)
        if not typed:
            additional.update(_quantity(m[0], public=True) for m in re.finditer(_NUMBER, folded(claim.text)))
    if not expected:
        return True
    from .presentation import prose, LOCATION, location_key
    text = folded(prose(answer))
    location_spans = [match.span(2) for match in LOCATION.finditer(text)
                      if location_key(*match.groups()) in locations]
    for amount in re.finditer(_NUMBER, text):
        value = _quantity(amount[0], public=True)
        if any(a <= amount.start() and amount.end() <= b for a, b in location_spans):
            continue
        if value is None or value not in expected and value not in additional:
            return False
        if value not in expected:
            continue
        explicit = {'percent'} if amount[0].endswith('%') else set()
        if text[max(0, amount.start()-1):amount.start()] == '$':
            explicit.add('usd')
        tail = text[amount.end():amount.end()+80]
        for _ in range(4):
            found = False
            for name, pattern in _UNITS:
                match = re.match(r'\s*(?:of\s+)?(?:'+pattern+r')', tail)
                if match:
                    explicit.add(name); tail = tail[match.end():]; found = True
                    break
            if not found:
                break
        if explicit and explicit not in expected[value]:
            return False
    return True
