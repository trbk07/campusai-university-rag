"""Require source support for explicitly requested academic subjects."""
from __future__ import annotations

import re
import unicodedata
import json

from .routing import detected_course_codes
from .tokenizer_vi import source_body


def _fold(text: str) -> str:
    value = unicodedata.normalize('NFKD', text.casefold().replace('đ', 'd'))
    return ' '.join(value.encode('ascii', 'ignore').decode('ascii').split())


def source_filename_references(query,documents):
    """Return literal authorized filename spans and unresolved PDF names.

    Filenames identify source scope, never facts. Match full names before
    shorter suffixes, preserving spaces, Unicode and duplicate-name ambiguity.
    No user path is opened or used to discover an unselected document.
    """
    names={}
    key=lambda name:' '.join(name.casefold().split())
    for document in documents:
        for item in document.get('items',[]):
            name=(item.get('metadata') or {}).get('source_name')
            if isinstance(name,str) and name.casefold().endswith('.pdf'):
                entry=names.setdefault(key(name),[name,set()])
                entry[1].add(document['doc_id'])
    quoted=list(re.finditer(r'["“\']([^"”\'\r\n]{1,240}\.pdf)["”\']',query,re.I))
    unknown=[m[1] for m in quoted if key(m[1]) not in names]
    protected=[m.span(1) for m in quoted if key(m[1]) not in names]
    candidates=[]
    for name,owners in names.values():
        pattern=r'(?<![\w.-])'+r'\s+'.join(map(re.escape,name.split()))+r'(?![\w.])'
        for match in re.finditer(pattern,query,re.I):
            if any(a<=match.start() and match.end()<=b for a,b in protected):continue
            candidates.append((match.start(),match.end(),name,tuple(sorted(owners))))
    chosen=[]
    for ref in sorted(candidates,key=lambda r:(-(r[1]-r[0]),r[0])):
        if not any(ref[0]<old[1] and old[0]<ref[1] for old in chosen):chosen.append(ref)
    residual=list(query)
    for start,end,_name,_owners in chosen:
        residual[start:end]=' '*(end-start)
    unknown.extend(m[1] for m in re.finditer(r'(?<![\w.])([\w.-]+\.pdf)(?![\w.])',''.join(residual),re.I))
    return sorted(chosen),tuple(dict.fromkeys(unknown))


def _curriculum_headings(records):
    """Read only explicit local programme headings, never inferred metadata."""
    headings={};siblings=[]
    def remember(key,priority,name):
        previous=headings.get(key)
        if previous is None or priority>previous[0]:headings[key]=(priority,name)
        elif priority==previous[0] and name!=previous[1]:headings[key]=(priority,None)
    for item in records.values():
        # Read the literal page text, not the generated context header.
        for line in source_body(item).splitlines():
            value=_fold(line)
            priority=0
            match=re.match(r'^\d+[.)]?\s+(?:nganh|program(?:me)?)\s+(.{2,100})$',value)
            if not match:
                match=re.match(r'^(?:chuyen nganh|chuong trinh)\s+dao tao\s*:\s*(.{2,100})$',value)
                priority=1
            if not match:
                # A catalogue may omit "Ngành" from one numbered sibling
                # title. Require the same literal root heading in source text
                # and the parsed hierarchy, not a document-wide programme tag.
                path=item.get('metadata',{}).get('heading_path',[])
                bare=re.match(r'^\d+[.)]?\s+(.{2,100})$',line.strip())
                if (item.get('content_type','text')=='text' and bare
                        and bare[1].isupper() and not any(c.isdigit() for c in bare[1])
                        and isinstance(path,list) and path and _fold(path[0])==value):
                    name=' '.join(re.findall(r'[a-z]+',_fold(bare[1])))
                    if 2<=len(name.split())<=12:
                        siblings.append(((item['doc_id'],int(item['page'])),name))
                continue
            name=re.split(r'\s*\(?\d+\s*(?:tin chi|credits?)\b',match[1],maxsplit=1)[0]
            name=' '.join(re.findall(r'[a-z]+',name))
            if not name or len(name.split())>12:continue
            key=(item['doc_id'],int(item['page']))
            remember(key,priority,name)
    catalogue_docs={doc for doc,_ in headings}
    for key,name in siblings:
        if key[0] in catalogue_docs:remember(key,0,name)
    return headings


def _curriculum_query(query):
    text=' '.join(re.sub(r'[^a-z0-9]+',' ',_fold(query)).split())
    return text if re.search(r'\b(?:nganh|chuyen nganh|chuong trinh|ke hoach|tien trinh|so do|diagram|study plan|curriculum|program(?:me)?|hk\s*\d+|hoc k[yi]\s*\d+)\b',text) else ''


def _matching_programmes(query,headings):
    text=_curriculum_query(query)
    if not text:return set()
    names={name for _,name in headings.values() if name}
    def literal_matches(value):
        return {name for name in names for match in re.finditer(r'(?<!\w)'+re.escape(name)+r'(?!\w)',value)
                if not re.search(r'\b(?:mon|hoc phan|course|subject)\s*$',value[:match.start()])}
    # An explicit new programme takes precedence over a previous user topic.
    raw=query.partition('\nContext topic (untrusted user input): ')[0]
    raw=' '.join(re.sub(r'[^a-z0-9]+',' ',_fold(raw)).split())
    matched=literal_matches(raw) or literal_matches(text)
    if matched:
        # "Accounting" is not a second requested programme when contained in
        # the explicit longer name "Accounting - Auditing".
        matched={name for name in matched if not any(name!=other and re.search(
            r'(?<!\w)'+re.escape(name)+r'(?!\w)',other) for other in matched)}
    if not matched:
        aliases={}
        for name in names:
            alias=''.join(word[0] for word in name.split())
            if len(alias)>=3:aliases.setdefault(alias,set()).add(name)
        matched=set().union(*(values for alias,values in aliases.items()
                              if len(values)==1 and re.search(r'(?<!\w)'+re.escape(alias)+r'(?!\w)',text))) if aliases else set()
    return matched


def explicit_source_documents(query,documents):
    """Source-only locator resolution, not an institutional-policy inference.

    A unique literal course code or programme heading selects documents just
    as a user-specified filename would. Ambiguous/absent anchors remain open;
    no answer, expected page, or evaluation label is used to pick a source.
    """
    raw=query.partition('\nContext topic (untrusted user input): ')[0]
    codes=detected_course_codes(raw)
    if codes:
        owners=[]
        for code in codes:
            pattern=re.compile(r'(?<!\w)'+r'\s*'.join(map(re.escape,code))+r'(?!\w)',re.I)
            owners.append({doc['doc_id'] for doc in documents if any(
                pattern.search(source_body(item)) for item in doc.get('items',[]))})
        # Several requested codes must all belong to the same source; a union
        # could hide a missing code or collapse an actual cross-document task.
        return set.intersection(*owners) if owners else set()
    if _curriculum_query(raw):
        records={str(i):{**item,'doc_id':doc['doc_id']} for i,(doc,item) in enumerate(
            (doc,item) for doc in documents for item in doc.get('items',[]))}
        headings=_curriculum_headings(records)
        matched=_matching_programmes(raw,headings)
        if matched:
            return {doc for (doc,_),(_,name) in headings.items() if name in matched} if len(matched)==1 else set()
    return _literal_location_documents(raw,documents)


def _prose_list_labels(body, query):
    """Read a named list field in a wrapped lead-in, not arbitrary body hits.

    Some PDFs print a mapping as prose rather than a drawn table. Require a
    numbered lead-in, two following short label:value entries, and a field
    explicitly called a table/list by the user. Values never choose a source.
    """
    stops=set('pages page tai o tren theo cho la thi co cua in on at from'.split())
    fields=set()
    # Remove coordinates before word boundaries: Vietnamese "trạng" folds
    # to "trang" too, and must remain part of a printed field name.
    named=re.sub(r'\b(?:trang|pages?)\s+\d+\b',' ',_fold(query))
    for match in re.finditer(r'\b(?:bang|table|danh sach|list)\s+(?:of\s+)?([a-z ]{3,90})',named):
        words=[]
        for word in match[1].split():
            if word in stops or len(words)==5:break
            words.append(word)
        if 2<=len(words)<=5:fields.add(' '.join(words))
    if not fields:return []
    entries=list(re.finditer(r'(?m)^\s*[^\W\d_][\w+\-]{0,9}\s*:\s*\S[^\r\n]{0,100}$',body))
    labels=[]
    for first,second in zip(entries,entries[1:]):
        # Intervening sections/prose cannot turn unrelated colon lines into
        # a mapping. The bounded lead-in must introduce this actual list.
        if body[first.end():second.start()].strip():continue
        lead=body[max(0,first.start()-650):first.start()]
        markers=list(re.finditer(r'(?m)^\s*(?:\d+|[a-zđ])[.)]\s*',lead))
        if not markers:continue
        lead=lead[markers[0].start():].strip()
        if not lead.endswith(':') or re.search(r'(?mi)^\s*(?:điều|article|chapter|section)\s+\d+\b',lead):continue
        text=_fold(lead)
        labels.extend((field,'table') for field in fields
                      if re.search(r'(?<!\w)'+re.escape(field)+r'(?!\w)',text))
    return labels


def _literal_location_documents(query,documents):
    """Resolve an explicit page/article AND a printed title, never a value.

    A page number alone, metadata heading, generic keyword or missing title
    does not identify a PDF. Keep all matching owners; the caller handles
    duplicate institutions/ambiguity and the normal answer proof still runs.
    """
    from ..rag.page_queries import page_intervals
    try:intervals=page_intervals(query)
    except ValueError:return set()
    if (any(start<1 or end<start for start,end in intervals)
            or sum(end-start+1 for start,end in intervals)>12):return set()
    articles=set(re.findall(r'\b(?:dieu|article|section|chapter)\s+(\d+)\b',_fold(query)))
    if not intervals and not articles:return set()
    # An unread competing source cannot establish unique title ownership.
    if any(item.get('metadata',{}).get('coverage_complete') is False
           for doc in documents for item in doc.get('items',[])):return set()
    tokens=lambda text:tuple(re.findall(r'[a-z]+',_fold(text)))
    content_query=re.sub(r'\b(?:dieu|article|section|chapter|pages?|trang)\s+\d+\b',' ',_fold(query))
    words=tokens(content_query)
    # "án" folds to English "an"; keep it as a content token so a literal
    # Vietnamese đồ án title is not lost to a bilingual stop-word collision.
    generic=set('the and of to in on at for is are what which how a '
        'la va cua cho trong tai o theo co gi nao noi ve trang page article section chapter'.split())
    phrases={words[i:i+n] for n in [2,3] for i in range(len(words)-n+1)
             if all(len(word)>=2 for word in words[i:i+n]) and not any(word in generic for word in words[i:i+n])}
    def matches(label,kind):
        title=tokens(label)
        if not 2<=len(title)<=32:return False
        if all(len(word)>=2 for word in title) and any(
                words[i:i+len(title)]==title for i in range(len(words)-len(title)+1)):
            return True
        if kind=='table':return False  # A table column needs its complete label.
        spans=[(i,i+n) for n in [2,3] for i in range(len(title)-n+1) if title[i:i+n] in phrases]
        return (any(end-start>=3 for start,end in spans)
                or any(a[1]<=b[0] or b[1]<=a[0] for a in spans for b in spans))
    found=set()
    for doc in documents:
        for item in doc.get('items',[]):
            page=item.get('page')
            if intervals and (type(page) is not int or not any(a<=page<=b for a,b in intervals)):continue
            body=source_body(item,decode_tables=False)
            labels=[]
            for line in body.splitlines():
                heading=re.match(r'^\s*(?:dieu|article|section|chapter)\s+(\d+)\s*[.:)]\s*(.+)$',_fold(line))
                if heading:
                    if not articles or heading[1] in articles:labels.append((heading[2],'article'))
                elif not articles:
                    heading=re.match(r'^\s*\d+[.)]\s+(.{3,180}):\s*$',_fold(line))
                    if heading:labels.append((heading[1],'subheading'))
            if not articles and item.get('content_type')=='table':
                start=body.find('{')
                try:table,_=json.JSONDecoder().raw_decode(body[start:]) if start>=0 else ({},0)
                except (ValueError,TypeError):table={}
                if isinstance(table,dict) and isinstance(table.get('headers'),list):
                    labels.extend((header,'table') for header in table['headers'] if isinstance(header,str))
            elif not articles and intervals:
                labels.extend(_prose_list_labels(body,query))
            if any(matches(label,kind) for label,kind in labels):found.add(doc['doc_id'])
    return found


def curriculum_scope_records(query: str, records: dict[str, dict]) -> dict[str, dict]:
    """Exclude other programmes only from literal local section ownership."""
    if not _curriculum_query(query):return records
    headings=_curriculum_headings(records)
    matched=_matching_programmes(query,headings)
    if len(matched)!=1:return records
    chosen=next(iter(matched));by_doc={}
    for (doc,page),(_priority,name) in headings.items():by_doc.setdefault(doc,[]).append((page,name))
    for values in by_doc.values():values.sort()
    scoped={}
    for key,item in records.items():
        markers=by_doc.get(item['doc_id'],[])
        span=item.get('page_range') or item.get('metadata',{}).get('page_range') or [item['page'],item['page']]
        if (not isinstance(span,(list,tuple)) or len(span)!=2 or any(type(p) is not int for p in span)
                or not 1<=span[0]<=item['page']<=span[1]):continue
        checkpoints=[span[0],span[1],*(page for page,_ in markers if span[0]<page<span[1])]
        owners=[]
        for point in checkpoints:
            preceding=[name for page,name in markers if page<=point]
            owners.append(preceding[-1] if preceding else None)
        # A chunk crossing into a different programme cannot prove a value
        # for the requested one; do not choose which part of its body to trust.
        if all(owner is None or owner==chosen for owner in owners):scoped[key]=item
    return scoped


def unsupported_source_reason(query: str, records: dict[str, dict]) -> str | None:
    """Reject absent subjects using the actual selected and filtered sources.

    A positive subject match only permits normal retrieval; it never certifies
    that the retrieved evidence answers a question. Candidate generation uses
    the same scope check. No benchmark labels or source identities are used.
    """
    raw = query.split('\nContext topic (untrusted user input): ', 1)[0]
    question = _fold(raw)
    bodies = [_fold(source_body(item)) for item in records.values()]
    personal_grade = re.search(r'\b(?:gpa|diem thi|diem (?:trung binh|tich luy)|exam score|grades?)\b', question)
    personal_owner = re.search(r'\b(?:cua (?:minh|em|toi|t)|my|of mine)\b', question)
    if personal_grade and personal_owner:
        # Institutional rules cannot reveal a student's current grades.
        # A source must actually be a grade report/transcript, rather than a
        # curriculum containing course credit numbers.
        transcript = any(
            item.get('metadata', {}).get('document_type') in {'academic_transcript', 'grade_report', 'student_results'}
            or re.match(r'(?:bang diem|academic transcript|grade report|student results)\b', body)
            for item, body in zip(records.values(), bodies))
        if not transcript:
            return 'personal_grade_record_not_in_selected_sources'
    codes = detected_course_codes(raw)
    for code in codes:
        pattern = re.compile(r'(?<!\w)' + r'\s*'.join(map(re.escape, code)) + r'(?!\w)', re.I)
        if not any(pattern.search(source_body(item)) for item in records.values()):
            return 'course_code_not_in_selected_sources'
    exam_schedule = re.search(
        r'\b(?:exam(?:ination)?\s+(?:date|time|schedule)|'
        r'(?:ngay(?:\s+va\s+gio)?|gio|lich)\s+(?:thi|kiem tra)|bao gio thi)\b', question)
    if exam_schedule:
        # Credits, assessment weights and a document's issue date do not
        # establish an exam appointment. Require a calendar/clock value in
        # a source passage about an exam. This only admits retrieval; normal
        # evidence/answer checks must still verify the requested course/time.
        months = r'(?:january|february|march|april|may|june|july|august|september|october|november|december)'
        day, month = r'(?:0?[1-9]|[12]\d|3[01])', r'(?:0?[1-9]|1[0-2])'
        calendar = (rf'\b(?:{day}[/-]{month}(?:[/-]\d{{2,4}})?|'
                    rf'\d{{4}}-{month}-{day}|(?:[01]?\d|2[0-3])[:h][0-5]\d|'
                    r'(?:ngay|day)\s+\d{1,2}|thang\s+\d{1,2}|'
                    r'(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)|'
                    rf'{months}\s+{day}(?:st|nd|rd|th)?|{day}\s+{months}|(?:in|during)\s+{months})\b')
        # Accent folding maps "máy" to English "May", and "thị giác" /
        # "thí điểm" to a token that resembles an exam. Those source phrases
        # cannot supply calendar support for an appointment.
        exam_marker = r'\b(?:exams?|examinations?|thi(?!\s+(?:diem|giac|truong|cong|dua)\b)|kiem tra)\b'
        supported = any(
            re.search(calendar, passage[max(0, match.start()-160):match.end()+160])
            for body in bodies for passage in re.split(r'[!?;]|\.(?!\d)', body)
            for match in re.finditer(exam_marker, passage))
        if not supported:
            return 'exam_schedule_not_in_selected_sources'
    subjects = (
        (r'\b(?:scholarships?|hoc bong|hb|kkht|ho tro hoc tap)\b',
         r'\b(?:scholarships?|hoc bong|ho tro hoc tap)\b'),
        (r'\b(?:academic warning|canh bao hoc vu|cbhv)\b',
         r'\b(?:academic warning|canh bao hoc vu)\b'),
        (r'\b(?:gpa|diem (?:trung binh|tich luy)|grade point average)\b',
         r'\b(?:gpa|diem (?:trung binh|tich luy)|grade point average)\b'),
        (r'\b(?:hoc cai thien|grade replacement|replace.*grade)\b',
         r'\b(?:hoc cai thien|grade replacement|replace.*grade)\b'),
    )
    for requested, supported in subjects:
        mentions = [match for match in re.finditer(requested, question)
                    if not re.search(r'(?:khong phai|not|rather than)\s*$', question[:match.start()])]
        if mentions and not any(re.search(supported, body) for body in bodies):
            return 'academic_subject_not_in_selected_sources'
    grade = r'\b(?:gpa|diem (?:trung binh|tich luy)|grade point average)\b'
    graduation = r'\b(?:tot nghiep|graduat(?:ion|e|ing))\b'
    registration = r'\b(?:dang k[yi]|register|registration|enrol(?:l)?(?:ment)?)\b'
    credit_field = r'\b(?:credits?|tin(?: chi)?|tc)\b'
    # An admission/award GPA and a curriculum credit total cannot support
    # rules about graduation grades or grade-dependent course registration.
    # Require the requested relationship in a local source passage, rather
    # than separate keyword hits in unrelated chunks of the selected corpus.
    relationships = (
        ((grade, graduation), 'graduation_grade_rule_not_in_selected_sources'),
        ((grade, registration, credit_field), 'grade_registration_rule_not_in_selected_sources'),
    )
    for fields, reason in relationships:
        if all(re.search(field, question) for field in fields):
            if not any(
                all(re.search(field, passage[max(0, match.start()-160):match.end()+160])
                    for field in fields)
                for body in bodies
                for passage in re.split(r'[!?;]|\.(?!\d)', body)
                for match in re.finditer(fields[0], passage)
            ):
                return reason
    semester = re.search(r'\b(?:semester|hoc ky|ky|ki)\b', question)
    bound = re.search(r'\b(?:minimum|maximum|at least|at most|toi thieu|toi da|it nhat|nhieu nhat)\b', question)
    credits = re.search(r'\b(?:credits?|tin(?: chi)?|tc)\b', question)
    if semester and bound and credits:
        # A curriculum's "Credits per semester" totals do not establish a
        # registration floor or ceiling. Require explicit constraint wording
        # near both the semester and credit fields in a source paragraph.
        supported = False
        for body in bodies:
            for match in re.finditer(r'\b(?:minimum|maximum|at least|at most|toi thieu|toi da|it nhat|nhieu nhat)\b', body):
                window = body[max(0, match.start()-160):match.end()+160]
                if (re.search(r'\b(?:semester|hoc ky|ky|ki)\b', window)
                        and re.search(r'\b(?:credits?|tin chi)\b', window)):
                    supported = True
                    break
        if not supported:
            return 'semester_credit_constraint_not_in_selected_sources'
    return None
