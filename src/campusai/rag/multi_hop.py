"""Bounded request/source roles for two-hop evidence composition.

No model, network, gold, or source-fact inference occurs in request planning.
The caller supplies already authorized document descriptors. Actual premises
and bridge keys must subsequently be proved from retrieved evidence.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re

from .course_credits import COURSE_CODE, course_code_key, folded

POLICY_VERSION = 'multi-source-v1'
CODE = re.compile(r'(?<![\w.])(' + COURSE_CODE + r')(?!\w)', re.I)
PDF = re.compile(r'(?<![\w.])([\w.-]+\.pdf)\b', re.I)


@dataclass(frozen=True)
class SourceRole:
    doc_id: str
    source_name: str
    code: str | None = None


@dataclass(frozen=True)
class MultiHopRequest:
    kind: str = 'single'
    roles: tuple[SourceRole, ...] = ()
    target_code: str | None = None
    lookup_name: str | None = None
    claimed_bridge: str | None = None
    problem: str | None = None
    policy_version: str = POLICY_VERSION


def _names(documents):
    result = {}
    for doc in documents:
        items = doc.get('items') or []
        name = str(items[0].get('metadata', {}).get('source_name', '')) if items else ''
        if name:
            result.setdefault(name.casefold(), []).append(SourceRole(doc['doc_id'], name))
    return result


def plan_request(question, documents):
    """Resolve explicit sources first; never substitute an unavailable source.

    Simple source-free queries keep their existing path. Filenames identify
    selected documents, never effective dates, program equivalence, or facts.
    """
    raw = str(question)
    text = folded(raw)
    names = _names(documents)
    refs = list(PDF.finditer(raw))
    roles = []
    spans = []
    for ref in refs:
        name = ref[1].casefold()
        matching = names.get(name, [])
        if len(matching) != 1:
            problem = 'source_not_in_selected_scope' if not matching else 'source_identity_ambiguous'
            return MultiHopRequest('unresolved', problem=problem)
        role = matching[0]
        if role.doc_id not in {r.doc_id for r in roles}:
            roles.append(role)
            spans.append(ref.span())
    if len(roles) > 2:
        return MultiHopRequest('unresolved', problem='more_than_two_source_groups')
    # Filenames can contain numeric fragments that are not course codes.
    clean = PDF.sub(' ', raw)
    codes = tuple(dict.fromkeys(course_code_key(m[1]) for m in CODE.finditer(clean)))
    credit = bool(re.search(r'\b(?:tin chi|credits?)\b', text))
    prerequisite = bool(re.search(r'\b(?:tien quyet|prerequisites?)\b', text))
    comparison = bool(re.search(r'\b(?:so sanh|compare|comparison)\b', text))
    # A comparison of one code in exactly two selected documents identifies
    # both sides without requiring the user to type filenames. Document order
    # is kept; it will be part of the request fingerprint, never sorted away.
    selected = [r for values in names.values() for r in values]
    if not refs and comparison and credit and len(codes) == 1 and len(selected) == 2:
        return MultiHopRequest('compare', tuple(SourceRole(r.doc_id,r.source_name,codes[0]) for r in selected))
    if not refs and prerequisite and len(selected) == 1:
        roles = selected
    if len(roles) >= 2 and re.search(r'\b(?:cong nhan thay the|tu dong duoc cong nhan|transferable|automatic equivalence)\b', text):
        return MultiHopRequest('unsupported_relation', tuple(roles), problem='recognition_rule_not_established')
    if prerequisite and roles:
        if credit and len(codes) == 1:
            return MultiHopRequest('prerequisite_lookup', (roles[0],), target_code=codes[0])
        if len(codes) == 2 and re.search(r'\b(?:chung minh|prove|confirm)\b', text):
            return MultiHopRequest('prerequisite_assertion', (roles[0],), target_code=codes[1], claimed_bridge=codes[0])
        return MultiHopRequest('unresolved', tuple(roles), problem='prerequisite_subject_ambiguous')
    if len(roles) == 2 and credit:
        # Named lookup is a user-requested identifier lookup across sources;
        # it does not assert those sources describe interchangeable programs.
        name = re.search(r'\b(?:tim ma mon|find (?:the )?(?:course )?code (?:for|of))\s+(.+?)\s+(?:trong|in)\s+', text)
        if name and not codes:
            original = re.search(r'\b(?:tìm mã môn|find (?:the )?(?:course )?code (?:for|of))\s+(.+?)\s+(?:trong|in)\s+', raw, re.I)
            return MultiHopRequest('name_code_lookup', tuple(roles),
                                   lookup_name=(original[1] if original else name[1]).strip())
        operation = ('difference' if re.search(r'\b(?:tru|minus|chenh lech|difference)\b', text)
                     else 'sum' if re.search(r'\b(?:tong|total|sum)\b', text) else None)
        if operation:
            assigned = []
            previous = 0
            for role, (start, end) in zip(roles, spans):
                preceding = list(CODE.finditer(PDF.sub(' ', raw[previous:start])))
                if len(preceding) != 1:
                    return MultiHopRequest('unresolved', tuple(roles), problem='operand_source_assignment_ambiguous')
                assigned.append(SourceRole(role.doc_id, role.source_name, course_code_key(preceding[0][1])))
                previous = end
            return MultiHopRequest(operation, tuple(assigned))
        if comparison and len(codes) == 1:
            return MultiHopRequest('compare', tuple(SourceRole(r.doc_id, r.source_name, codes[0]) for r in roles))
    return MultiHopRequest()


def request_fingerprint(plan):
    return hashlib.sha256(json.dumps(asdict(plan),sort_keys=True,ensure_ascii=False).encode()).hexdigest()
