"""Resolve institution references from source headers, not a school/answer list."""
import re
import unicodedata
from dataclasses import dataclass, replace


def folded(text):
    text = unicodedata.normalize('NFD', text.casefold()).replace('đ', 'd')
    return re.sub(r'[^a-z0-9]+', ' ', ''.join(c for c in text if not unicodedata.combining(c))).strip()


_GENERIC = set('truong dai hoc dh vien hocvien university college institute national of and the em toi minh ban o tai cua co la thi duoc khong nam ky ki diem tin chi at in is to for an it tu va voi nay nao sao can quy che ap dung'.split())
_ACADEMIC = {'gpa','cpa','tc','ects','pdf','cntt','ielts','toefl'}
_CONTEXT = '\nContext topic (untrusted user input): '


def _institution_groups(documents):
    """Group repeated files, without merging different schools under a parent."""
    profiles={d['doc_id']:institution_headers(d.get('items',[])) for d in documents}
    keys={}
    for ident,names in profiles.items():
        compact={name.replace(' ','') for name in names}
        primary={name for name in compact if name.startswith('truong')}
        primary=primary or {name for name in compact if re.match(r'^(?:daihoc|dh|hocvien)',name)} or compact
        keys[ident]={re.sub(r'^(?:truong)?(?:daihoc|dh)','daihoc',name) for name in primary}
    parents={ident:ident for ident in profiles}
    def root(ident):
        while parents[ident]!=ident:ident=parents[ident]
        return ident
    for i,ident in enumerate(profiles):
        for other in list(profiles)[:i]:
            if keys[ident]&keys[other]:parents[root(ident)]=root(other)
    return profiles,{ident:root(ident) for ident in profiles}


def institution_headers(items):
    names = set()
    for item in items:
        metadata = item.get('metadata') or {}
        values = [str(metadata.get('institution', ''))]
        if item.get('page', 999) <= 5:
            from .tokenizer_vi import source_body
            values.extend(source_body(item).splitlines())
        for line in values:
            value = folded(line)
            value = re.split(r'\b(?:ban hanh|tu hao|la truong|theo nghi quyet|quy dinh)\b', value, maxsplit=1)[0].strip()
            value = re.sub(r'\s+\d+$', '', value)
            compact = value.replace(' ', '')
            if (re.match(r'^(?:truong)?(?:daihoc|dh|hocvien)', compact)
                    or re.search(r'\b(?:university|college|institute)\b', value)):
                if 8 <= len(compact) <= 150:
                    names.add(value)
    return names


def _references(raw, documents):
    words = folded(raw).split()
    pairs = {a+b for a,b in zip(words,words[1:]) if not (a in _GENERIC and b in _GENERIC)
             and a.isalpha() and b.isalpha() and len(a+b) >= 5}
    query_words = {w for w in words if w not in _GENERIC|_ACADEMIC and len(w) >= 2}
    matches = {}
    for doc in documents:
        names = institution_headers(doc.get('items', []))
        compact_names = [name.replace(' ', '') for name in names]
        aliases = set()
        for name in names:
            terms = [w for w in name.split() if w not in {'of','and','the'}]
            aliases.add(''.join(w[0] for w in terms))
            # Short references can name a distinctive contiguous part of a
            # header. Ambiguous acronyms retain every matching source.
            for n in range(2, min(6,len(terms))+1):
                aliases.update(''.join(w[0] for w in terms[i:i+n]) for i in range(len(terms)-n+1))
        for reference in {pair for pair in pairs if any(pair in name for name in compact_names)} | (query_words & aliases):
            matches.setdefault(reference, set()).add(doc['doc_id'])
    return matches


def _unmatched_name(raw, documents):
    # A new named school must not silently inherit the previous school.
    for part in re.split(r'\b(?:va|voi|and|versus|vs)\b|[,;]',folded(raw)):
        # Quantified common nouns ("all schools require ...") are not names.
        # Remove only that noun phrase; a separately named unknown school
        # in the same comparison must still trigger confirmation.
        part = re.sub(r'\b(?:tat ca(?: cac)?|cac|moi|hai|ba|\d+)\s+truong\b', ' ', part)
        named=re.search(r'\b(?:truong(?: dai hoc)?|dai hoc|dh|university|college|institute)\s+(\w+)',part)
        if (named and named[1] not in _GENERIC|{'do','khac','chinh','dao','vua','tu','thac','tien'}
                and not _references(part,documents)):
            return True
    acronyms=set(re.findall(r'\b[A-Z]{2,12}\b',raw))
    unknown={a for a in acronyms if a.casefold() not in _ACADEMIC and not _references(a,documents)}
    return bool(unknown and _institution_dependent(raw,documents) and (raw.strip() in unknown or re.match(
        r'^(?:con|the|vay|o|tai|what about|at)\b',folded(raw))))


def requested_institution_documents(question, documents):
    # A shared city name cannot override a specific school. Multiple files
    # of one school count as one institution, not an ambiguous abbreviation.
    raw = question.split(_CONTEXT, 1)[0]
    matches=_references(raw,documents)
    _,groups=_institution_groups(documents)
    unique = set().union(*(ids for ids in matches.values() if len({groups[i] for i in ids}) == 1)) if matches else set()
    matched = unique or (set().union(*matches.values()) if matches else set())
    if not matched and _CONTEXT in question and not _unmatched_name(raw,documents):
        return requested_institution_documents(question.split(_CONTEXT,1)[1],documents)
    return matched


def needs_institution_clarification(question, documents, *, strict=True):
    if strict:return resolve_institution_request(question,documents).needs_clarification
    value=folded(question.split('\nContext topic (untrusted user input): ',1)[0])
    if not re.search(r'\b(?:truong (?:cua )?(?:em|minh|toi|t)|my (?:university|college|school))\b',value):
        return False
    known=[institution_headers(d.get('items',[])) for d in documents]
    known=[names for names in known if names]
    return len(known)>1 and not set.intersection(*known)


@dataclass(frozen=True)
class InstitutionRequest:
    question: str
    doc_ids: frozenset[str]=frozenset()
    needs_clarification: bool=False
    unknown_name: bool=False
    source_options: tuple[str, ...]=()
    unrecognized_reference: str=''
    alias_check_unavailable: bool=False
    question_clarification: bool=False

    def clarification(self,language='vi'):
        if self.question_clarification:
            message=('Mình đã nhận lựa chọn trường. Bạn muốn hỏi riêng nội dung nào, hay so sánh với trường nào?'
                if language=='vi' else 'I have the institution choice. Which topic do you want, or which institution should I compare it with?')
        elif self.unknown_name:
            reference=f' “{self.unrecognized_reference[:80]}”' if self.unrecognized_reference else ''
            message=(f'Mình chưa khớp được tên/viết tắt{reference} với trường trong các PDF đang chọn. '
                'Bạn xác minh tên trường đầy đủ hoặc chọn đúng PDF giúp mình. Mình sẽ tiếp tục câu hỏi trước sau khi bạn xác nhận.'
                if language=='vi' else f'I cannot match the institution name/abbreviation{reference} to the selected PDFs. '
                'Please confirm its full name or select its PDF; I will then continue your previous question.')
            if self.alias_check_unavailable:
                message=('Lượt đối chiếu tên/viết tắt qua dịch vụ AI chưa thực hiện được lúc này. '
                    if language=='vi' else 'The AI abbreviation check is currently unavailable. ')+message
        else:
            message=('Bạn muốn hỏi trường nào? Các PDF đang chọn có thể thuộc nhiều trường. Hãy nêu tên trường hoặc chọn đúng PDF.'
                if language=='vi' else 'Which institution do you mean? Please give its name or select its PDF.')
        if self.source_options:
            message+=('\nCác nguồn đang chọn:\n' if language=='vi' else '\nSelected sources:\n')
            message+='\n'.join('- '+option for option in self.source_options)
        return message


def _source_options(documents):
    """Show actual source labels, rather than suggesting unsupported aliases."""
    profiles,groups=_institution_groups(documents)
    options=[];seen=set()
    for doc in documents:
        group=groups[doc['doc_id']]
        if group in seen:continue
        seen.add(group)
        label='';source=''
        for item in doc.get('items',[]):
            metadata=item.get('metadata') or {}
            source=source or str(metadata.get('source_name') or '')
            candidates=[str(metadata.get('institution') or '')]
            if item.get('page',999)<=5:
                from .tokenizer_vi import source_body
                candidates.extend(source_body(item).splitlines())
            label=next((value.strip() for value in candidates
                        if folded(value) in profiles[doc['doc_id']]),'')
            if label:break
        option=label[:160] or source[:160]
        if option:options.append(option)
        if len(options)>=6:break
    return tuple(options)


def institution_alias_candidates(documents):
    """Candidate names come from authorized sources; IDs are local to this list."""
    profiles,groups=_institution_groups(documents)
    candidates=[]
    for group in sorted(set(groups.values())):
        members=[doc for doc in documents if groups[doc['doc_id']]==group]
        names=set().union(*(profiles[doc['doc_id']] for doc in members))
        if not names:continue
        labels=_source_options(members)
        if not labels:continue
        candidates.append({'candidate_id':f'c{len(candidates)}','name':labels[0],
            'names':sorted({labels[0],*names})[:6],
            'doc_ids':tuple(sorted(doc['doc_id'] for doc in members))})
    return candidates


def _multi_source_request(raw):
    value=folded(raw)
    return bool(re.search(r'\b(?:cac truong|moi truong|hai truong|ba truong|(?:tat ca(?: cac)?|ca (?:hai|ba|\d+)) (?:truong|tai lieu|nguon|pdf)|all (?:schools|institutions|sources|documents)|both (?:schools|institutions|sources|documents))\b',value)
        or re.search(r'\b(?:tom tat|tong hop|summari[sz]e|overview)\b',value)
        and re.search(r'\b(?:tai lieu|nguon|pdf|documents|sources)\b',value))


def _institution_dependent(question,documents):
    """Affiliation in a book/paper is not an instruction to ask for a school.

    Require an institutional rule question and source evidence of academic
    administration. Other PDF subjects retain ordinary content retrieval.
    """
    value=folded(question)
    if re.search(r'\b(?:truong (?:cua )?(?:em|minh|toi|t)|my (?:school|university|college))\b',value):return True
    administrative=False
    for doc in documents:
        for item in doc.get('items',[]):
            kind=folded(str(item.get('metadata',{}).get('document_type','')))
            if kind in {'regulation','admission','curriculum','handbook','academic calendar'}:
                administrative=True;break
            if item.get('page',999)<=5:
                from .tokenizer_vi import source_body
                if re.search(r'\b(?:quy che dao tao|quy dinh tuyen sinh|student handbook|academic regulations|academic calendar)\b',folded(source_body(item))):
                    administrative=True;break
        if administrative:break
    return administrative and bool(re.search(
        r'\b(?:quy che|quy dinh|tin chi|tc|gpa|cpa|hoc phi|le phi|hoc bong|tot nghiep|khoa luan|'
        r'phuc khao|phuc tra|hoan thi|thi lai|thi cuoi|ky thi|hoc ky|hoc ki|ky chinh|ky he|'
        r'dang k[yi]|hoc lai|hoc cai thien|hoc truoc|tien quyet|canh bao|tuyen sinh|nhap hoc|'
        r'diem chu|quy doi diem|thoi gian hoc|tuan hoc|'
        r'rules?|regulations?|polic(?:y|ies)|credits?|tuition|scholarship|graduation|admission|register|registration|prerequisite|exam|semester)\b|'
        r'\b(?:\d+(?:[.,]\d+)?|may|bao nhieu)\s+(?:tin|diem)\b|\bdiem\s+[a-f][+-]?(?!\w)',value)
        or re.search(r'\bthi\b',question,re.I))


def _scope_decision(question,documents):
    raw,separator,topic=question.partition(_CONTEXT)
    profiles,groups=_institution_groups(documents)
    refs=_references(raw,documents)
    if _unmatched_name(raw,documents) and any(profiles.values()):
        return InstitutionRequest(question,needs_clarification=True,unknown_name=True)
    if not refs and separator:
        inherited=_scope_decision(topic,documents)
        if inherited.doc_ids or inherited.unknown_name:
            return InstitutionRequest(question,inherited.doc_ids,inherited.needs_clarification,inherited.unknown_name)
    matched=requested_institution_documents(raw,documents)
    all_sources=_multi_source_request(raw)
    if matched:
        chosen_groups={groups[i] for i in matched}
        precise={groups[next(iter(ids))] for ids in refs.values() if len({groups[i] for i in ids})==1}
        unresolved=any(len({groups[i] for i in ids})>1 and not {groups[i] for i in ids}&precise for ids in refs.values())
        listed=bool(re.search(r'\b(?:va|voi|and|vs|versus|so sanh|compare|khac nhau|giong nhau)\b|[,;]',folded(raw)))
        ambiguous=(unresolved or len(chosen_groups)>1 and not (len(precise)>1 and listed)) and not all_sources
        return InstitutionRequest(question,frozenset(matched),ambiguous)
    # No identified institution in ordinary textbooks is not evidence that
    # they come from different schools. Unknown files remain separate when
    # other selected PDFs do establish institution-specific scopes.
    ambiguous=bool(any(profiles.values()) and len(set(groups.values()))>1 and not all_sources
                   and _institution_dependent(raw,documents))
    return InstitutionRequest(question,needs_clarification=ambiguous)


def _school_clarification(text):
    return bool(re.search(r'\b(?:truong nao|xac minh ten truong|which institution|confirm its name)\b',folded(text)))


def _reference_only(raw,documents):
    refs=_references(raw,documents)
    if not refs:return False
    words=folded(raw).split();covered=set()
    for i,word in enumerate(words):
        if word in refs:covered.add(i)
        if i+1<len(words) and word+words[i+1] in refs:covered.update((i,i+1))
    extras={word for i,word in enumerate(words) if i not in covered}-_GENERIC-set('hoi ve dung roi nhe a ah yes please do con the vay'.split())
    return not extras


def _unrecognized_choice(raw):
    words=re.findall(r'[^\W\d_]+',raw)
    if not words or len(words)>5:return False
    if re.fullmatch(r'[\w.-]{2,32}',raw.strip()):
        return folded(raw) not in _GENERIC|_ACADEMIC
    return all(word[0].isupper() for word in words)


def unresolved_institution_reference(question,documents):
    """Find a name-like token in a rule question, without a school whitelist."""
    raw,separator,topic=question.partition(_CONTEXT)
    contextual=bool(separator and _institution_dependent(topic,documents))
    if not (_institution_dependent(raw,documents) or contextual):return ''
    words=list(re.finditer(r'[^\W_]+',raw))
    refs=_references(raw,documents)
    covered=set()
    for index,word in enumerate(words):
        if folded(word.group()) in refs:covered.add(index)
        if index+1<len(words) and folded(word.group())+folded(words[index+1].group()) in refs:
            covered.update((index,index+1))
    for index,word in enumerate(words):
        if index in covered:continue
        token=word.group();value=folded(token)
        if (not re.fullmatch(r'[A-Za-z]{3,12}',token) or value in _GENERIC|_ACADEMIC
                or _references(token,documents)):
            continue
        previous=folded(words[index-1].group()) if index else ''
        following=folded(words[index+1].group()) if index+1<len(words) else ''
        named=(previous in {'cua','tai','o','truong','ben','about','at','of','for'}
               and following in {'','la','co','thi','nhu','quy','yeu','hoc','can','duoc','ap','rules','policy'})
        named=named or contextual and previous in {'con','the','vay'} and following in {'','thi','sao'}
        if named or token.isupper() and value not in {'sv','student','students','pdf'}:
            return token
    return ''


def replace_institution_alias(question,reference,canonical):
    return re.sub(r'(?<!\w)'+re.escape(reference)+r'(?!\w)',lambda _m:canonical,question,flags=re.I)


def _retarget_question(pending,documents,name):
    """Keep the requested rule/attribute, replacing its old institution only."""
    raw,separator,topic=pending.partition(_CONTEXT)
    suffix=separator+_retarget_question(topic,documents,name) if separator else ''
    refs=_references(raw,documents)
    words=list(re.finditer(r'[^\W_]+',raw))
    spans=[]
    for index,word in enumerate(words):
        if folded(word.group()) in refs:spans.append(word.span())
        if index+1<len(words) and folded(word.group())+folded(words[index+1].group()) in refs:
            spans.append((word.start(),words[index+1].end()))
    if spans:
        # Keep separate mentions separate; do not erase conditions between them.
        merged=[]
        for start,end in sorted(spans):
            if merged and (start<=merged[-1][1] or not raw[merged[-1][1]:start].strip()):
                merged[-1]=(merged[-1][0],max(end,merged[-1][1]))
            else:merged.append((start,end))
        start,end=max(merged,key=lambda span:span[1]-span[0])
        prefix=[word for word in words if word.end()<=start]
        initial=[word for word in words if start<=word.start()<end][:2]
        institution_prefixes={'truong','dai hoc','truong dai hoc','dh','truong dh','hoc vien','hocvien',
                              'university','university of','the university of','college','college of','institute','institute of'}
        for offset in range(max(0,len(prefix)-4),len(prefix)):
            phrases=[' '.join(folded(word.group()) for word in prefix[offset:]+initial[:count])
                     for count in range(len(initial)+1)]
            if any(phrase in institution_prefixes for phrase in phrases):
                start=prefix[offset].start();break
        return raw[:start]+name+raw[end:]+suffix
    unknown=unresolved_institution_reference(raw,documents)
    if unknown:return replace_institution_alias(raw,unknown,name)+suffix
    return raw+suffix


def _pending_question(turns,documents):
    for index in range(len(turns)-1,-1,-1):
        role,text=turns[index]
        if role!='user':continue
        raw=text.partition(_CONTEXT)[0]
        if _reference_only(raw,documents):continue
        if (index and turns[index-1][0]=='assistant'
                and _school_clarification(turns[index-1][1]) and _unrecognized_choice(raw)):
            continue
        return text
    return None


def _resolve_institution_request(question,documents,history=()):
    """Resolve source intent from user input; never use a model answer as fact."""
    turns=[(turn['role'],turn['content']) if isinstance(turn,dict) else turn for turn in history]
    raw=question.partition(_CONTEXT)[0]
    if not _references(raw,documents) and re.search(r'\b(?:truong khac|doi truong|chuyen truong|other (?:school|institution|university))\b',folded(raw)):
        return InstitutionRequest(question,needs_clarification=True)
    if turns:
        if _reference_only(raw,documents):
            # A school-only reply is a source choice, not a new subject.
            # Skip earlier choices too, so successive school switches retain
            # the user's substantive question rather than the last acronym.
            pending=_pending_question(turns,documents)
            confirmed=_scope_decision(raw,documents)
            if pending and confirmed.doc_ids and not confirmed.needs_clarification:
                # Keep a complete pending question as the main request so
                # ordinary content/structured retrieval still sees its intent.
                previous_ids=requested_institution_documents(pending,documents)
                _,groups=_institution_groups(documents)
                if (len({groups[ident] for ident in previous_ids})>1
                        and re.search(r'\b(?:so sanh|compare|comparison|khac nhau)\b',folded(pending))):
                    return InstitutionRequest(question,confirmed.doc_ids,needs_clarification=True,
                        question_clarification=True)
                selected=[doc for doc in documents if doc['doc_id'] in confirmed.doc_ids]
                labels=_source_options(selected)
                effective=_retarget_question(pending,documents,labels[0]) if labels else pending
                return InstitutionRequest(effective,confirmed.doc_ids)
            if pending:question=raw+_CONTEXT+pending
        elif turns[-1][0]=='assistant' and _school_clarification(turns[-1][1]):
            if _unrecognized_choice(raw) or _unmatched_name(raw,documents):
                return InstitutionRequest(question,needs_clarification=True,unknown_name=True,
                    unrecognized_reference=raw)
    decision=_scope_decision(question,documents)
    if decision.doc_ids or decision.unknown_name or _multi_source_request(raw):return decision
    if re.search(r'\b(?:truong khac|doi truong|chuyen truong|other (?:school|institution|university))\b',folded(raw)):
        return InstitutionRequest(question,needs_clarification=True)
    if not _institution_dependent(question,documents):return decision
    # An explicit user school remains usable for a new subject in the same
    # bounded conversation. A clarification or comparison is a scope boundary.
    for role,text in reversed(turns):
        if role=='assistant' and _school_clarification(text):break
        if role!='user':continue
        previous=_scope_decision(text,documents)
        if previous.unknown_name:break
        if previous.doc_ids:
            _,groups=_institution_groups(documents)
            if not previous.needs_clarification and len({groups[i] for i in previous.doc_ids})==1:
                return InstitutionRequest(question,previous.doc_ids)
            break
    return decision


def resolve_institution_request(question,documents,history=()):
    request=_resolve_institution_request(question,documents,history)
    if not request.unrecognized_reference:
        reference=unresolved_institution_reference(question,documents)
        if reference:
            request=replace(request,doc_ids=frozenset(),needs_clarification=True,
                unknown_name=True,unrecognized_reference=reference)
    if request.doc_ids and not request.needs_clarification:
        _,groups=_institution_groups(documents)
        if len({groups[ident] for ident in request.doc_ids})==1:
            labels=_source_options([doc for doc in documents if doc['doc_id'] in request.doc_ids])
            if labels:request=replace(request,question=_retarget_question(request.question,documents,labels[0]),source_options=labels)
    if request.needs_clarification:
        request=replace(request,source_options=_source_options(documents))
    return request
