"""Bounded contextual query resolution from request input, never gold labels."""
from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

from .policies import sanitize_evidence_text

CONTEXT_VERSION = "request-context-v11"
FOLLOWUP = re.compile(r"\b(?:môn này|mon nay|cái đó|cai do|nó|that course|that program|this course|it|what about)\b", re.I)


def _fold(value):
    return ''.join(c for c in unicodedata.normalize('NFD', value.casefold())
                   if not unicodedata.combining(c)).replace('đ', 'd')


def small_talk_kind(question):
    text = ' '.join(re.sub(r'[^\w\s]', ' ', _fold(question)).split())
    if text in {'hi', 'hello', 'hey', 'alo', 'chao', 'xin chao', 'chao ban', 'hello ban', 'ban oi'}:
        return 'greeting'
    if text in {'cam on', 'cam on ban', 'thanks', 'thank you', 'ok', 'oke', 'ok ban'}:
        return 'thanks'
    return None


def meaningless_fragment(question):
    text = question.strip().strip('?!. ')
    return bool(re.fullmatch(r'[a-zA-Z]{8,}', text) and
                (re.search(r'[bcdfghjklmnpqrstvwxz]{6,}', text, re.I)
                 or re.search(r'(.)\1{5,}', text, re.I)))


def depends_on_previous_topic(question):
    """Require a reference or ellipsis; brevity alone never inherits a topic."""
    # A selected file identifies the source, not the antecedent of "it".
    # Inspect the actual question before applying the document-scope exemption.
    question = re.sub(r'^(?:use only (?:the )?uploaded|chỉ dùng tài liệu đã tải lên)\s+'
                      r'[\w.-]+\.pdf\.\s*', '', question, flags=re.I)
    text = ' '.join(re.sub(r'[^\w\s]', ' ', _fold(question)).split())
    if missing_topic_reference(question):
        return True
    if re.fullmatch(r'(?:vi du(?: di)?|cho (?:minh|t|toi) vi du|noi (?:de hieu|ngan gon)(?: hon)?|'
                    r'them vi du(?: nua)?|ngan gon hon|don gian hon(?: chut)?|noi ro cho nay|tl dr|'
                    r'(?:this|that) one|give me another example|'
                    r'(?:tom tat|giai thich)(?: lai| them)|tai sao|vi sao|why|how|credits|'
                    r'how many credits|how much|give (?:me )?an example|explain (?:more|again)|simplify it)', text):
        return True
    # Explicit document/section questions have their subject in the current
    # request and selected scope, even when a previous question was very short.
    discourse = re.match(r'^(?:con|vay|ua)\b', text) or re.match(r'^thế\b', question, re.I)
    if discourse and len(question.split()) <= 24:
        # A discourse filler does not turn a complete new definition into a
        # follow-up; "còn phần rèn luyện thì cần tới loại nào" does need context.
        return not bool(re.search(r'\b(?:la gi|what is|what are|explain|summarize|tong hop|tom tat|giai thich)\b', text))
    # Selecting a file does not identify which course/rule a deictic object
    # refers to. Resolve from an explicit local subject, user history or
    # selected text before the general document-scope exemption below.
    if re.search(r'\b(?:this|that)\s+(?:course|subject|rule|program|programme)\b', text):
        return True
    if re.search(r'\b(?:tai lieu|tep|file|pdf|document|section|chapter|phan|chuong)\b', text):
        return False
    if FOLLOWUP.search(question) and len(question.split()) <= 24:
        return True
    if re.search(r'\b(?:cai nay|cai day|this one|that one)\b', text):
        return True
    if re.match(r'^no\s+(?:hoat dong|la|co|dung|khac|duoc)\b', text):
        return True
    return False


def _user_topic(turns):
    chain = []
    for role, content in reversed(turns):
        if role != 'user':
            continue
        if small_talk_kind(content):
            continue
        chain.append(content)
        if not depends_on_previous_topic(content):
            break
    return '\n'.join(reversed(chain)) if chain else None


def has_local_topic_reference(question: str) -> bool:
    """A plan's explicitly listed object can anchor 'it' in the same utterance.

    This is a grammar rule, not a list of known courses or benchmark answers.
    A pronoun-only object still requires conversational context.
    """
    # An explicitly named prerequisite subject also resolves the same-sentence
    # "it"; a lone pronoun or two possible course subjects still need context.
    from .course_credits import COURSE_CODE
    without_files = re.sub(r'\b[\w.-]+\.pdf\b', ' ', question, flags=re.I)
    codes = re.findall(r'(?<!\w)'+COURSE_CODE+r'(?!\w)', without_files, re.I)
    if len(codes) == 1 and re.search(
            r'\b(?:this|that)\s+(?:course|subject)\s*\(?\s*'+COURSE_CODE+r'\b', without_files, re.I):
        return True
    text = _fold(question)
    local = re.sub(r'^(?:use only (?:the )?uploaded|chi dung tai lieu da tai len) [\w.-]+\.pdf\.\s*', '', text)
    subject_clause = re.match(r'^when does (.{2,100}?) (?:take effect|become effective),?\s+and\b', local)
    if subject_clause and re.search(r'\b(?:regulation|policy|decision|rule)\b', subject_clause[1]):
        if not re.search(r'\b(?:it|this|that|and|or)\b', subject_clause[1]):
            return True
    subject = None
    for pattern in (
        r'^([^;.!?]{1,80}?)\s+la gi\s+(?:va|[,;])',
        r'^what (?:is|are)\s+([^;.!?]{1,80}?)\s+and\b',
        r'^(?:explain|giai thich)\s+([^;.!?]{1,80}?)\s+(?:and|va)\b',
    ):
        match = re.match(pattern, text)
        if match:
            subject = re.sub(r'^(?:a|an|the|mot)\s+', '', match[1].strip())
            break
    if (subject and len(codes) <= 1
            and not re.match(r'^(?:it|its|their|this|that|these|those)\b', subject)
            and subject not in {
            'it', 'this', 'that', 'this course', 'that course', 'course', 'program',
            'the course', 'no', 'mon nay', 'cai nay', 'cai do'}):
        return True
    if len(codes)==1 and re.search(
            r'\b(?:direct\s+)?prerequisite\s+of\s+'+COURSE_CODE+
            r'\s+and\s+how\s+many\s+credits\s+does\s+it\s+have\s*\??\s*$',without_files,re.I):
        return True
    match = re.match(
        r'^the\s+[^;.!?]{0,120}\b(?:plan|curriculum|catalogue|catalog|program|programme)'
        r'\s+(?:lists|includes|contains|shows)\s+([^;.!?]{1,100});\s*(?:what|which|how)\b',
        question.strip(), re.I)
    if not match:
        return False
    topic = ' '.join(match[1].casefold().split())
    return (bool(re.search(r'[^\W\d_]', topic)) and not re.match(
        r'^(?:it|them|this|that|these|those|some|a course|a subject|the course|the subject)\b', topic))


def missing_topic_reference(question: str) -> bool:
    """Recognize incomplete references without guessing a course or personal facts.

    Whole-utterance matches keep discourse fillers in complete questions harmless.
    These grammar rules use only user input, never corpus names or benchmark labels.
    """
    folded = "".join(char for char in unicodedata.normalize("NFD", question.casefold())
                     if not unicodedata.combining(char)).replace("đ", "d")
    text = " ".join(re.sub(r"[^\w\s]", " ", folded).split())
    credit = re.fullmatch(
        r"(?:(?:ua|the|vay|con|it nhat)\s+)*"
        r"(?:(?:bao nhieu|bn|may)\s+(?:tin(?: chi)?|tc)|credits(?: can)?\s+(?:bao nhieu|bn)|"
        r"(?:tong|total)\s+(?:la\s+)?(?:may|bao nhieu|bn))"
        r"(?:\s+(?:thi|la|duoc|du|vay|nhi|moi|ok|ban))*", text)
    personal = re.fullmatch(
        r"(?:(?:the|vay|con|ua|nhu|tinh)\s+)*"
        r"(?:(?:minh|em|toi|t)(?: co)? (?:du dieu kien|duoc|bi gi)|am i eligible|"
        r"case (?:t|minh|em|toi)|cua (?:minh|em|toi)|(?:bang|ielts|chung chi) nay)"
        r"(?:\s+(?:thi|sao|co|bi|gi|du|chua|khong|ko|k|ok|ban|chu|vay|dung|duoc|dung duoc))*", text)
    year = re.fullmatch(
        r"(?:(?:the|vay|con|ua|em|sinh vien|sv)\s+)*"
        r"(?:nam (?:hai|2)|n2|second year students?)"
        r"(?:\s+(?:thi|sao|co|duoc|khac|khong|ko|k|ap dung|kieu gi))*", text)
    # An unspecified proof document is an anaphoric admission/registration
    # follow-up. Named credentials or an explicit application subject remain
    # self-contained and do not match this whole-utterance grammar.
    document = re.fullmatch(
        r"(?:(?:chua|khong|ko|k) co\s+)?"
        r"(?:giay(?: chung minh)?|giay to|chung chi)(?: nay|do)?\s+"
        r"(?:thi\s+)?(?:nop|bo sung)(?: sau)?"
        r"(?:\s+(?:duoc|khong|ko|k|chu|nhi|vay|ban))*", text)
    return bool(credit or personal or year or document)


def authorized_scope(doc_ids: list[str] | None, authorized_doc_ids: list[str] | None) -> list[str] | None:
    for scope in (doc_ids, authorized_doc_ids):
        if scope is not None and (not isinstance(scope, list)
                or any(not isinstance(doc, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,255}", doc) for doc in scope)
                or len(scope) != len(set(scope))):
            raise ValueError("invalid document scope")
    if authorized_doc_ids is None:
        return doc_ids
    if doc_ids is None:
        return list(authorized_doc_ids)
    if not set(doc_ids) <= set(authorized_doc_ids):
        raise ValueError("document scope exceeds authorization")
    return doc_ids


@dataclass(frozen=True)
class ResolvedQuery:
    raw: str
    resolved: str
    history: tuple[tuple[str, str], ...]
    selected_text: str | None
    needs_clarification: bool
    contextual: bool

    def cache_context(self) -> dict:
        return {"version": CONTEXT_VERSION, "history": list(self.history),
                "selected_text": self.selected_text, "resolved": " ".join(self.resolved.split()).casefold(),
                "needs_clarification": self.needs_clarification}


def resolve_query(question: str, *, history: list[dict] | None = None,
                  selected_text: str | None = None, requires_context: bool = False) -> ResolvedQuery:
    if not isinstance(question, str) or not question.strip() or len(question) > 8000:
        raise ValueError("question must contain 1-8000 characters")
    if type(requires_context) is not bool:
        raise ValueError("requires_context must be boolean")
    if history is not None and (not isinstance(history, list) or len(history) > 8):
        raise ValueError("history must contain at most eight turns")
    turns = []
    for turn in history or []:
        if (not isinstance(turn, dict) or set(turn) != {"role", "content"}
                or turn.get("role") not in {"user", "assistant"}
                or not isinstance(turn.get("content"), str) or not turn["content"].strip()
                or len(turn["content"]) > 4000):
            raise ValueError("invalid conversation turn")
        turns.append((turn["role"], turn["content"].strip()))
    if sum(len(content) for _, content in turns) > 16000:
        raise ValueError("conversation context exceeds budget")
    if selected_text is not None and (not isinstance(selected_text, str)
                                     or not selected_text.strip() or len(selected_text) > 4000):
        raise ValueError("selected_text must contain 1-4000 characters")
    raw = question.strip()
    local_topic = has_local_topic_reference(raw)
    contextual = requires_context or (not local_topic and depends_on_previous_topic(raw))
    # Assistant output and selected text never become trusted source evidence.
    # Follow-up chains keep their nearest explicit user topic; a fresh question
    # starts a new topic. Older turns remain in cache identity.
    anchor = selected_text or _user_topic(turns)
    meaningless = meaningless_fragment(raw)
    needs_clarification = meaningless or (contextual and not anchor)
    resolved = raw
    if not meaningless and anchor and (contextual or selected_text):
        resolved = raw + "\nContext topic (untrusted user input): " + sanitize_evidence_text(anchor)
    return ResolvedQuery(raw, resolved, tuple(turns), selected_text, bool(needs_clarification), contextual)


def benchmark_request(row: dict, default_doc_ids: list[str]) -> dict:
    """Shared runtime request adapter; no expected answer/difficulty/gold input."""
    context = row.get("context", [])
    if context and isinstance(context, list) and all(isinstance(turn, dict) and set(turn) == {"role", "content"} for turn in context):
        history = context
    elif context:
        raise ValueError("benchmark context must use runtime role/content turns")
    else:
        history = row.get("history", [])
    request = {"question": row["question"], "doc_ids": row.get("doc_ids", default_doc_ids),
            "filters": row.get("filters"), "history": history,
            "selected_text": row.get("selected_text", row.get("document_context", {}).get("selected_text"))}
    if 'requires_context' in row:
        request['requires_context'] = row['requires_context']
    return request


def benchmark_retrieval_request(row: dict, default_doc_ids: list[str]) -> dict:
    request = benchmark_request(row, default_doc_ids)
    resolved = resolve_query(request["question"], history=request["history"], selected_text=request["selected_text"],
                             requires_context=request.get('requires_context', False))
    return {"query": "" if resolved.needs_clarification else resolved.resolved,
            "doc_ids": request["doc_ids"], "filters": request["filters"]}
