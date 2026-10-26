"""Select a contiguous source excerpt without generating or rewriting text."""
import re
from collections import Counter
import math
from ..retrieval.tokenizer_vi import normalized_tokens

_STOP = set('a an the and or of to in on for is are was were be does do did what which how why when '
            'should would could called this that these those it its la cua va hay cho nhung gi nao '
            'the nao tai sao khi mot cac duoc'.split())


def verbatim_window(text: str, question: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    # An explicitly requested article is a stronger source locator than common
    # words repeated in neighbouring articles. Keep the excerpt verbatim.
    requested = set(re.findall(r'\b(?:article|điều|dieu)\s+(\d+)\b', question,
                               flags=re.IGNORECASE))
    if len(requested) == 1:
        number = next(iter(requested))
        headings = list(re.finditer(
            r'(?mi)^[ \t]*(?:article|điều|dieu)\s+(\d+)\s*[:.)]', text))
        matching = [i for i, heading in enumerate(headings)
                    if heading.group(1) == number]
        if len(matching) == 1:
            index = matching[0]
            end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
            text = text[headings[index].start():end]
            if len(text) <= limit:
                return text
    # A named article also identifies the requested source clause. Generic
    # words in neighbouring articles must not win a window that ends at the
    # target title and drops its predicate on the next line. Keep every equally
    # specific match: duplicate titles may disagree, and comparisons need both
    # clauses. Explicit article numbers retain priority above.
    if not requested:
        headings = list(re.finditer(
            r'(?mi)^[ \t]*(?:article|điều|dieu)\s+\d+\s*[:.)]\s*([^\r\n]*)', text))
        query_tokens = normalized_tokens(question)
        phrases = {tuple(query_tokens[i:i + size])
                   for size in range(3, 9) for i in range(len(query_tokens) - size + 1)}
        matches = []
        for heading in headings:
            label = re.split(r'\b(?:is|are|shall|must|được|duoc|có|co)\b',
                             heading[1], maxsplit=1, flags=re.I)[0]
            tokens = normalized_tokens(label)
            matches.append({tuple(tokens[i:i + size]) for size in range(3, 9)
                            for i in range(len(tokens) - size + 1)
                            if tuple(tokens[i:i + size]) in phrases})
        found = set().union(*matches) if matches else set()
        # A shared title prefix is not a second named object. E.g. the prefix
        # "student award" must not outrank a complete, explicitly named award.
        specific = {p for p in found if not any(len(q) > len(p) and any(
                    q[i:i + len(p)] == p for i in range(len(q) - len(p) + 1)) for q in found)}
        selected = [i for i, group in enumerate(matches) if group & specific]
        comparison = re.search(r'\b(?:compare|comparison|difference|versus|so sánh|so sanh)\b', question, re.I)
        if selected and (not comparison or len(selected) > 1):
            first, last = min(selected), max(selected)
            end = headings[last + 1].start() if last + 1 < len(headings) else len(text)
            section = text[headings[first].start():end]
            if len(section) <= limit:
                return section
            if len(selected) == 1:
                text = section
    terms = {t for t in normalized_tokens(question) if len(t) >= 2 and t not in _STOP}
    lines = []
    offset = 0
    for line in text.splitlines(keepends=True):
        matches = terms & set(normalized_tokens(line))
        lines.append((offset + len(line) / 2, matches))
        offset += len(line)
    frequencies = Counter(term for _, matches in lines for term in matches)
    focus = max(lines, key=lambda row: sum(math.log1p(len(lines) / (frequencies[t] + 1))
                                           for t in row[1]))[0] if lines else 0
    starts = {0, max(0, len(text) - limit)}
    starts.update(m.end() for m in re.finditer('\n', text) if m.end() < len(text))
    # Score coverage, not repetition: repeated generic words must not drown
    # a short source condition. No corpus IDs, synonyms or expected answers.
    def excerpt_at(start):
        end = min(len(text), start + limit)
        if end < len(text):
            boundary = text.rfind('\n', start, end)
            if boundary > start:
                end = boundary
        return text[start:end]
    def score(start):
        excerpt = excerpt_at(start)
        return (len(terms & set(normalized_tokens(excerpt))),
                -abs(start + len(excerpt) / 2 - focus), -start)
    start = max(starts, key=score)
    return excerpt_at(start)
