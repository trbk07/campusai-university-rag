"""Link matching course table rows to their original text fragments."""
from __future__ import annotations

from collections import Counter
import json
import math
import re
import unicodedata

from .tokenizer_vi import normalized_tokens, tokenize, requested_semesters


def _phrase(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold().replace("đ", "d"))
    return " " + " ".join(tokenize(value.encode("ascii", "ignore").decode("ascii"))) + " "


def named_table_sources(query: str, records: dict[str, dict]) -> list[str]:
    """Find explicit subject columns containing a complete requested name."""
    query_phrase = _phrase(query)
    matches = []
    for chunk, item in records.items():
        start = item.get("content", "").find('{"headers"')
        if start < 0:
            continue
        try:
            table = json.loads(item["content"][start:])
        except (ValueError, TypeError):
            continue
        for cells in table.get("rows", []):
            if not isinstance(cells, list) or any(not isinstance(cell, str) for cell in cells):
                continue
            named = _named_curriculum_row(cells, table.get("headers", []))
            if named is not None and _phrase(" ".join(named[1])) in query_phrase:
                matches.append(chunk)
                break
    return matches


def primary_course_tables(code: str, records: dict[str, dict]) -> set[str]:
    """Identify the actual course-code column, never prerequisite mentions."""
    matches = set()
    for chunk, item in records.items():
        content = str(item.get('content', ''))
        start = content.find('{"headers"')
        if start < 0:
            continue
        try:
            table = json.loads(content[start:])
        except (ValueError, TypeError):
            continue
        if not isinstance(table, dict):
            continue
        headers, rows = table.get('headers'), table.get('rows')
        if (not isinstance(headers, list) or any(not isinstance(h, str) for h in headers)
                or not isinstance(rows, list)):
            continue
        roles = [_phrase(h).strip() for h in headers]
        columns = [i for i, role in enumerate(roles) if role in {'ma hoc phan', 'ma so hoc phan', 'ma so', 'course code'}]
        if len(columns) != 1:
            continue
        column = columns[0]
        if any(isinstance(row, list) and len(row) > column and isinstance(row[column], str)
               and re.sub(r'\s+', '', row[column]).casefold() == code.casefold() for row in rows):
            matches.add(chunk)
    return matches


def course_table_fields_requested(query: str) -> bool:
    """A code identifies a subject; explicit requested fields favor its row.

    Generic requests for information or a description should retain the
    subject's prose before repeated table rows containing the same code.
    """
    text=' '.join(normalized_tokens(query))
    return bool(re.search(r'\b(?:credits?|tin chi|so tin|may tin|hoc ky|hoc ki|semesters?|terms?|'
                          r'prerequisites?|tien quyet|hoc truoc|course name|subject name|'
                          r'ten mon|ten hoc phan|mon gi|hoc phan gi|called|named)\b',text))


def _named_curriculum_row(cells: list[str], headers: list[str]) -> tuple[set[str], list[str]] | None:
    """Read a subject name from an explicit column, without inventing a code."""
    if not isinstance(headers, list) or any(not isinstance(header, str) for header in headers):
        return None
    name_headers = {"discipline", "subject", "course", "course name", "subject name",
                    "hoc phan", "ten hoc phan", "mon hoc", "ten mon hoc",
                    "học phần", "tên học phần", "môn học", "tên môn học"}
    columns = [i for i, header in enumerate(headers)
               if " ".join(tokenize(header)) in name_headers]
    if len(columns) != 1 or columns[0] >= len(cells):
        return None
    name = cells[columns[0]]
    sequence = tokenize(name)
    # Section markers and totals are not subject identities.
    if (len(name.strip()) < 5 or not sequence
            or " ".join(sequence) in {"compulsory subjects", "elective subjects", "credits per semester"}
            or requested_semesters(name)):
        return None
    return {t for t in normalized_tokens(name) if len(t) >= 3}, sequence


def semester_table_sources(query: str, records: dict[str, dict]) -> list[str]:
    """Locate explicit semester section rows in original tables.

    Document-level semester metadata can describe another page. Only the
    actual table cells establish a semester match here.
    """
    requested = set(requested_semesters(query))
    if not requested:
        return []
    matches = []
    for chunk, item in records.items():
        start = str(item.get('content', '')).find('{"headers"')
        if start < 0:
            continue
        try:
            table = json.loads(item['content'][start:])
        except (ValueError, TypeError):
            continue
        cells = [cell for row in [table.get('headers', []), *table.get('rows', [])]
                 if isinstance(row, list) for cell in row if isinstance(cell, str)]
        present = {semester for cell in cells for semester in requested_semesters(cell)}
        overlap = requested & present
        if overlap:
            matches.append((-len(overlap), chunk))
    return [chunk for _, chunk in sorted(matches)]


def table_acronym_expansion(query: str, records: dict[str, dict]) -> str:
    """Resolve a source row's initialism only when its spelling is unique."""
    abbreviations = set(re.findall(r'\b[A-Z]{3,6}\b', query))
    if not abbreviations:
        return query
    expansions = {abbreviation: set() for abbreviation in abbreviations}
    for item in records.values():
        start = str(item.get('content', '')).find('{"headers"')
        if start < 0:
            continue
        try:
            table = json.loads(item['content'][start:])
        except (ValueError, TypeError):
            continue
        for row in table.get('rows', []):
            if not isinstance(row, list):
                continue
            for cell in row:
                if not isinstance(cell, str):
                    continue
                words = tokenize(cell.replace('\\n', ' '))
                if 3 <= len(words) <= 6 and all(word.isalpha() for word in words):
                    initialism = ''.join(word[0] for word in words).upper()
                    if initialism in expansions:
                        expansions[initialism].add(cell.replace('\\n', ' '))
    return ' '.join([query, *(next(iter(values)) for values in expansions.values() if len(values) == 1)])


def linked_table_sources(query: str, records: dict[str, dict], cap: int,
                         *, include_named_curriculum: bool = False,
                         named_exact_only: bool = False) -> list[str]:
    """Use source row names/codes only, preserving actual chunk provenance."""
    rows = []
    query_phrase = _phrase(query)
    for chunk, item in records.items():
        start = item.get("content", "").find('{"headers"')
        if start < 0:
            continue
        try:
            table = json.loads(item["content"][start:])
        except (ValueError, TypeError):
            continue
        for cells in table.get("rows", []):
            if not isinstance(cells, list) or any(not isinstance(c, str) for c in cells):
                continue
            coded_row = False
            for column, cell in enumerate(cells[:-1]):
                code = re.sub(r"\s+", "", cell)
                if re.fullmatch(r"[A-Z]{2,5}\d{3,5}[A-Z]?", code) and len(cells[column + 1]) >= 5:
                    names = {t for t in normalized_tokens(cells[column + 1]) if len(t) >= 3}
                    codes = re.findall(r"\b[A-Z]{2,5}\s*\d{3,5}[A-Z]?\b", " ".join(cells))
                    rows.append((chunk, item, names, [re.sub(r"\s+", "", c) for c in codes],
                                 tokenize(cells[column + 1])))
                    coded_row = True
            if include_named_curriculum and not coded_row:
                named = _named_curriculum_row(cells, table.get("headers", []))
                if named is not None:
                    names, sequence = named
                    if not named_exact_only or _phrase(" ".join(sequence)) in query_phrase:
                        rows.append((chunk, item, names, [], sequence))
    terms = set(normalized_tokens(query))
    frequencies = Counter(t for _, _, names, _, _ in rows for t in names)
    query_sequence = " " + " ".join(tokenize(query)) + " "
    matches = []
    for chunk, item, names, codes, sequence in rows:
        overlap = names & terms
        rare_hit = any(len(t) >= 5 and frequencies[t] <= 2 for t in overlap)
        name_match = len(overlap) >= 2 and len(overlap) / max(1, len(names)) >= .25
        code_match = any(c.casefold() in terms for c in codes[:1])
        if not (rare_hit or name_match or code_match):
            continue
        score = sum(math.log(1 + len(rows) / frequencies[t]) for t in overlap) + 10 * code_match
        # A named course phrase is more specific than separate words such as
        # "applications" or the program name elsewhere in a long question.
        for width in range(min(8, len(sequence)), 1, -1):
            if any(" " + " ".join(sequence[i:i + width]) + " " in query_sequence
                   for i in range(len(sequence) - width + 1)):
                score += 5 * width * width
                break
        matches.append((score, chunk, item, codes))
    matches.sort(key=lambda row: (-row[0], row[1]))
    result = []
    for score, chunk, item, codes in matches[:2]:
        if score < matches[0][0] * .75:
            continue
        patterns = [re.compile(r"(?<!\w)" + r"\s*".join(re.escape(c) for c in code) + r"(?!\w)", re.I)
                    for code in codes]
        siblings = [key for key, candidate in records.items()
                    if candidate.get("doc_id") == item.get("doc_id") and candidate.get("page") == item.get("page")
                    and any(p.search(candidate.get("content", "")) for p in patterns)]
        # The table stays first; linked fragments retain their source order.
        for key in [chunk, *sorted(siblings)]:
            if key not in result:
                result.append(key)
    return result[:cap]
