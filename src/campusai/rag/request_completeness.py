"""Bounded coverage checks for explicit two-part and personal-record requests.

Only a named pair introduced by both/ca and an explicit no-partial requirement
is parsed. This is a conservative lexical coverage check, not semantic NLU.
The ordinary source/claim verifier must still prove every matching claim.
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
    """A credit-count request needs a value, not a repeated empty source heading.

    This checks completeness only; normal source alignment must still prove
    the number, unit and subject. Years and article numbers do not count.
    """
    current=folded(question.partition('\nContext topic (untrusted user input): ')[0])
    if not re.search(r'\b(?:how many(?: [a-z-]+){0,4} credits|bao nhieu tin chi|so tin chi.{0,80}bao nhieu)\b',current):
        return True
    text=folded(answer).strip()
    value=r'[0-9]{1,6}(?:[.,][0-9]{1,3})?'
    unit=r'(?:credits?|tin chi)'
    return bool(re.fullmatch(value+r'[.!]?',text) or re.search(
        r'(?<![\w.])'+value+r'\s+'+unit+r'\b|\b'+unit+r'\s*[:=]\s*'+value+r'(?!\w)',text))


def personal_event_requires_record(question, results):
    """A general regulation cannot establish an individual's realized event.

    This only rejects a proposed positive answer. It does not certify document
    absence, classify unknown sources, or reject ordinary personal eligibility
    questions about what a policy requires. No filenames or benchmark labels
    are used as proof of a source's scope.
    """
    current = folded(question.partition('\nContext topic (untrusted user input): ')[0])
    personal = re.search(r'\b(?:my|me|i|cua toi|ban than toi)\b', current)
    event = re.search(r'\b(?:assigned|appointed|received|credited|recorded|approved|'
        r'enrolled|transferred|mailed|completed|outcome|serial number|tracking number|'
        r'actual|personally|da duoc|da nhan|da nop|da chuyen|duoc phan cong|'
        r'ket qua thuc te|quyet dinh ca nhan)\b', current)
    policy_question = re.search(r'\b(?:must|should|required|requirements|minimum|'
        r'eligible|eligibility|procedure|procedures|can i|may i|how do i|'
        r'can phai|phai lam|dieu kien|thu tuc|toi thieu|co duoc)\b', current)
    if not personal or not event or policy_question or not results:
        return False
    by_doc = {}
    for result in results:
        by_doc.setdefault(result.doc_id, []).append(result)
    def normative(items):
        return any(folded(str(item.metadata.get('document_type', ''))) in {
            'regulation', 'regulations', 'curriculum', 'course_catalog', 'syllabus',
        } or (item.page in {1, 2} and re.search(
            r'(?:^|\n)\s*(?:quy che|quy dinh|academic regulations|academic rules)\b',
            folded(item.content))) for item in items)
    return all(normative(items) for items in by_doc.values())
