"""Resolve institution references from source headers, not a school/answer list."""
import re
import unicodedata


def folded(text):
    text = unicodedata.normalize('NFD', text.casefold()).replace('đ', 'd')
    return re.sub(r'[^a-z0-9]+', ' ', ''.join(c for c in text if not unicodedata.combining(c))).strip()


_GENERIC = set('truong dai hoc dh vien hocvien university college institute national of and the em toi minh ban o tai cua co la thi duoc khong nam ky ki diem tin chi at in is to for an it tu va voi nay nao sao can quy che ap dung'.split())


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


def requested_institution_documents(question, documents):
    # The current request may replace the previous school in a follow-up.
    raw = question.split('\nContext topic (untrusted user input): ', 1)[0]
    words = folded(raw).split()
    pairs = {a+b for a,b in zip(words,words[1:]) if not (a in _GENERIC and b in _GENERIC)
             and a.isalpha() and b.isalpha() and len(a+b) >= 5}
    query_words = {w for w in words if w not in _GENERIC and len(w) >= 2}
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
    # A shared city name cannot override a more specific institution name.
    # Comparisons retain every independently identified institution.
    unique = set().union(*(ids for ids in matches.values() if len(ids) == 1)) if matches else set()
    matched = unique or (set().union(*matches.values()) if matches else set())
    if not matched and '\nContext topic (untrusted user input): ' in question:
        # A subject-less follow-up inherits its user's topic; a newly named
        # institution must not silently inherit the previous institution.
        explicit_new = (re.search(r'\b(?:dai hoc|truong|university|college|institute)\b',folded(raw))
                        or re.search(r'\b[A-Z]{2,12}\b',raw))
        if not explicit_new:
            return requested_institution_documents(question.split('\nContext topic (untrusted user input): ',1)[1],documents)
    return matched


def needs_institution_clarification(question, documents):
    value=folded(question.split('\nContext topic (untrusted user input): ',1)[0])
    if not re.search(r'\b(?:truong (?:cua )?(?:em|minh|toi|t)|my (?:university|college|school))\b',value):
        return False
    known=[institution_headers(d.get('items',[])) for d in documents]
    known=[names for names in known if names]
    return len(known)>1 and not set.intersection(*known)
