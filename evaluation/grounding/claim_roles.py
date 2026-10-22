"""Bounded role checks before lexical gold matching; this is not an NLI judge."""
from __future__ import annotations

import re

from campusai.rag.course_credits import COURSE_CODE, course_code_key, folded
from campusai.rag.claims import CODE_RE

_ENTITY = rf'(?:{COURSE_CODE}|[a-z])'
_NAMED = r'(?:course |mon |hoc phan )?'
_PRE = r'(?:prerequisite|tien quyet)'
_FORWARD = re.compile(
    rf'\b(?P<a>{_ENTITY})\s+(?:is|la)\s+(?:(?:a|the|mon|hoc phan)\s+)?'
    rf'(?P<direct>direct\s+)?{_PRE}(?:\s+(?P<direct_vi>truc tiep))?\s+(?:of|for|cua)\s+'
    rf'{_NAMED}(?P<b>{_ENTITY})\b')
_REQUIRED = re.compile(
    rf'\b(?P<b>{_ENTITY})\s+(?:requires|yeu cau|can)\s+{_NAMED}(?P<a>{_ENTITY})\b'
    rf'(?:\s+(?:as|la)\s+(?:(?:a|the|mon|hoc phan)\s+)?(?P<direct>direct\s+)?{_PRE}'
    rf'(?:\s+(?P<direct_vi>truc tiep))?)?')
_CREDITS = re.compile(
    rf'\b(?P<code>{COURSE_CODE})\s*(?:(?:has|carries|is worth|requires|co)\s+|:\s*)'
    r'(?P<bound>at least|at most|exactly|toi thieu|toi da|chinh xac)?\s*'
    r'(?P<number>\d+(?:[.,]\d+)?)\s+(?:credits?|tin chi)\b')
_CODE_NAME = re.compile(
    rf'^(?:the )?(?:course |mon |hoc phan )?(?P<name>.+?)\s+'
    rf'(?:has (?:course )?code|co ma(?: hoc phan)?)\s+(?P<code>{COURSE_CODE})[.!]?$')
_REMAP_FOR = re.compile(
    rf'\bcorrected (?:course )?code for\s+(?P<old>{COURSE_CODE})\s+is\s+(?P<new>{COURSE_CODE})\b')
_REMAP_TO = re.compile(
    rf'\b(?P<old>{COURSE_CODE})\s+(?:(?:is|was)\s+)?'
    rf'(?:corrected|changed|renamed)\s+(?:to|as)\s+(?P<new>{COURSE_CODE})\b')
_REMAP_VI = re.compile(
    rf'\b(?P<old>{COURSE_CODE})\s+duoc\s+(?:dinh chinh|dieu chinh|doi|thay the)\s+'
    rf'(?:thanh|bang)\s+(?P<new>{COURSE_CODE})\b')
_REMAP_REPLACES = re.compile(
    rf'\b(?P<new>{COURSE_CODE})\s+(?:replaces|thay the)\s+(?P<old>{COURSE_CODE})\b')


def canonical_pair(left: str, right: str) -> tuple[str, str]:
    """Normalise proven code spacing and trailing-zero credit formatting only.

    Quotes/public text are never edited. A spaced token is compacted only when
    the corresponding contiguous identifier actually occurs in this pair.
    """
    codes = {course_code_key(code) for code in CODE_RE.findall(left + ' ' + right)}
    codes.update(course_code_key(code) for code in re.findall(
        rf'\b{COURSE_CODE}\b', left + ' ' + right, flags=re.I)
        if not any(character.isspace() for character in code))

    def canonical(text):
        text = re.sub(rf'\b{COURSE_CODE}\b', lambda match:
            course_code_key(match[0]) if course_code_key(match[0]) in codes else match[0], text, flags=re.I)
        text = re.sub(r'(?<!\w)(\d+)[.,]0+(?=\s*(?:credits?|tín\s+chỉ|tc)\b)', r'\1', text, flags=re.I)
        # Recognised English correction grammars express the same ordered
        # pair. Preserve surrounding text/qualifiers and the lexical threshold.
        for pattern in (_REMAP_FOR, _REMAP_TO, _REMAP_REPLACES):
            text = re.sub(pattern.pattern, lambda match:
                f"{course_code_key(match['old'])} corrected to {course_code_key(match['new'])}",
                text, flags=re.I)
        return text

    return canonical(left), canonical(right)


def _facts(text: str) -> set[tuple]:
    value = folded(text)
    facts = set()
    for pattern in (_FORWARD, _REQUIRED):
        for match in pattern.finditer(value):
            direct = bool(match.groupdict().get('direct') or match.groupdict().get('direct_vi'))
            facts.add(('prerequisite', course_code_key(match['a']), course_code_key(match['b']), direct))
    for match in _CREDITS.finditer(value):
        bound = match['bound'] or 'exact'
        bound = {'exactly': 'exact', 'chinh xac': 'exact', 'toi thieu': 'minimum',
                 'at least': 'minimum', 'toi da': 'maximum', 'at most': 'maximum'}.get(bound, bound)
        number = match['number'].replace(',', '.').rstrip('0').rstrip('.') if '.' in match['number'].replace(',', '.') else match['number']
        facts.add(('credits', course_code_key(match['code']), number, bound))
    if match := _CODE_NAME.fullmatch(value):
        facts.add(('course_code', match['name'].strip(), course_code_key(match['code'])))
    for pattern in (_REMAP_FOR, _REMAP_TO, _REMAP_VI, _REMAP_REPLACES):
        for match in pattern.finditer(value):
            facts.add(('code_correction', course_code_key(match['old']), course_code_key(match['new'])))
    return facts


def roles_compatible(predicted: str, gold: str) -> bool:
    """Reject recognised role swaps or stronger unsupported direct relations.

    Other statement types retain the existing conservative lexical proxy. An
    unrecognised two-endpoint prerequisite cannot use a word bag as entailment.
    """
    left, right = _facts(predicted), _facts(gold)
    kinds = {fact[0] for fact in left} & {fact[0] for fact in right}
    for kind in kinds:
        expected = {fact for fact in right if fact[0] == kind}
        for fact in (item for item in left if item[0] == kind):
            if kind == 'prerequisite':
                if not any(fact[:3] == target[:3] and (not fact[3] or target[3]) for target in expected):
                    return False
            elif fact not in expected:
                return False
    for text, facts in ((predicted, left), (gold, right)):
        normalized = folded(text)
        if (re.search(r'\b(?:prerequisites?|tien quyet)\b', normalized)
                and len(re.findall(rf'\b{_ENTITY}\b', normalized)) >= 2
                and not any(fact[0] == 'prerequisite' for fact in facts)
                and folded(predicted) != folded(gold)):
            return False
        if (re.search(r'\b(?:corrected|changed|renamed|replaces|dinh chinh|dieu chinh|thay the)\b', normalized)
                and len(re.findall(rf'\b{COURSE_CODE}\b', normalized)) >= 2
                and not any(fact[0] == 'code_correction' for fact in facts)
                and folded(predicted) != folded(gold)):
            return False
    return True
