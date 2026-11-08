"""Bounded coverage checks for explicit two-part and personal-record requests.

Only a named pair introduced by both/ca and an explicit no-partial requirement
is parsed. This is a conservative lexical coverage check, not semantic NLU.
The ordinary source/claim verifier must still prove every matching claim.
Explicit leading requests for private app internals can be refused separately
from a subsequent document question, without suppressing its grounding checks.
"""
import re
from .claims import normalize_text
from .course_credits import COURSE_CODE,course_code_key,folded

NO_PARTIAL=re.compile(r'\b(?:do not give a partial answer|no partial answer|'
    r'khong tra loi mot phan|chi dua dap an khi co bang chung cho ca hai thong tin|'
    r'neu thieu mot phan thi tu choi ket luan toan bo)\b')
PAIRS=(
    re.compile(r'\b(?:report|provide|give|state|tell me)\s+both\s+(.+?)\s+and\s+(.+?)(?:[.!?](?:\s|$)|$)',re.I),
    re.compile(r'\b(?:hay cho biet|cho biet|cung cap|neu)\s+(?:ca\s+)?(.+?)\s+va\s+(.+?)(?:[.!?](?:\s|$)|$)',re.I),
)
FUNCTION_WORDS={'the','a','an','of','your','our','their','its','my','value','number',
    'cua','ban','toi','chung','he','thong','so'}
CODE=re.compile(r'(?<!\w)'+COURSE_CODE+r'(?!\w)',re.I)


def document_request_without_internal_disclosure(question):
    """Separate an explicit leading disclosure command from a later question.

    None means no recognized command. An empty remainder means refuse without
    retrieval/generation. Preserve the exact remaining text, including names,
    numbers and source restrictions; never derive a question from source/gold.
    Educational mentions and quoted commands are not disclosure requests.
    """
    if not isinstance(question,str) or len(question)>2000:
        return None
    from .footnotes import _fold_with_offsets
    text,offsets=_fold_with_offsets(question)
    command=r'^\s*(?:(?:please|hay|vui long|ban)\s+)*(?:reveal|show|print|give(?:\s+me)?|disclose|dua|tiet lo|hien thi|cung cap|in)\b'
    command_match=re.search(command,text)
    if not command_match:
        return None
    boundary=re.search(r'[;!?]\s+|\s+(?:roi(?:\s+moi)?|sau do|then|and then|also|ngoai ra|dong thoi)\s+',text)
    prefix=text[:boundary.start()] if boundary else text
    target=prefix[command_match.end():].lstrip()
    if not re.match(r'(?:(?:the|your|current|our|me|toi|minh|cho toi|cho minh)\s+)*'
                    r'(?:(?:system|developer|hidden|internal)\s+prompt|prompt\s+(?:he thong|noi bo)|'
                    r'api[ _-]?key|khoa api|credential|secret key)\b',target):
        return None
    prompt=re.search(r'\b(?:(?:system|developer|hidden|internal)\s+prompt|prompt\s+(?:he thong|noi bo))\b',prefix)
    key=(re.search(r'\b(?:api[ _-]?key|khoa api|credential|secret key)\b',prefix)
         and re.search(r'\b(?:your|current|running|dang chay|dang dung|cua (?:app|ung dung|ban|he thong))\b',prefix))
    if not prompt and not key:
        return None
    return question[offsets[boundary.end()]:].strip() if boundary and boundary.end()<len(offsets) else ''


def refuse_internal_disclosure(answer=None, language='vi'):
    """Keep independently grounded content and explicitly refuse private internals."""
    from dataclasses import replace
    from .grounding import GroundedAnswer
    notice=('Mình không cung cấp khóa API hoặc chỉ dẫn nội bộ của ứng dụng.'
            if language.casefold().startswith('vi') else
            'I cannot provide application API keys or private internal instructions.')
    if answer is None:
        return GroundedAnswer(notice,(), 'low',True,
                              reason='no_retrieval_evidence',evidence_status='missing')
    return replace(answer,answer=notice+'\n\n'+answer.answer)


def asserts_document_absence(answer):
    """Recognize explicit source-absence assertions, not ordinary negated facts.

    A positive answer may hide an unverified absence statement outside its
    structured claims. Such a statement still needs the complete-source audit.
    Keep the subject/verb grammar bounded; a policy saying students do not pay
    a fee, or quoting the phrase inside a source discussion, is not this claim.
    """
    text=folded(answer)
    # Availability assertions can start a clause within a comparison, not
    # only a sentence. Use punctuation boundaries rather than enumerating
    # discourse phrases or source names; quoted discussions still do not
    # match a source subject immediately after this boundary.
    boundary=r'(?:^|[.!?;,:]\s*)'
    english=(r'(?:(?:the|this|these|those)\s+)?'
        r'(?:(?:uploaded|provided|supplied|selected|checked|retrieved|available)\s+)*'
        r'(?:documents?|sources?|pdfs?|texts?|materials?|context)\s+'
        r'(?:do(?:es)?\s+not|doesn[\x27\u2019]t|don[\x27\u2019]t)\s+'
        r'(?:contain|mention|specify|provide|include|state|show|cover|address|list|establish|confirm|describe)\b')
    vietnamese=(r'(?:(?:cac|nhung)\s+)?(?:tai lieu|nguon|tep pdf|pdf)'
        r'(?:\s+(?:(?:duoc|dang)\s+)?(?:tai len|cung cap|chon|kiem tra)|\s+hien co)?'
        r'(?:\s+nay)?\s+(?:khong|chua)\s+(?:he\s+)?'
        r'(?:de cap|co|chua thong tin|neu|cung cap|ghi|chi ro|bao gom|the hien|xac lap|cong bo|phan chia|liet ke|quy dinh)\b')
    if re.search(boundary+r'(?:'+english+'|'+vietnamese+r')',text):
        return True
    # The source can be the subject of a qualified clause: "the document only
    # lists historical scores and does not publish this year's cutoff". Keep
    # this bounded to a source subject and information-availability verbs.
    # A source's title, owner or year can qualify its subject before an
    # explicit information-absence assertion. Do not treat ordinary negative rules
    # or quoted discussions as assertions about information availability.
    qualified_subject = (r'(?:tai lieu|nguon|tep pdf|pdf)\s+(?P<subject>[^.!?;]{1,180}?)\s+'
        r'(?:khong|chua)\s+(?:he\s+)?(?:chua thong tin|cong bo|phan chia|de cap|cung cap|xac lap|quy dinh|neu|ghi ro)\b')
    subject_match=re.search(boundary+qualified_subject,text)
    if subject_match and not re.search(
            r'\b(?:quy dinh|ghi ro|cho biet|neu rang|trich dan|sinh vien|nguoi hoc)\b',
            subject_match['subject']):
        return True
    qualified = (r'(?:tai lieu|nguon|pdf)(?:\s+nay)?\s+'
        r'(?:chi\s+(?:cung cap|neu|co|liet ke)\s+(?:[^.!?]|(?<=\d)\.(?=\d)){1,380}?\b(?:va|nhung|chu)\s+'
        r'|la\s+[^.!?;]{1,380}?\bnen\s+)'
        r'(?:khong|chua)\s+(?:co|cong bo|xac lap|de cap|phan chia)\b')
    return bool(re.search(boundary+qualified,text))


def explicit_request_roles(question):
    """Return only the two user-specified roles of a recognized explicit pair."""
    current=question.partition('\nContext topic (untrusted user input): ')[0]
    current=folded(current)
    if not NO_PARTIAL.search(current):return ()
    for pattern in PAIRS:
        match=pattern.search(current)
        if match:return tuple(match.groups())
    return ()


def role_tokens(text):
    text=normalize_text(text)
    text=CODE.sub(lambda m:course_code_key(m[0]),text)
    return set(re.findall(r'\w+',folded(text)))-FUNCTION_WORDS


def roles_covered(roles,claim_texts):
    """Require a claim to retain each role's content words/codes before proof."""
    claims=[role_tokens(text) for text in claim_texts]
    return all(bool(tokens:=role_tokens(role)) and any(tokens<=claim for claim in claims) for role in roles)


def requested_credit_value_present(question, answer):
    """Require the requested credit count/percentage, not an empty heading.

    This checks completeness only; normal source alignment must still prove
    the number, unit and subject. Years and article numbers do not count.
    """
    current=folded(question.partition('\nContext topic (untrusted user input): ')[0])
    count=bool(re.search(r'\b(?:how many(?: [a-z-]+){0,4} credits|bao nhieu tin chi|'
                         r'so tin chi[^.!?;]{0,80}bao nhieu(?!\s*(?:phan tram|%)))\b',current))
    percentage=bool(re.search(r'\b(?:credits?|tin chi|tc)\b',current) and re.search(
        r'\b(?:what percentage|what percent|bao nhieu\s*(?:phan tram|%))',current))
    if not count and not percentage:
        return True
    text=folded(answer).strip()
    value=r'[0-9]{1,6}(?:[.,][0-9]{1,3})?'
    unit=r'(?:credits?|tin chi|tc)'
    bare=bool(re.fullmatch(value+r'[.!]?',text))
    has_count=bool(re.search(r'(?<![\w.])'+value+r'\s*'+unit+r'\b|\b'+unit+r'\s*[:=]\s*'+value+r'(?!\w)',text))
    has_percentage=bool(re.search(r'(?<![\w.])'+value+r'\s*(?:%|percent\b|phan tram\b)',text))
    return ((not count or has_count or bare and not percentage)
            and (not percentage or has_percentage or bare and not count))


def personal_event_requires_record(question, results):
    """A general regulation cannot establish an individual's realized event.

    This only rejects a proposed positive answer. It does not certify document
    absence, classify unknown sources, or reject ordinary personal eligibility
    questions about what a policy requires. No filenames or benchmark labels
    are used as proof of a source's scope.
    """
    current = folded(question.partition('\nContext topic (untrusted user input): ')[0])
    credential = bool(re.search(r'\b(?:mat khau|password|passcode|pin)\b',current)
                      and re.search(r'\b(?:my|cua (?:em|minh|toi|t)|ca nhan)\b',current)
                      and not re.search(r'\b(?:dat lai|khoi phuc|doi mat khau|reset|recover|change)\b',current))
    personal = re.search(r'\b(?:my|me|i|cua toi|ban than toi|ca nhan toi|lop toi|nhom toi)\b|'
                         r'(?:^|[.!?]\s+)toi\s+(?:duoc|co|bi)\b', current)
    event = re.search(r'\b(?:assigned|appointed|received|credited|recorded|approved|'
        r'enrolled|transferred|mailed|completed|outcome|serial number|tracking number|'
        r'actual|personally|verification|verified|da duoc|da nhan|da nop|da chuyen|duoc phan cong|'
        r'ket qua thuc te|thuc te|quyet dinh ca nhan|xac nhan|chap nhan dang)\b|'
        r'\bquyet dinh\b[^.!?]{0,80}\brieng\b', current)
    policy_question = re.search(r'\b(?:must|should|required|requirements|minimum|'
        r'eligible|eligibility|procedure|procedures|can i|may i|how do i|'
        r'can phai|can duoc|phai lam|dieu kien|thu tuc|yeu cau|tieu chuan|toi thieu|co duoc)\b', current)
    if (not credential and (not personal or not event or policy_question)) or not results:
        return False
    by_doc = {}
    for result in results:
        by_doc.setdefault(result.doc_id, []).append(result)
    def normative(items):
        return any(folded(str(item.metadata.get('document_type', ''))) in {
            'regulation', 'regulations', 'curriculum', 'course_catalog', 'syllabus',
        } or (item.page in {1, 2} and any(re.search(
            r'^\s*(?:quy che|quy dinh|academic regulations|academic rules|'
            r'(?:thong tin|chinh sach|de an) tuyen sinh|admissions? (?:information|policy|rules))\b',
            folded(line)) for line in item.content.splitlines())) for item in items)
    return all(normative(items) for items in by_doc.values())
