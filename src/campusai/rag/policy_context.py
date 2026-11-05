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


def _missing_qualifier(text, answer):
    norm=folded(text)
    if (len(re.findall(r'\b(?:danh cho|ap dung|doi voi|provided that|eligible|applies to)\b',norm))!=1
            or re.search(r'\b(?:trong khi|whereas)\b',norm)):
        return False
    qualifiers=re.findall(r'\b(?:danh cho|doi voi|ap dung cho|applies to|provided that)\s+'
        r'(.+?)(?=\bva (?:duoc|phai|co the)\b|[.;]|$)',norm)
    return any(not _words(scope)<=_words(answer) for scope in qualifiers)


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
    marker = re.compile(r'(?m)^[ \t]*(?P<label>\d+|[a-zđ])[.)](?!\d)[ \t]*(?:\n[ \t]*)?')
    # Preserve offsets into the original quote while recognizing PDF line
    # boundaries in LF, CRLF and CR text alike.
    markers = list(marker.finditer(body.replace('\r', '\n')))
    alphabets=('abcdefghijklmnopqrstuvwxyz','abcdđefghijklmnopqrstuvwxyz')
    def follows(first,second):
        if first.isdigit() and second.isdigit():return int(second)==int(first)+1
        return any(first in order and second in order and order.index(second)==order.index(first)+1 for order in alphabets)
    for index, start in enumerate(markers):
        label = start['label']
        parent=None
        if not label.isdigit():
            parents=[i for i,m in enumerate(markers[:index]) if m['label'].isdigit()]
            if parents:
                position=parents[-1]
                siblings=''.join(m['label'] for m in markers[position+1:index+1])
                if any(order.startswith(siblings) for order in alphabets):parent=markers[position]['label']
        for end in markers[index + 1:]:
            # The next parent closes its final lettered child only when the
            # actual a/b/c... siblings establish the hierarchy. An orphaned
            # last child or a chunk boundary is not evidence of completion.
            if end['label'].isdigit() != label.isdigit():
                if label.isdigit():continue
                if parent is None or not follows(parent,end['label']):break
            elif not follows(label,end['label']):break
            item = body[start.end():end.start()].strip()
            if (len(item) <= 1200 and (not leaf_only or not marker.search(item.replace('\r', '\n'))) and not re.search(
                    r'(?mi)^\s*(?:điều|article|section|chapter)\s+\d+\b', item)
                    # Accent folding conflates "vị đủ" with "ví dụ".
                    # Unaccented example cues need a clause boundary.
                    and not re.search(r'\b(?:ví dụ|giả sử|example|illustration)\b',item,re.I)
                    and not re.search(r'(?:^|[.:;!?])\s*(?:vi du|gia su)\b',folded(item))
                    and sanitize_evidence_text(item) == '\n'.join(item.splitlines())):
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


def _closed_star_criteria(body):
    """A following same-level requirements heading closes a bullet group.

    An end-of-chunk or an isolated footnote does not prove completion. Keep
    the original heading, conditions and exact source span together.
    """
    markers=list(re.finditer(r'(?m)^[ \t]*\*[ \t]+([^\r\n]+)\n',body.replace('\r','\n')))
    for start,end in zip(markers,markers[1:]):
        if not all(re.search(r'\b(?:dieu kien|conditions?|requirements?)\b',folded(m[1])) for m in [start,end]):
            continue
        quoted=body[start.start():end.start()].strip()
        if (len(quoted)<=1200 and sanitize_evidence_text(quoted)=='\n'.join(quoted.splitlines())
                and not re.search(r'\b(?:ví dụ|giả sử|example|illustration)\b',quoted,re.I)
                and not re.search(r'(?:^|[.:;!?])\s*(?:vi du|gia su)\b',folded(quoted))):
            yield quoted,quoted


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
            # Use the smallest structurally closed node containing all cited
            # claims. A multi-item answer may need their common parent; using
            # one child's quote would silently drop the other claims' proof.
            items=[(quoted,item) for quoted,item in _closed_items(body,leaf_only=False)
                   if all(_compact(claim.text) in _compact(item) for claim in related)]
            shortest=min((len(quoted) for quoted,_ in items),default=None)
            for quoted, item in items:
                if len(quoted)!=shortest:continue
                compact = _compact(item)
                if any(_compact(claim.text) not in compact for claim in related): continue
                # Do not translate a source sentence by guessing. Other
                # languages continue through the ordinary generation path.
                vietnamese = bool(re.search(r'[ăâđêôơưáàảãạấầẩẫậắằẳẵặếềểễệốồổỗộớờởỡợứừửữự]', item, re.I))
                if vietnamese != language.startswith('vi'): continue
                sentences = re.split(r'(?<=[.!?;])\s+(?=[A-ZÀ-Ỹ])', ' '.join(item.split()))
                anchor = ' '.join(claim.text for claim in related)
                denied = bool(re.search(r'\b(?:khong (?:duoc|giai quyet|cho phep)|cannot|not permitted)\b', folded(anchor)))
                permission_cue=r'duoc dang k[yi]|duoc phep' if language.startswith('vi') else r'may|can'
                grants_permission=bool(re.search(r'\b(?:'+permission_cue+r')\b',folded(anchor))) and not denied
                def action_related(sentence):
                    shared=(_words(anchor)&_words(sentence))-{'may','can','must','not','khong','phai'}
                    short_action=(grants_permission and all(len(word)>=3 for word in shared)
                        and not shared&{'nguoi','hoc','sinh','vien','person','student','visitor','people'})
                    return len(shared)>=3 or len(shared)==2 and (all(len(word)>=5 for word in shared) or short_action)
                extras = []
                for sentence in sentences:
                    norm = folded(sentence)
                    # Keep an eligibility qualifier in the very sentence
                    # containing the accepted fact. A short copied suffix
                    # (e.g. a deadline) must not drop its governing subject.
                    same_sentence=(all(_compact(claim.text) in _compact(sentence) for claim in related)
                        and len(re.findall(r'\b(?:danh cho|ap dung|doi voi|provided that|eligible|applies to)\b',norm))==1
                        and not re.search(r'\b(?:trong khi|whereas)\b',norm))
                    missing_scope=same_sentence and _missing_qualifier(sentence,answer)
                    condition = re.search(r'\b(?:tuy nhien|voi dieu kien|can dam bao|chi ap dung|provided that|subject to|only applies)\b', norm)
                    optional = (re.search(r'^(?:ngoai|in addition to|besides)\b', norm)
                                and re.search(r'\b(?:co the|may|can)\b', norm))
                    permission = (denied and re.search(r'\b(?:duoc dang k[yi]|duoc phep|may|can)\b', norm)
                                  and not re.search(r'\b(?:khong|not|cannot)\b', norm))
                    if (not (condition or optional or permission or same_sentence)
                            or _covered(sentence, answer) and not missing_scope or not action_related(sentence)): continue
                    extras.append(sentence)
                # Outcomes and exclusions may follow an accepted fact in the
                # same short closed leaf. Preserve the whole item verbatim;
                # never borrow an adjacent sibling or invent a summary.
                if (2<=len(sentences)<=3 and len(item)<=650
                        and not re.search(r'(?m)^\s*(?:\d+|[a-zđ])[.)]\s*',item)
                        and all(action_related(sentence) for sentence in sentences if not _words(sentence)<=_words(answer))
                        and (not _covered(item,answer) or not _words(item)<=_words(answer))):
                    extras=[' '.join(item.split())]
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
        if (vietnamese != language.startswith('vi')
                or _covered(text, answer) and not _missing_qualifier(text,answer)): continue
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
        scoped=(same_sentence and text.endswith(('.', ';')) and _missing_qualifier(text,answer)
                and len(_words(text)&_words(answer))>=3)
        if paired or dated_reference or scoped:
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


def application_checklist_context(question, answer, claims, citations, results, language):
    """Keep an explicitly printed application checklist beside its cited rule.

    Only a closed bullet list immediately following the accepted fact qualifies.
    Every attachment remains literal source text, checked again by the caller.
    """
    candidates=[]
    for citation in citations:
        related=[claim for claim in claims if citation.chunk_id in claim.citation_ids]
        source=next((row for row in results if row.chunk_id==citation.chunk_id),None)
        if (not related or source is None or source.content_type=='table'
                or any(claim.citation_ids!=(citation.chunk_id,) for claim in related)):
            continue
        body=source_body({'content':source.content},decode_tables=False)
        lines=[];offset=0
        for line in body.splitlines(keepends=True):
            lines.append((offset,offset+len(line),line.strip()))
            offset+=len(line)
        for index,(start,end,heading) in enumerate(lines):
            if not re.fullmatch(r'(?:ho so|giay to|documents|paperwork)\b.{0,120}:',folded(heading)):
                continue
            if language.startswith('vi') != bool(re.match(r'(?:ho so|giay to)\b',folded(heading))):
                continue
            prefix=body[max(0,start-650):start]
            if (not all(_compact(claim.text) in _compact(prefix) for claim in related)
                    or len(_words(heading)&_words(' '.join(c.text for c in related)))<2):
                continue
            entries=[];current=[];list_end=end;closed=False
            for line_start,line_end,text in lines[index+1:]:
                if not text:continue
                bullet=re.match(r'^[+•–—-]\s+(.+)',text)
                if bullet:
                    if current:
                        if not current[-1].endswith(('.', ';')):break
                        entries.append(' '.join(current))
                    current=[bullet[1]]
                elif current and not current[-1].endswith(('.', ';')):
                    current.append(text)
                else:
                    if current:entries.append(' '.join(current))
                    closed=bool(current)
                    break
                list_end=line_end
                if list_end-start>900 or len(entries)>=6:break
            if not closed or not 2<=len(entries)<=6:continue
            quote=citation.quote
            # Retain every existing claim and its exact source proof when
            # expanding; an unrelated earlier or later rule cannot be dropped.
            anchor=body.rfind(quote,0,start)
            if anchor<0:continue
            quote=body[anchor:list_end].strip()
            if (len(quote)>1200 or sanitize_evidence_text(quote)!='\n'.join(quote.splitlines())
                    or re.search(r'\b(?:ví dụ|giả sử|example|illustration)\b',quote,re.I)):
                continue
            extras=[text for text in entries if not _covered(text,answer)]
            if not extras:continue
            identities={claim.claim_id for claim in claims};extra=[];number=1
            for text in extras:
                while 'checklist_context_'+str(number) in identities:number+=1
                ident='checklist_context_'+str(number);identities.add(ident)
                extra.append({'claim_id':ident,'text':text,'citation_ids':[citation.chunk_id]})
            label='Documents listed in the source' if language.startswith('en') else 'Hồ sơ theo tài liệu'
            expanded=answer+'\n\n'+label+':\n'+'\n'.join('- '+text for text in extras)
            updated=tuple(replace(ref,quote=quote) if ref.chunk_id==citation.chunk_id else ref for ref in citations)
            candidates.append((expanded,updated,extra))
    return candidates[0] if len(candidates)==1 else None


def criterion_scope_context(question, answer, claims, citations, results, language):
    """Remind a personal-decision question to check the remaining criteria.

    This is guidance, not a new personal classification. A closed source group
    must actually contain multiple criteria, with the accepted fact in just
    one child item; an isolated threshold cannot establish that scope.
    """
    query = folded(question)
    if (not (re.search(r'\b(?:em|minh|toi|e|t|my|i|me|du kien nay)\b', query)
                 or re.search(r'\b(?:cpa|gpa|dieu kien|canh bao)\b',query))
            or not re.search(r'\b(?:bi|duoc|ko|khong|can|bao nhieu|la gi|eligible|will|am|can|what)\b', query)
            or re.search(r'\b(?:dieu kien khac|kiem tra them|xet them|other criteria|other conditions)\b', folded(answer))):
        return None
    candidates = []
    for citation in citations:
        related = [claim for claim in claims if citation.chunk_id in claim.citation_ids]
        if not related or any(claim.citation_ids != (citation.chunk_id,) for claim in related): continue
        source = next((item for item in results if item.chunk_id == citation.chunk_id), None)
        if source is None or source.content_type == 'table': continue
        body = source_body({'content': source.content}, decode_tables=False)
        starred=list(_closed_star_criteria(body))
        for quoted, item in starred or _closed_items(body, leaf_only=False):
            markers = list(re.finditer(r'(?m)^[ \t]*(?:[a-zđ][)]|[-–—•~])\s+', item.replace('\r','\n')))
            if len(markers) < 2: continue
            heading = item[:markers[0].start()]
            if not re.search(r'\b(?:dieu kien|danh gia|conditions?|criteria|assessment|eligibility|requirements?)\b', folded(heading)):
                continue
            children = [item[marker.end():markers[i+1].start() if i+1 < len(markers) else len(item)]
                        for i, marker in enumerate(markers)]
            matches = [child for child in children if any(_compact(claim.text) in _compact(child) for claim in related)]
            if (not matches or len(matches)==len(children)
                    or not all(any(_compact(claim.text) in _compact(child) for child in matches) for claim in related)):
                continue
            vietnamese = bool(re.search(r'\b(?:dieu kien|danh gia)\b', folded(heading)))
            if vietnamese != language.startswith('vi'): continue
            guidance = ('This checks the criterion you described. To assess your full situation, check the other criteria in the same source section.'
                        if language.startswith('en') else
                        'Đây là đối chiếu theo điều kiện bạn vừa nêu. Để kết luận đầy đủ, cần kiểm tra cả các điều kiện khác trong cùng mục nguồn.')
            updated = tuple(replace(ref, quote=quoted) if ref.chunk_id == citation.chunk_id else ref for ref in citations)
            expanded=answer + '\n\n' + guidance;extra=[]
            # A closed, explicitly headed requirements group can expose its
            # other criteria, not just an unspecified caveat. This is source
            # text, not a personal eligibility conclusion or a new rule.
            if starred:
                others=[child.strip() for child in children if child not in matches]
                if (0<len(others)<=2 and all(len(child)<=500 and child.endswith(('.', ';'))
                        for child in others)):
                    identities={claim.claim_id for claim in claims};index=1
                    for text in others:
                        if _covered(text,answer):continue
                        while 'criterion_context_'+str(index) in identities:index+=1
                        ident='criterion_context_'+str(index);identities.add(ident)
                        extra.append({'claim_id':ident,'text':text,'citation_ids':[citation.chunk_id]})
                    if extra:expanded+='\n'+'\n'.join('- '+claim['text'] for claim in extra)
            candidates.append((expanded, updated, extra))
    return candidates[0] if len(candidates) == 1 else None


def complete_policy_context(question, answer, claims, citations, results, language):
    if explicit_comparison_request(question) or re.search(
            r'\b(?:chi (?:can|muon)|only|do not add|khong can|khong neu|dung neu)\b', folded(question)):
        return None
    return (policy_item_context(question, answer, claims, citations, results, language)
            or application_checklist_context(question, answer, claims, citations, results, language)
            or verified_field_context(question, answer, claims, citations, language)
            or grade_family_context(question, answer, claims, citations, language)
            or criterion_scope_context(question, answer, claims, citations, results, language))
