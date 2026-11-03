"""Optional context from a closed policy item in an already cited source.

Structure selects the scope; literal source text supplies every added claim.
The caller must validate the expanded citation and all claims normally.
"""
import json
import re
import unicodedata
from dataclasses import replace
from fractions import Fraction

from .course_credits import folded
from .policies import explicit_comparison_request, sanitize_evidence_text
from .source_citations import sparse_prose_quote, sparse_prose_text
from ..retrieval.tokenizer_vi import source_body


def _compact(text):
    return ' '.join(unicodedata.normalize('NFC', text).casefold().split()).strip(' .;')


def _words(text):
    stop = set(('a an the of to for and or in is are be with as '
                'la va cua cho cac nhung mot duoc theo trong tai co da thi nay khi').split())
    words = set(re.findall(r'\w+', folded(text))) - stop
    return {word[:-1] if re.fullmatch(r'[a-z]{4,}s', word) and not word.endswith('ss') else word for word in words}


def _covered(text, answer):
    words, available = _words(text), _words(answer)
    numbers = lambda value: {m.replace(',', '.') for m in re.findall(r'\d+(?:[.,]\d+)?(?:/\d+(?:[.,]\d+)?)?', value)}
    labels = lambda value: set(re.findall(r'(?<!\w)[A-Z][+-]?(?!\w)', value))
    return (numbers(text) <= numbers(answer) and labels(text) <= labels(answer)
            and len(words & available) / max(1, len(words)) >= .8)


def _bounds(text):
    patterns = {'lower': r'toi thieu|minimum|at least', 'upper': r'toi da|maximum|at most'}
    found = {}
    for key, cue in patterns.items():
        values = set()
        for match in re.finditer(r'\b(?:' + cue + r')\s+(?:(?:bang|la|of|is)\s+)?'
                                 r'(\d+(?:[.,]\d+)?(?:/\d+(?:[.,]\d+)?)?)', folded(text)):
            try:
                parts = [Fraction(part.replace(',', '.')) for part in match[1].split('/')]
                values.add(parts[0] / parts[1] if len(parts) == 2 else parts[0])
            except (ValueError, ZeroDivisionError):
                continue
        found[key] = values
    return found


def _closed_items(body, *, leaf_only=True):
    marker = re.compile(r'(?m)^[ \t]*(?P<label>\d+|[a-zđ])[.)][ \t]*(?:\n[ \t]*)?')
    markers = list(marker.finditer(body))
    for index, start in enumerate(markers):
        label = start['label']
        successor = str(int(label) + 1) if label.isdigit() else chr(ord(label) + 1)
        for end in markers[index + 1:]:
            # A different level may contain its own sub-items, but cannot
            # establish the closing boundary of this item.
            if end['label'].isdigit() != label.isdigit():
                if not label.isdigit(): break
                continue
            if end['label'] != successor: break
            item = body[start.end():end.start()].strip()
            if (len(item) <= 1200 and (not leaf_only or not marker.search(item)) and not re.search(
                    r'(?mi)^\s*(?:điều|article|section|chapter)\s+\d+\b', item)
                    # Accent folding conflates "vị đủ" with "ví dụ".
                    # Unaccented example cues need a clause boundary.
                    and not re.search(r'\b(?:ví dụ|giả sử|example|illustration)\b',item,re.I)
                    and not re.search(r'(?:^|[.:;!?])\s*(?:vi du|gia su)\b',folded(item))
                    and sanitize_evidence_text(item) == item):
                yield body[start.start():end.start()].strip(), item
            break


def _prose_runs(result):
    if result.content_type != 'table':
        yield source_body({'content': result.content}, decode_tables=False), None
        return
    try:
        table = json.loads(result.content[result.content.index('{"headers"'):])
        headers, rows = table['headers'], table['rows']
    except (ValueError, KeyError, TypeError):
        return
    # Never flatten populated table relationships into neighbouring prose.
    for column, header in enumerate(headers):
        if not isinstance(header, str) or header.strip(): continue
        run = []
        for row in [*rows, None]:
            if (isinstance(row, list) and len(row) == len(headers)
                    and all(isinstance(cell, str) for cell in row)
                    and row[column].strip()
                    and all(not cell.strip() for i, cell in enumerate(row) if i != column)):
                run.append(row)
            else:
                prose = sparse_prose_text(table, run) if run else None
                if prose is not None: yield prose, table
                run = []


def policy_item_context(question, answer, claims, citations, results, language):
    """Add at most one missing condition/permission from the same closed item.

    An open chunk, a paraphrased anchor, a comparison, or several plausible
    items cannot license an addition. Optional failure leaves the answer intact.
    """
    if explicit_comparison_request(question) or re.search(
            r'\b(?:chi (?:can|muon)|only|do not add|khong can|khong neu|dung neu)\b', folded(question)):
        return None
    candidates = []
    for citation in citations:
        related = [claim for claim in claims if citation.chunk_id in claim.citation_ids]
        if not related or any(claim.citation_ids != (citation.chunk_id,) for claim in related): continue
        source = next((item for item in results if item.chunk_id == citation.chunk_id), None)
        if source is None: continue
        for body, table in _prose_runs(source):
            for quoted, item in _closed_items(body):
                compact = _compact(item)
                if any(_compact(claim.text) not in compact for claim in related): continue
                # Do not translate a source sentence by guessing. Other
                # languages continue through the ordinary generation path.
                vietnamese = bool(re.search(r'[ăâđêôơưáàảãạấầẩẫậắằẳẵặếềểễệốồổỗộớờởỡợứừửữự]', item, re.I))
                if vietnamese != language.startswith('vi'): continue
                sentences = re.split(r'(?<=[.!?;])\s+(?=[A-ZÀ-Ỹ])', ' '.join(item.split()))
                anchor = ' '.join(claim.text for claim in related)
                denied = bool(re.search(r'\b(?:khong (?:duoc|giai quyet|cho phep)|cannot|not permitted)\b', folded(anchor)))
                extras = []
                for sentence in sentences:
                    norm = folded(sentence)
                    condition = re.search(r'\b(?:tuy nhien|voi dieu kien|can dam bao|provided that|subject to)\b', norm)
                    optional = (re.search(r'^(?:ngoai|in addition to|besides)\b', norm)
                                and re.search(r'\b(?:co the|may|can)\b', norm))
                    permission = (denied and re.search(r'\b(?:duoc dang k[yi]|duoc phep|may|can)\b', norm)
                                  and not re.search(r'\b(?:khong|not|cannot)\b', norm))
                    shared = _words(anchor) & _words(sentence)
                    action_related = len(shared) >= 3 or (len(shared) == 2 and all(len(word) >= 5 for word in shared))
                    if not (condition or optional or permission) or _covered(sentence, answer) or not action_related: continue
                    extras.append(sentence)
                if len(extras) != 1: continue
                if table is not None:
                    _, quote = sparse_prose_quote(table, [quoted])
                else:
                    quote = quoted
                if not quote or len(quote) > 1200: continue
                identities = {claim.claim_id for claim in claims}; index = 1
                while 'policy_context_' + str(index) in identities: index += 1
                extra = {'claim_id': 'policy_context_' + str(index), 'text': extras[0],
                         'citation_ids': [citation.chunk_id]}
                prefix = 'Related rule in the same source item' if language.startswith('en') else 'Quy định cùng mục'
                expanded = answer + '\n\n' + prefix + ': ' + extras[0]
                updated = tuple(replace(ref, quote=quote) if ref.chunk_id == citation.chunk_id else ref for ref in citations)
                candidates.append((expanded, updated, [extra]))
    return candidates[0] if len(candidates) == 1 else None


def verified_field_context(question, answer, claims, citations, language):
    """Expose paired bounds or a dated document reference already proved.

    Use the diagnostic claim's printed context, never document metadata or a
    date merely found elsewhere on the page. No new claim is manufactured.
    """
    from .presentation import calendar_presentation
    if explicit_comparison_request(question) or re.search(
            r'\b(?:chi (?:can|muon)|only|do not add|khong can|khong neu|dung neu)\b', folded(question)):
        return None
    candidates = []
    def references(text):
        return {_compact(match[0]).rstrip('.') for match in re.finditer(
            r'(?<!\w)\d{1,8}/[A-ZĐ][A-ZĐ0-9.-]*(?:/[A-ZĐ0-9.-]+)*(?!\w)', text, re.I)}
    for claim in claims:
        text = ' '.join(claim.text.split())
        norm = folded(text)
        if claim.status != 'supported' or len(claim.citation_ids) != 1 or len(text) > 650: continue
        vietnamese = bool(re.search(r'[ăâđêôơưáàảãạấầẩẫậắằẳẵặếềểễệốồổỗộớờởỡợứừửữự]', text, re.I))
        if vietnamese != language.startswith('vi') or _covered(text, answer): continue
        same_sentence = not re.search(r'[.!?;]\s+[A-ZÀ-Ỹ]', text)
        source_bounds, shown_bounds = _bounds(text), _bounds(answer)
        paired = (same_sentence and all(source_bounds.values())
                  and any(not values <= shown_bounds[key] for key, values in source_bounds.items())
                  and len(_words(text) & _words(answer)) >= 4)
        dates = calendar_presentation(text)[1]
        refs = references(text)
        dated_reference = (re.search(r'\b(?:ban hanh kem theo|issued (?:with|under))\b', norm)
                           and len(refs) == 1 and refs == references(answer)
                           and len(dates) == 1 and next(iter(dates))[0] == 'date'
                           and not calendar_presentation(answer)[1])
        if paired or dated_reference:
            prefix = 'Source context' if language.startswith('en') else 'Thông tin cùng nguồn'
            candidates.append((answer + '\n\n' + prefix + ': ' + text, citations, []))
    return candidates[0] if len(candidates) == 1 else None


def grade_family_context(question, answer, claims, citations, language):
    """Distinguish a requested grade from its one printed +/- counterpart.

    A modifier and its value must both be printed in the same visible mapping;
    they cannot be derived from another school's scale or an uncited row.
    """
    query = folded(question)
    requested = set(re.findall(r'\b(?:diem(?: chu)?|grade|letter)\s+([a-z][+-]?)(?!\w)', query))
    if len(requested) != 1: return None
    grade = next(iter(requested)).upper(); candidates = []
    pattern = re.compile(r'(?mi)^[ \t]*([A-Z][+-]?)[ \t]+(?:quy\s+đổi\s+thành|converts?\s+to)'
                         r'\s+\d+(?:[.,]\d+)?[ \t]*[;.]?[ \t]*$')
    for citation in citations:
        matches = [match for match in pattern.finditer(citation.quote) if match[1][0].upper() == grade[0]]
        if len(matches) != 2 or len({match[1].upper() for match in matches}) != 2: continue
        base = [match for match in matches if match[1].upper() == grade]
        sibling = [match for match in matches if match[1].upper() != grade]
        if not base or not sibling: continue
        if not any(claim.citation_ids == (citation.chunk_id,) and _compact(claim.text) == _compact(base[0][0])
                   for claim in claims): continue
        text = sibling[0][0].strip()
        vietnamese = 'quy đổi' in text.casefold()
        if vietnamese != language.startswith('vi') or _covered(text, answer): continue
        index = 1; identities = {claim.claim_id for claim in claims}
        while 'grade_context_' + str(index) in identities: index += 1
        extra = {'claim_id': 'grade_context_' + str(index), 'text': text, 'citation_ids': [citation.chunk_id]}
        prefix = 'Distinct grade in the same scale' if language.startswith('en') else 'Phân biệt với mức điểm cùng thang'
        candidates.append((answer + '\n\n' + prefix + ': ' + text, citations, [extra]))
    return candidates[0] if len(candidates) == 1 else None


def criterion_scope_context(question, answer, claims, citations, results, language):
    """Remind a personal-decision question to check the remaining criteria.

    This is guidance, not a new personal classification. A closed source group
    must actually contain multiple criteria, with the accepted fact in just
    one child item; an isolated threshold cannot establish that scope.
    """
    query = folded(question)
    if (not (re.search(r'\b(?:em|minh|toi|e|t|my|i|me|du kien nay)\b', query)
                 or re.search(r'\b(?:cpa|gpa|dieu kien|canh bao)\b',query))
            or not re.search(r'\b(?:bi|duoc|ko|khong|can|bao nhieu|eligible|will|am|can)\b', query)
            or re.search(r'\b(?:dieu kien khac|kiem tra them|xet them|other criteria|other conditions)\b', folded(answer))):
        return None
    candidates = []
    for citation in citations:
        related = [claim for claim in claims if citation.chunk_id in claim.citation_ids]
        if not related or any(claim.citation_ids != (citation.chunk_id,) for claim in related): continue
        source = next((item for item in results if item.chunk_id == citation.chunk_id), None)
        if source is None or source.content_type == 'table': continue
        body = source_body({'content': source.content}, decode_tables=False)
        for quoted, item in _closed_items(body, leaf_only=False):
            markers = list(re.finditer(r'(?m)^[ \t]*(?:[a-zđ][)]|[-–—•~])\s+', item))
            if len(markers) < 2: continue
            heading = item[:markers[0].start()]
            if not re.search(r'\b(?:dieu kien|danh gia|conditions?|criteria|assessment|eligibility|requirements?)\b', folded(heading)):
                continue
            children = [item[marker.end():markers[i+1].start() if i+1 < len(markers) else len(item)]
                        for i, marker in enumerate(markers)]
            matches = [child for child in children if all(_compact(claim.text) in _compact(child) for claim in related)]
            if len(matches) != 1: continue
            vietnamese = bool(re.search(r'\b(?:dieu kien|danh gia)\b', folded(heading)))
            if vietnamese != language.startswith('vi'): continue
            guidance = ('This checks the criterion you described. To assess your full situation, check the other criteria in the same source section.'
                        if language.startswith('en') else
                        'Đây là đối chiếu theo điều kiện bạn vừa nêu. Để kết luận đầy đủ, cần kiểm tra cả các điều kiện khác trong cùng mục nguồn.')
            updated = tuple(replace(ref, quote=quoted) if ref.chunk_id == citation.chunk_id else ref for ref in citations)
            candidates.append((answer + '\n\n' + guidance, updated, []))
    return candidates[0] if len(candidates) == 1 else None


def complete_policy_context(question, answer, claims, citations, results, language):
    if explicit_comparison_request(question) or re.search(
            r'\b(?:chi (?:can|muon)|only|do not add|khong can|khong neu|dung neu)\b', folded(question)):
        return None
    return (verified_field_context(question, answer, claims, citations, language)
            or policy_item_context(question, answer, claims, citations, results, language)
            or grade_family_context(question, answer, claims, citations, language)
            or criterion_scope_context(question, answer, claims, citations, results, language))
