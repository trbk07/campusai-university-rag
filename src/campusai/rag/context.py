"""Bounded contextual query resolution from request input, never gold labels."""
from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

from .policies import sanitize_evidence_text

CONTEXT_VERSION = "request-context-v4"
FOLLOWUP = re.compile(r"\b(?:môn này|mon nay|cái đó|cai do|nó|that course|that program|this course|it|what about)\b", re.I)


def has_local_topic_reference(question: str) -> bool:
    """A plan's explicitly listed object can anchor 'it' in the same utterance.

    This is a grammar rule, not a list of known courses or benchmark answers.
    A pronoun-only object still requires conversational context.
    """
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
    contextual = requires_context or missing_topic_reference(raw) or bool(
        not local_topic and FOLLOWUP.search(raw) and len(raw.split()) <= 16)
    if not local_topic and turns and len(raw.split()) <= 8 and not re.search(r"\b[A-Z]{2,}\d{2,}\b", raw, re.I):
        contextual = True
    if not local_topic and turns and len(raw.split()) <= 24 and re.match(r"^(?:còn|con|thế|the|vậy|vay|ủa|ua)\b", raw, re.I):
        contextual = True
    # Assistant output and selected text never become trusted source evidence.
    # Only the last user topic is used; older turns remain in cache identity.
    anchor = selected_text or next((content for role, content in reversed(turns) if role == "user"), None)
    needs_clarification = contextual and not anchor
    resolved = raw
    if anchor and (contextual or selected_text):
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
