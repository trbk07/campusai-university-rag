"""Gold-based Phase 5 claim, citation and abstention metrics."""

from __future__ import annotations

from collections import Counter
from functools import lru_cache
import json
import re
import unicodedata
from typing import Iterable

from campusai.rag.confidence import calibration_metrics
from campusai.rag.abstention import canonicalize_abstention_reason
from campusai.rag.claims import _exact_markers, _markers_match
from evaluation.grounding.claim_roles import canonical_pair, roles_compatible

CITATION_QUOTE_POLICY = "reviewed-span-coverage-v7"


def _without_layout_ordinal(span: str, fact: str | None) -> str:
    """Ignore only a leading list label absent from the reviewed factual value.

    Years, decimal quantities, units and any number required by the gold fact
    remain literal. Without a reviewed fact there is no normalization. Source
    coordinates and the entire remaining reviewed span must still match.
    """
    match = re.match(r'^\s*(\d{1,3})[.)]\s+(?=[^\W\d_])', span)
    if not fact or not match:
        return span
    rest = span[match.end():]
    # Preserve an explicitly required inline identity (Item5, R5, ...).
    # Programme CN14 may also be a row14 label: its complete CN14 identity
    # must remain in the literal row rather than disappearing with the label.
    for identity in re.finditer(r'\b[^\W\d_]+(\d+)\b', fact):
        if (int(identity[1]) == int(match[1])
                and not re.search(r'(?<!\w)'+re.escape(identity[0])+r'(?!\w)', rest, re.I)):
            return span
    for marker in _metric_markers(fact):
        value = re.match(r'value:(\d+)', marker)
        if (value and int(value[1]) == int(match[1])
                and marker not in _metric_markers(rest)):
            return span
    if re.match(r'(?:years?|months?|days?|hours?|credits?|percent|năm|tháng|ngày|giờ|tín\s+chỉ)\b', rest, re.I):
        return span
    return rest


@lru_cache(maxsize=8192)
def _quote_spans(quote: str) -> tuple[str, ...]:
    """Keep complete table rows separate; never combine cells across rows."""
    if not isinstance(quote, str) or not quote.strip():
        return ()
    quote = quote.strip()
    if not quote.startswith(("[", "{")):
        return (quote,)
    try:
        value = json.loads(quote)
    except (ValueError, TypeError):
        return ()
    if isinstance(value, dict):
        if (set(value) == {'scope', 'headers', 'rows'} and isinstance(value.get('scope'), str)
                and isinstance(value.get('headers'), list)
                and isinstance(value.get('rows'), list) and value['rows']
                and all(isinstance(row, list) and row and all(isinstance(cell, str) for cell in row)
                        for row in value['rows'])):
            flattened = ' '.join(' '.join(row) for row in value['rows'])
            scope = value['scope'].strip()
            if flattened.casefold().startswith(scope.casefold()):
                flattened = flattened[len(scope):].lstrip()
            return (scope + ' ' + flattened,)
        value = value.get("rows")
    if not isinstance(value, list) or not value:
        return ()
    if all(isinstance(cell, str) for cell in value):
        return (" ".join(value),)
    if all(isinstance(row, list) and row and all(isinstance(cell, str) for cell in row) for row in value):
        return tuple(" ".join(row) for row in value)
    return ()


@lru_cache(maxsize=8192)
def _quote_tokens(text: str) -> tuple[str, ...]:
    # Preserve namespace/suffix and numeric punctuation instead of a word bag.
    return tuple(re.findall(r"[^\W_]+(?:[.,][^\W_]+)*|[%<>≤≥=+\-]",
                            unicodedata.normalize("NFC", text).casefold()))


def _quote_covers_reviewed_span(citation: dict, evidence: dict, fact: str | None = None, *,
                                allow_scoped_table_subspan: bool = False) -> bool:
    """Bounded literal coverage, not a semantic or general NLI judgment.

    Official gold must contain reviewed source quotes. Legacy coordinate-only
    fixture/score rows retain their older proxy; they cannot pass the dataset
    contract that requires gold quotes. Different valid source spans need
    independently reviewed alternatives, never guessed lexical entailment.
    """
    expected = evidence.get("quote")
    if not isinstance(expected, str) or not expected.strip():
        return True
    actual = citation.get("quote")
    if not isinstance(actual, str) or not actual.strip():
        return False
    gold_spans, actual_spans = _quote_spans(expected), _quote_spans(actual)
    if not gold_spans or not actual_spans:
        return False
    for gold_span in gold_spans:
        covered = False
        for actual_span in actual_spans:
            left, right = canonical_pair(_without_layout_ordinal(gold_span, fact),
                                         _without_layout_ordinal(actual_span, fact))
            required, supplied = _quote_tokens(left), _quote_tokens(right)
            if required and any(supplied[i:i + len(required)] == required
                                for i in range(len(supplied) - len(required) + 1)):
                covered = True
                break
        if not covered:
            if allow_scoped_table_subspan and _scoped_table_quote_covers(citation, gold_span, fact):
                continue
            return False
    return True


def _scoped_table_quote_covers(citation: dict, gold_span: str, fact: str | None) -> bool:
    """A directly cited row plus its explicit scope may cover a broad table gold quote."""
    try:
        value = json.loads(citation.get('quote', ''))
    except (TypeError, ValueError):
        return False
    if (not isinstance(value, dict) or set(value) != {'scope', 'headers', 'rows'}
            or not isinstance(value.get('scope'), str) or not value['scope'].strip()
            or not isinstance(value.get('headers'), list)
            or any(not isinstance(header, str) for header in value['headers'])
            or not isinstance(value.get('rows'), list) or not value['rows']):
        return False
    rows = value['rows']
    if any(not isinstance(row, list) or not row or any(not isinstance(cell, str) for cell in row)
           for row in rows):
        return False
    reviewed_tokens = _quote_tokens(gold_span)
    scope_tokens = _quote_tokens(value['scope'])
    if not scope_tokens or not any(reviewed_tokens[i:i + len(scope_tokens)] == scope_tokens
                                   for i in range(len(reviewed_tokens) - len(scope_tokens) + 1)):
        return False
    row_tokens = [_quote_tokens(' '.join(row)) for row in rows]
    if not all(tokens and any(reviewed_tokens[i:i + len(tokens)] == tokens
                              for i in range(len(reviewed_tokens) - len(tokens) + 1))
               for tokens in row_tokens):
        return False
    source_text = value['scope'] + ' ' + ' '.join(' '.join(row) for row in rows)
    fact = str(fact or '')
    required_numbers = set(re.findall(r'(?<!\w)\d+(?:[.,]\d+)?(?!\w)', fact))
    source_numbers = set(re.findall(r'(?<!\w)\d+(?:[.,]\d+)?(?!\w)', source_text))
    if not required_numbers <= source_numbers:
        return False
    if re.search(r'\b(?:credits?|tín\s*chỉ|tin\s*chi)\b', fact, re.I):
        header_text = ' '.join(value['headers']).casefold()
        explicit_cell_units = any(re.fullmatch(r'\s*\d+(?:[.,]\d+)?\s*(?:credits?|tín\s+chỉ)\s*',
                                              cell, re.I) for row in rows for cell in row)
        if not re.search(r'\b(?:credits?|tín\s*chỉ|tin\s*chi)\b', header_text) and not explicit_cell_units:
            return False
    fact_codes = {marker for marker in _metric_markers(fact) if marker.startswith('code:')}
    source_codes = {marker for marker in _metric_markers(source_text) if marker.startswith('code:')}
    if not fact_codes <= source_codes:
        return False
    generic = {'a','an','and','as','at','by','carries','credit','credits','for','has','in','is','of',
                'on','per','semester','the','to','with','year','years'}
    anchors = {token for token in _tokens(str(fact or '')) if token not in generic and not token.isdigit()}
    cited = {token for row in rows for token in _tokens(' '.join(row)) if not token.isdigit()}
    return not anchors or len(anchors & cited) >= min(2, len(anchors))


def _citation_matches_evidence(citation: dict, evidence: dict, fact: str | None = None, *,
                               allow_reviewed_source_subspan: bool = False) -> bool:
    """Require known source coordinates and the reviewed visible source span."""
    same_chunk = bool(citation.get("chunk_id")) and citation.get("chunk_id") == evidence.get("chunk_id")
    expected_doc, expected_page = evidence.get("doc_id"), evidence.get("page")
    if expected_doc is not None and citation.get("doc_id") != expected_doc:
        return False
    same_page = False
    if expected_page is not None:
        if type(expected_page) is not int or type(citation.get("page")) is not int:
            return False
        page_range = citation.get("page_range", [citation["page"], citation["page"]])
        if (not isinstance(page_range, (list, tuple)) or len(page_range) != 2
                or any(type(p) is not int or p < 1 for p in page_range)
                or not page_range[0] <= citation["page"] <= page_range[1]):
            return False
        same_page = page_range[0] <= expected_page <= page_range[1]
        if not same_page:
            return False
    quote_valid = _quote_covers_reviewed_span(citation, evidence, fact,
        allow_scoped_table_subspan=allow_reviewed_source_subspan)
    return (same_chunk or (expected_doc is not None and same_page)) and quote_valid


@lru_cache(maxsize=8192)
def _tokens(value: str) -> frozenset[str]:
    return frozenset(re.findall(r"[\wÀ-ỹ]+", value.casefold()))


def _similarity(left: dict, right: dict) -> float:
    return _text_similarity(str(left.get("text", "")), str(right.get("text", "")))


@lru_cache(maxsize=8192)
def _text_similarity(left: str, right: str) -> float:
    # IDs identify records, never prove entailment. A lexical match cannot
    # override a changed number, code, date, unit, qualifier or polarity.
    left, right = canonical_pair(left, right)
    if (not _markers_match(_metric_markers(left), _metric_markers(right))
            or not roles_compatible(left, right)):
        return 0.0
    # ASCII Vietnamese claims may preserve the entire reviewed statement while
    # omitting accents. Require the same ordered tokens, including all words,
    # values and qualifiers; this is not accent-insensitive fuzzy matching.
    if left.isascii() != right.isascii():
        from campusai.rag.course_credits import folded
        if _quote_tokens(folded(left)) == _quote_tokens(folded(right)):
            return 1.0
    a, b = _tokens(left), _tokens(right)
    return len(a & b) / max(1, len(a | b))


def _canonical_numeric_markers(markers: set[str]) -> set[str]:
    """Normalize only unambiguous repeated locale grouping separators."""
    result = set()
    for marker in markers:
        if marker.startswith('value:'):
            value = marker[6:]
            # Zero-padded counts have the same value; retain the full unit.
            value = re.sub(r'^0+(?=\d)', '', value)
            value = re.sub(r'^(\d+),(\d{1,2})(?=\D|$)', r'\1.\2', value)
            marker = 'value:' + value
            if re.fullmatch(r'\d{1,3}(?:[.,]\d{3}){2,}', value):
                marker = 'value:' + re.sub(r'[.,]', '', value)
        result.add(marker)
    return result


def _metric_markers(text: str) -> set[str]:
    """Canonicalize clearly grouped thousands before exact quantity checks."""
    from campusai.rag.presentation import calendar_presentation
    # A calendar's "tháng 6 năm 2031" is not a six-year duration, nor is
    # "học kỳ 1 năm học ..." a one-year quantity. Whole valid dates retain
    # their exact day/month/year identity under the existing date parser.
    text, _calendar = calendar_presentation(text)
    text = re.sub(r'\b(học\s+kỳ\s+\d+)\s+năm\s+(?:học\s+)?(?=\d{4}\b)',
                  r'\1 academic year ', text, flags=re.I)
    # These are explicit academic units, not inferred semantic synonyms. Do
    # not turn a count, a credit value and a duration into the same marker.
    text = re.sub(r'(?<=\d)\s*(?:years?|năm)\b', ' năm', text, flags=re.I)
    text = re.sub(r'(?<=\d)\s*(?:credits?|tín\s+chỉ|tc)\b', ' tín chỉ', text, flags=re.I)
    markers = _exact_markers(text)
    for match in re.finditer(r'(?<!\d)\d{1,3}(?:[.,]\d{3}){2,}(?!\d)', text):
        raw = match.group()
        markers = {marker for marker in markers
                   if not (marker.startswith('value:') and marker[6:] in raw)}
        markers.add('value:' + re.sub(r'[.,]', '', raw))
    return _canonical_numeric_markers(markers)


def _evidence_set(claim: dict) -> set[tuple]:
    result = set()
    for item in claim.get("evidence", []):
        if isinstance(item, dict) and item.get("chunk_id"):
            result.add(("chunk", item["chunk_id"]))
        elif isinstance(item, dict) and item.get("doc_id") is not None and item.get("page") is not None:
            result.add(("coord", item["doc_id"], item["page"]))
    return result


def _predicted_evidence(row: dict, claim: dict) -> set[tuple]:
    ids = set(claim.get("citation_ids", claim.get("evidence_ids", [])))
    result = {("chunk", item) for item in ids if item}
    if row.get("citations"):
        for item in row.get("citations", []):
            if not isinstance(item, dict):
                continue
            if item.get("chunk_id") in ids:
                if item.get("chunk_id"):
                    result.add(("chunk", item["chunk_id"]))
                if item.get("doc_id") is not None and item.get("page") is not None:
                    result.add(("coord", item["doc_id"], item["page"]))
                    page_range = item.get("page_range", [item["page"], item["page"]])
                    if isinstance(page_range, list) and len(page_range) == 2:
                        result.update(("coord", item["doc_id"], page)
                                      for page in range(int(page_range[0]), int(page_range[1]) + 1))
    return result


def _link_counts(row: dict, predicted: dict, gold: dict, *,
                 allow_reviewed_source_subspan: bool = False) -> tuple[int, int, int]:
    """Count proved gold spans; one source citation can prove several spans."""
    gold_items = [item for item in gold.get("evidence", []) if isinstance(item, dict)]
    predicted_ids = set(str(item) for item in predicted.get("citation_ids", predicted.get("evidence_ids", [])) if item)
    predicted_items = [item for item in row.get("citations", [])
                       if isinstance(item, dict) and item.get("chunk_id") in predicted_ids]
    gold_count = len(gold_items)
    predicted_count = len(predicted_ids)
    if (not row.get("citation_valid", True)
            or len(predicted_items) != len({item.get("chunk_id") for item in predicted_items})):
        return gold_count, predicted_count, 0
    matched = 0
    unused = set(range(len(gold_items)))
    for citation in predicted_items:
        proved = 0
        for index in tuple(unused):
            evidence = gold_items[index]
            if _citation_matches_evidence(citation, evidence, str(gold.get('text', '')),
                                          allow_reviewed_source_subspan=allow_reviewed_source_subspan):
                matched += 1
                proved += 1
                unused.remove(index)
        # Keep the gold-span denominator unchanged. Credit each additional
        # span only after validating its full quote and physical coordinates;
        # a duplicate or irrelevant citation still adds an unmatched link.
        predicted_count += max(0, proved - 1)
    return gold_count, predicted_count, matched


def _expand_gold(claims: list[dict]) -> list[dict]:
    """Make gold atomic at evaluation time without changing the source file."""
    expanded = []
    for claim in claims:
        text = str(claim.get("text", ""))
        # Keep evaluator atomicization aligned with the runtime extractor;
        # annotated multi-evidence answers also use semicolons.
        parts = [part.strip() for part in re.split(r"\s*(?:;|and|và)\s*", text, flags=re.I) if part.strip()]
        # Conjunctions such as "và"/"and" are ordinary title text; keep the
        # reviewed annotation atomic for recall and completeness accounting.
        for part in [text]:
            item = dict(claim)
            item.setdefault("claim_id", f"gold-{len(expanded) + 1}")
            item["text"] = part
            expanded.append(item)
    return expanded


def _comparison_claim(predicted: dict, gold: dict, row: dict | None) -> dict:
    """A proved source locator is not an extra factual numeric value.

    Preserve locators explicitly required by reviewed gold. Otherwise remove
    only the matching label proved by a directly mapped visible citation;
    never license the same number as a quantity elsewhere in the claim.
    """
    from campusai.rag.presentation import LOCATION,VISIBLE_LOCATION,folded,location_key
    if row is None or VISIBLE_LOCATION.search(str(gold.get('text',''))):return predicted
    ids=set(predicted.get('citation_ids',predicted.get('evidence_ids',[])));proven=set()
    for citation in row.get('citations',[]):
        if citation.get('chunk_id') not in ids:continue
        if type(citation.get('page')) is int:proven.add(('page',str(citation['page'])))
        for line in str(citation.get('quote','')).splitlines():
            match=LOCATION.match(folded(line))
            if match:proven.add(location_key(*match.groups()))
    text=VISIBLE_LOCATION.sub(lambda m:' ' if location_key(folded(m[1]),m[2]) in proven else m[0],str(predicted.get('text','')))
    return {**predicted,'text':text}


def _pair_claims(predicted: list[dict], gold: list[dict], row: dict | None = None, *,
                allow_reviewed_source_subspan: bool = False) -> list[tuple[dict, dict | None]]:
    unused = set(range(len(gold)))
    pairs = []
    for claim in predicted:
        if allow_reviewed_source_subspan:
            # Model claims and reviewed annotations need not use the same
            # sentence boundaries. A literal, reviewed composite span can
            # prove several atomic annotations; reuse its physical proof, not
            # a claim ID or a lexical guess. Denominators stay distinct below.
            literal_matches = [i for i in range(len(gold))
                if _pair_similarity(claim, gold[i], row,
                    allow_reviewed_source_subspan=True, literal_only=True) == 1.0]
            if literal_matches:
                for index in literal_matches:
                    unused.discard(index)
                    pairs.append((claim, gold[index]))
                continue
        claim_id = claim.get("claim_id")
        if claim_id:
            exact = [i for i in unused if gold[i].get("claim_id") == claim_id
                     and _pair_similarity(claim,gold[i],row,
                         allow_reviewed_source_subspan=allow_reviewed_source_subspan) >= 0.35]
            if exact:
                index = exact[0]
                unused.remove(index)
                pairs.append((claim, gold[index]))
                continue
        candidates = sorted(((_pair_similarity(claim,gold[i],row,
            allow_reviewed_source_subspan=allow_reviewed_source_subspan), i) for i in unused), reverse=True)
        if candidates and candidates[0][0] >= 0.35:
            _, index = candidates[0]
            unused.remove(index)
            pairs.append((claim, gold[index]))
        else:
            pairs.append((claim, None))
    return pairs


def _pair_similarity(predicted: dict, gold: dict, row: dict | None, *,
                     allow_reviewed_source_subspan: bool = False, literal_only: bool = False) -> float:
    candidate=_comparison_claim(predicted,gold,row)
    if (allow_reviewed_source_subspan
            and _program_code_anchors(str(candidate.get('text', ''))) != _program_code_anchors(str(gold.get('text', '')))):
        return 0.0
    similarity=0.0 if literal_only else _similarity(candidate,gold)
    if row is None:return similarity
    # Lexical overlap must not introduce an unproved bound or condition. A
    # source-faithful contextual projection can still prove it below.
    if (_source_scope_signature(_quote_tokens(str(candidate.get('text',''))))
            != _source_scope_signature(_quote_tokens(str(gold.get('text',''))))):
        similarity=0.0
    required=_quote_tokens(str(gold.get('text','')))
    supplied=_quote_tokens(str(candidate.get('text','')))
    if not required or not supplied:return similarity
    starts=[i for i in range(len(supplied)-len(required)+1) if supplied[i:i+len(required)]==required]
    # Source-faithful contextual quotation can be longer than an atomic gold
    # fact. Require the entire prediction in its actual cited quote AND the
    # reviewed gold span/provenance. Do not infer entailment from word overlap.
    negating={'not','no','never','false','if','unless','neither','không','chưa','chẳng','nếu'}
    if starts and all(negating.intersection(supplied[:i]) for i in starts):return 0.0
    if similarity>=.35:return similarity
    # An independently reviewed evidence span binds the gold meaning to its
    # original source language. Literal reproduction of that complete span
    # needs no guessed bilingual synonym/entailment mapping.
    ids=set(predicted.get('citation_ids',predicted.get('evidence_ids',[])))
    for citation in row.get('citations', []):
        if citation.get('chunk_id') not in ids:
            continue
        for evidence in gold.get('evidence', []):
            if not _citation_matches_evidence(citation, evidence, str(gold.get('text', '')),
                    allow_reviewed_source_subspan=allow_reviewed_source_subspan):
                continue
            for span in _quote_spans(str(evidence.get('quote', ''))):
                literal = re.sub(r'^\s*(?:[-*\u2022]\s+)(?=[^\W\d_])', '', span)
                # The full reviewed heading is still required in the visible
                # citation above, even when the factual claim omits its label.
                factual = re.sub(r'^\s*(?:[-*\u2022]\s+)(?=[^\W\d_])', '', str(candidate.get('text', '')))
                if allow_reviewed_source_subspan:
                    # A longer, verbatim source statement can contain the
                    # reviewed fact plus its original context. Require both
                    # complete literal spans, the same provenance, exact gold
                    # anchors and unchanged qualification/polarity. An edited
                    # paraphrase or an appended model assertion cannot pass.
                    anchor_prefixes = ('code:', 'value:', 'year:', 'date:')
                    required_anchors = {m for m in _metric_markers(str(gold.get('text', '')))
                                        if m.startswith(anchor_prefixes)}
                    actual_anchors = {m for m in _metric_markers(factual) if m.startswith(anchor_prefixes)}
                    fragment = re.sub(r'^(?:và|and)\s+', '', literal, flags=re.I)
                    fragment_tokens, factual_tokens = _quote_tokens(fragment), _quote_tokens(factual)
                    contains = lambda outer, inner: bool(inner) and any(
                        outer[i:i+len(inner)] == inner for i in range(len(outer)-len(inner)+1))
                    expected_scope = _source_scope_signature(_quote_tokens(str(gold.get('text', ''))))
                    actual_scope = _source_scope_signature(factual_tokens)
                    fragment_ends = [i+len(fragment_tokens) for i in range(len(factual_tokens)-len(fragment_tokens)+1)
                                     if factual_tokens[i:i+len(fragment_tokens)] == fragment_tokens]
                    scope_preserved = ((_literal_scope_matches(factual,str(gold.get('text','')))
                        and not (actual_scope-expected_scope)&{'conditional','exclusion','restriction'}) or (
                        actual_scope - expected_scope <= {'conditional','exclusion'}
                        and any(_source_scope_signature(factual_tokens[:end]) == expected_scope
                                for end in fragment_ends)))
                    if (len(fragment_tokens) >= 4 and required_anchors <= actual_anchors
                            and scope_preserved
                            and contains(factual_tokens, fragment_tokens)
                            and any(contains(_quote_tokens(actual), factual_tokens)
                                    for span in _quote_spans(str(citation.get('quote', '')))
                                    for actual in _literal_source_versions(span))):
                        return 1.0
                    if _literal_list_projection(factual, str(citation.get('quote', '')), literal,
                                                str(gold.get('text', ''))):
                        return 1.0
                    if required_anchors <= actual_anchors and _scoped_table_quote_covers(citation, span, str(gold.get('text', ''))):
                        try: table = json.loads(citation['quote'])
                        except (ValueError, TypeError): table = {}
                        if isinstance(table, dict):
                            for source_row in table.get('rows', []):
                                projection = str(table.get('scope', '')) + ' ' + ' '.join(source_row)
                                if _quote_tokens(projection) == factual_tokens:
                                    return 1.0
                if (allow_reviewed_source_subspan
                        and _reviewed_source_subspan(factual, literal, str(gold.get('text', '')))):
                    return 1.0
                stripped = _without_layout_ordinal(literal, str(gold.get('text', '')))
                if stripped != literal:
                    # A claim may omit a proved layout label, but cannot gain
                    # permission to discard an unrelated unproved number.
                    label = re.match(r'^\s*(\d{1,3})[.)]\s+', literal)
                    if label and re.match(r'^\s*'+re.escape(label[1])+r'[.)]\s+', factual):
                        factual = _without_layout_ordinal(factual, str(gold.get('text', '')))
                    literal = stripped
                heading = r'^\s*(?:article|\u0111i\u1ec1u|dieu)\s+\d+[.:)]\s*'
                if not re.match(heading, factual, flags=re.I):
                    literal = re.sub(heading, '', literal, flags=re.I)
                left, right = canonical_pair(literal, factual)
                if _quote_tokens(left) and _quote_tokens(left) == _quote_tokens(right):
                    return 1.0
    starts=[i for i in starts if not negating.intersection(supplied[:i])]
    if not starts:return similarity
    ids=set(predicted.get('citation_ids',predicted.get('evidence_ids',[])))
    for citation in row.get('citations',[]):
        if citation.get('chunk_id') not in ids:continue
        if not any(_citation_matches_evidence(citation,e,str(gold.get('text','')),
                   allow_reviewed_source_subspan=allow_reviewed_source_subspan)
                   for e in gold.get('evidence',[])):continue
        for span in _quote_spans(str(citation.get('quote',''))):
            actual=_quote_tokens(span)
            if any(actual[i:i+len(supplied)]==supplied for i in range(len(actual)-len(supplied)+1)):
                return 1.0
    return similarity


_SOURCE_SCOPE_GROUPS = {
    'negation': frozenset({'not', 'no', 'never', 'neither', 'không', 'chưa', 'chẳng'}),
    'conditional': frozenset({'if', 'unless', 'nếu'}),
    'restriction': frozenset({'only'}),
    'exclusion': frozenset({'without', 'except', 'trừ'}),
}
_SOURCE_CLAUSE_END = frozenset({'.', ';', ':', '!', '?', ')'})


def _literal_source_versions(text: str) -> tuple[str, ...]:
    """An explicit example list can be omitted, never a scope/value condition."""
    def example(match):
        value=match[1]
        if (_source_scope_signature(_quote_tokens(value)) or _program_code_anchors(value)
                or any(m.startswith(('value:','date:','year:')) for m in _metric_markers(value))):
            return match[0]
        return ' '
    shortened=re.sub(r'\((\s*(?:bao gồm|including|such as|for example)\b[^()]{0,500})\)',
                     example,text,flags=re.I)
    return tuple(dict.fromkeys((text,shortened)))


def _quantity_bounds(text: str) -> set[tuple]:
    """Bind a stated minimum/maximum to its own value and unit, not a word bag."""
    from campusai.rag.course_credits import folded
    text=folded(text)
    result=set()
    bounds={'minimum':r'at least|minimum|min|toi thieu|it nhat',
            'maximum':r'at most|maximum|max|no more than|not exceed|khong (?:duoc )?vuot qua|khong qua|toi da'}
    units={'credit':'credits','credits':'credits','tc':'credits','tin chi':'credits',
           'hour':'hours','hours':'hours','gio':'hours','month':'months','months':'months',
           'thang':'months','year':'years','years':'years','nam':'years'}
    for kind,pattern in bounds.items():
        for match in re.finditer(r'\b(?:'+pattern+r')\b\s*(?:(?:of|is|la)\s+)?[:=]?\s*'
                                r'(\d+(?:[.,]\d+)?)(?:\s*(credits?|tin chi|tc|hours?|gio|months?|thang|years?|nam)\b)?',text):
            result.add((kind,float(match[1].replace(',','.')),units.get(match[2])))
    for match in re.finditer(r'\b(?:tu\s+(?:diem\s+)?|from\s+(?:grade\s+)?)([a-f]\+?)\s+(?:tro len|or (?:above|higher)|and (?:above|up))\b',text):
        result.add(('minimum',match[1],None))
    grades=re.sub(r'\(hoac quy doi tuong duong\)','',text)
    for match in re.finditer(r'\b(?:at least\s+(?:grade\s+)?|tu\s+(?:diem\s+)?)'
                            r'([a-f]\+?)(?=\s|[.,;]|$)',grades):
        if match[0].startswith('at least') or re.match(r'\s+tro len\b',grades[match.end():]):
            result.add(('minimum',match[1],None))
    return result


def _literal_scope_matches(claim: str, gold: str, *, reviewed_context: str = '') -> bool:
    """Extra verbatim context is allowed; required values/roles cannot vanish."""
    from campusai.rag.course_credits import folded
    left,right=folded(claim),folded(gold)
    outside=r'\b(?:outside (?:academic )?warning|not under (?:academic )?warning|khong thuoc (?:dien )?canh bao(?: hoc tap)?)\b'
    bound=r'\b(?:no more than|not exceed|khong (?:duoc )?vuot qua|khong qua)\b'
    exempt=r'\b(?:exempt(?:ion)?|mien|khong ap dung)\b'
    def negative(value):
        value=re.sub(outside,'',re.sub(bound,'',value))
        return bool(re.search(r'\b(?:not|no|never|khong|chua|chang)\b|'+exempt,value))
    if negative(left)!=negative(right) or not _quantity_bounds(gold)<=_quantity_bounds(claim):
        return False
    roles=(r'\b(?:final[- ]year|last year|nam cuoi)\b',exempt,outside,
           r'\b(?:annual|yearly|per year|trong (?:mot|1) nam(?: hoc)?)\b',
           r'\b(?:semester|hoc ky)\b',r'\b(?:bachelor|undergraduate|cu nhan|sinh vien)\b',
           r'\b(?:engineer|ky su)\b',r'\b(?:master|thac si|hoc vien)\b',
           r'\b(?:doctoral|doctorate|phd|tien si|ncs|nghien cuu sinh)\b')
    # A following sentence can refer to the same courses explicitly named in
    # the reviewed sentence. Permit inheritance only for an anaphoric subject
    # and one unambiguous academic population in that reviewed context.
    population=roles[-4:]
    context=folded(reviewed_context)
    inherited=(bool(re.match(r'^(?:those|these) courses\b|^nhung hoc phan\b',left))
        and sum(bool(re.search(role,context)) for role in population)==1)
    return all(not re.search(role,right) or re.search(role,left)
               or (inherited and role in population and re.search(role,context)
                   and not any(re.search(other,left) for other in population if other!=role))
               for role in roles)


def _literal_list_projection(claim: str, quote: str, reviewed: str, gold: str) -> bool:
    """Prove a shared quantity predicate plus one complete semicolon item.

    No words or values are generated: both parts must reproduce the source in
    order, and the selected item must contain the entire reviewed evidence.
    This handles a literal minimum shared by a list without inventing one.
    """
    wanted, evidence = _quote_tokens(claim), _quote_tokens(reviewed)
    if len(evidence) < 4 or not wanted:
        return False
    gold_scope, claim_scope = _source_scope_signature(_quote_tokens(gold)), _source_scope_signature(wanted)
    if not gold_scope <= claim_scope or claim_scope - gold_scope - {'minimum'}:
        return False
    anchors = lambda text: {m for m in _metric_markers(text)
                            if m.startswith(('code:', 'value:', 'year:', 'date:'))}
    if not anchors(gold) <= anchors(claim):
        return False
    contains = lambda outer, inner: any(outer[i:i+len(inner)] == inner
                                       for i in range(len(outer)-len(inner)+1))
    for sentence in re.split(r'(?<=[.!?])\s+', quote):
        if ';' not in sentence or len(sentence) > 2048:
            continue
        parts = sentence.split(';')
        for item in parts[1:]:
            if not contains(_quote_tokens(item), evidence):
                continue
            for value in re.finditer(r'(?<!\w)\d+(?:[.,]\d+)?\s*(?:giờ|hours?|tín\s+chỉ|credits?|tháng|months?|năm|years?)\b',
                                     parts[0], re.I):
                projection = _quote_tokens(parts[0][:value.start()] + item.strip())
                if (contains(projection, wanted)
                        and _source_scope_signature(projection) == claim_scope):
                    return True
    return False


def _source_scope_signature(tokens: tuple[str, ...] | list[str]) -> frozenset[str]:
    token_set = set(tokens)
    signature = {group for group, markers in _SOURCE_SCOPE_GROUPS.items()
                 if token_set.intersection(markers)}
    text = ' '.join(tokens)
    if re.search(r'\b(?:at least|minimum|min)\b|\b(?:ít nhất|tối thiểu)\b|\btừ\b(?:\s+[^\W\d_]+){0,4}\s+(?:\d+(?:[.,]\d+)?|[a-f])\s+(?:hoặc quy đổi tương đương\s+)?trở lên\b', text):
        signature.add('minimum')
    if re.search(r'\b(?:at most|maximum|max|no more than|may not exceed|must not exceed)\b|\b(?:không quá|không (?:được )?vượt quá|tối đa|cao nhất)\b', text):
        signature.add('maximum')
    if re.search(r'\b(?:exactly|precisely)\b|\b(?:chính xác|đúng)\b', text):
        signature.add('exact')
    return frozenset(signature)


def _program_code_anchors(text: str) -> frozenset[str]:
    # Preserve all-caps academic identifiers such as CN2, PO1 and PHI5001;
    # don't mistake ordinary labels, currency units or "Level 4" for a code.
    compact = re.sub(r'(?<![A-Za-z])([A-Z]{2,5})\s+(\d{1,5})(?!\d)', r'\1\2', text)
    currencies = {'VND', 'USD', 'EUR', 'JPY', 'GBP', 'CNY', 'CAD', 'AUD', 'SGD', 'THB', 'RUB', 'INR'}
    return frozenset(code for code in re.findall(
        r'(?<![A-Za-z0-9])[A-Z]{2,5}\d{1,5}(?![A-Za-z0-9])', compact)
        if re.match(r'[A-Z]+', code).group() not in currencies)


def _reviewed_source_subspan(claim: str, reviewed_quote: str, gold_text: str) -> bool:
    """Accept a claim copied from its reviewed quote, without semantic guessing.

    This is for cross-language predictions that preserve the source wording but
    answer only one clause of a longer reviewed quote. The citation has already
    been bound to that exact reviewed span. Requiring a contiguous literal
    subspan, matching gold numeric anchors and preserving scope/polarity markers
    keeps this narrower than general lexical entailment.
    """
    claim = re.sub(r'^\s*(?:lưu ý|xin lưu ý|note(?: that)?|please note that)\b\s*[:,;\-]?\s*',
                   '', claim, flags=re.I)
    source_versions = [_quote_tokens(value) for value in _literal_source_versions(reviewed_quote)]
    claim_tokens = _quote_tokens(claim)
    if not claim_tokens or len(claim_tokens) < 4:
        return False
    anchor_prefixes = ('code:', 'value:', 'year:', 'date:')
    # Exact number/year/code identity is checked below using canonical metric
    # markers, including unambiguous locale thousands separators.
    gold_anchors = {marker for marker in _metric_markers(gold_text) if marker.startswith(anchor_prefixes)}
    claim_anchors = {marker for marker in _metric_markers(claim) if marker.startswith(anchor_prefixes)}
    if not gold_anchors <= claim_anchors:
        return False
    claim_markers = _source_scope_signature(claim_tokens)
    if not _literal_scope_matches(claim,gold_text,reviewed_context=reviewed_quote):
        return False
    for source_tokens in source_versions:
        for start in range(len(source_tokens) - len(claim_tokens) + 1):
            if source_tokens[start:start + len(claim_tokens)] != claim_tokens:
                continue
            clause_start = max((i + 1 for i, token in enumerate(source_tokens[:start])
                                if token in _SOURCE_CLAUSE_END), default=0)
            source_prefix_markers = _source_scope_signature(source_tokens[clause_start:start])
            if source_prefix_markers - claim_markers:
                continue
            return True
    return False


def is_grounded_answer(row: dict, *, allow_reviewed_source_subspan: bool = False) -> bool:
    """Gold-link correctness proxy for calibration, separate from source review."""
    if is_native_evaluation_failure(row):
        return False
    if not bool(row.get("answerable", True)) or row.get("abstained"):
        return False
    if "gold_claims" not in row:
        return True  # Legacy score-only calibration inputs.
    gold = _expand_gold(row["gold_claims"])
    pairs = _pair_claims(row.get("claims", []), gold, row,
                         allow_reviewed_source_subspan=allow_reviewed_source_subspan)
    if not gold or not pairs:
        return False
    complete = [(p, g) for p, g in pairs if g is not None and p.get('status') == 'supported'
               and _link_counts(row, p, g, allow_reviewed_source_subspan=allow_reviewed_source_subspan)[2] == len(g.get("evidence", []))
               and len(g.get('evidence', [])) > 0]
    if ({id(p) for p, _ in complete} != {id(p) for p in row.get('claims', [])}
            or {g.get('claim_id') for _, g in complete} != {g.get('claim_id') for g in gold}):
        return False
    return all(any(citation.get('chunk_id') in pred.get('citation_ids', pred.get('evidence_ids', []))
                   and any(_citation_matches_evidence(citation, e, str(g.get('text', '')),
                           allow_reviewed_source_subspan=allow_reviewed_source_subspan)
                           for e in g.get('evidence', []))
                   for pred, g in complete)
               for citation in row.get('citations', []))


def is_native_evaluation_failure(row: dict) -> bool:
    """Provider and pipeline faults are missing predictions, never gold negatives."""
    return bool(row.get("native_failure") or row.get("provider_failure")
                or row.get("pipeline_error_type"))


def evaluable_prediction_rows(rows: Iterable[dict]) -> list[dict]:
    """Return rows with an actual pipeline outcome suitable for quality scoring."""
    return [row for row in rows if not is_native_evaluation_failure(row)]


def evaluate_grounding(rows: Iterable[dict], *, allow_reviewed_source_subspan: bool = False) -> dict:
    source_rows = list(rows)
    rows = evaluable_prediction_rows(source_rows)
    excluded_native_failures = len(source_rows) - len(rows)
    row_pairs = [_pair_claims(row.get("claims", []), _expand_gold(row.get("gold_claims", [])), row,
                              allow_reviewed_source_subspan=allow_reviewed_source_subspan) for row in rows]
    pairs = [pair for group in row_pairs for pair in group]
    predicted_claim_count = sum(len(row.get("claims", [])) for row in rows)
    matched_predicted_claim_count = sum(len({id(pred) for pred, gold in group if gold is not None})
                                       for group in row_pairs)
    matched_gold_claim_count = sum(len({gold.get("claim_id") for _, gold in group if gold is not None})
                                   for group in row_pairs)
    grounded_predicted = grounded_gold = 0
    gold_count = sum(len(_expand_gold(row.get("gold_claims", []))) for row in rows)
    leaked = sum(bool(row.get("public", not row.get("abstained", False)))
                 and pred.get("status") != "contradicted"
                 and (gold is None or not bool(gold.get("answerable", True))
                      or pred.get("status") in {"unsupported", "ambiguous", "partial", "partially_supported"})
                 for row, group in zip(rows, row_pairs)
                 for pred, gold in {id(p): (p, g) for p, g in group}.values())
    contradicted_leaked = sum(pred.get("status") == "contradicted"
                               and bool(row.get("public", not row.get("abstained", False)))
                               for row, group in zip(rows, row_pairs)
                               for pred in {id(p): p for p, _ in group}.values())

    citation_total = valid_citations = coordinate_total = coordinate_valid = gold_links = predicted_links = linked_correct = 0
    complete_total = complete_hit = 0
    # Missed gold claims still belong in recall/completeness denominators.
    gold_links = sum(len(claim.get("evidence", [])) for row in rows
                     for claim in _expand_gold(row.get("gold_claims", []))
                     if bool(claim.get("answerable", True)))
    complete_total = sum(bool(claim.get("answerable", True)) for row in rows
                         for claim in _expand_gold(row.get("gold_claims", [])))
    for row, pairs_for_row in zip(rows, row_pairs):
        complete_predictions, complete_annotations, correct_links = set(), set(), set()
        citations = [item for item in row.get("citations", []) if isinstance(item, dict)]
        citation_total += len(citations)
        coordinate_total += len(citations)
        coordinate_valid += len(citations) if row.get("citation_valid", True) else 0
        for citation in citations:
            mapped = [(pred, gold) for pred, gold in pairs_for_row
                      if citation.get("chunk_id") in pred.get("citation_ids", pred.get("evidence_ids", []))]
            # A shared citation must support every claim assigned to it. An
            # orphan or a quote for only one of two course rows is not correct.
            valid_citations += bool(mapped) and row.get("citation_valid", True) and all(
                any(gold is not None and bool(gold.get('answerable', True))
                    and any(_citation_matches_evidence(citation, evidence, str(gold.get('text', '')),
                            allow_reviewed_source_subspan=allow_reviewed_source_subspan)
                            for evidence in gold.get('evidence', []) if isinstance(evidence, dict))
                    for candidate, gold in mapped if candidate is pred)
                for pred in {id(p): p for p, _ in mapped}.values())
        for pred, gold in pairs_for_row:
            if gold is None or not bool(gold.get("answerable", True)):
                predicted_links += len(set(pred.get("citation_ids", pred.get("evidence_ids", []))))
                continue
            row_gold_links, row_predicted_links, row_matched_links = _link_counts(
                row, pred, gold, allow_reviewed_source_subspan=allow_reviewed_source_subspan)
            complete = (row_gold_links > 0 and row_matched_links == row_gold_links
                        and pred.get("status") == "supported")
            if complete:
                complete_predictions.add(id(pred))
                complete_annotations.add(gold.get('claim_id'))
            predicted_links += row_predicted_links
            ids = set(pred.get('citation_ids', pred.get('evidence_ids', [])))
            for index, evidence in enumerate(gold.get('evidence', [])):
                if any(c.get('chunk_id') in ids and _citation_matches_evidence(c, evidence,
                        str(gold.get('text', '')),
                        allow_reviewed_source_subspan=allow_reviewed_source_subspan) for c in citations):
                    correct_links.add((gold.get('claim_id'), index))
        grounded_predicted += len(complete_predictions)
        grounded_gold += len(complete_annotations)
        complete_hit += len(complete_annotations)
        linked_correct += len(correct_links)

    predicted_abstain = [bool(row.get("abstained")) for row in rows]
    gold_abstain = [not bool(row.get("answerable", True)) for row in rows]
    tp = sum(p and g for p, g in zip(predicted_abstain, gold_abstain))
    fp = sum(p and not g for p, g in zip(predicted_abstain, gold_abstain))
    fn = sum(not p and g for p, g in zip(predicted_abstain, gold_abstain))
    reason_pairs = [
        (canonicalize_abstention_reason(
            row.get("abstention_reason", row.get("reason")),
            evidence_found=bool(row.get("retrieved_pages")),
        ), row.get("gold_abstention_reason"))
        for row in rows if row.get("abstained") and row.get("gold_abstention_reason")
    ]
    reasons = Counter(canonicalize_abstention_reason(
        row.get("abstention_reason", row.get("reason")),
        evidence_found=bool(row.get("retrieved_pages")),
    ) for row in rows if row.get("abstained"))
    citation_precision = valid_citations / max(1, citation_total)
    link_precision = linked_correct / max(1, predicted_links)
    link_recall = linked_correct / max(1, gold_links)
    confidence_scores = []
    confidence_labels = []
    label_scores = {"low": 0.25, "medium": 0.60, "high": 0.90}
    for row in rows:
        score = row.get("confidence_score")
        if score is None:
            score = 0.0 if row.get("abstained") else label_scores.get(row.get("confidence"))
        if score is not None:
            confidence_scores.append(float(score))
            confidence_labels.append(is_grounded_answer(
                row, allow_reviewed_source_subspan=allow_reviewed_source_subspan))
    calibration = calibration_metrics(confidence_scores, confidence_labels) if confidence_scores else {
        "brier_score": 1.0, "ece": 1.0, "count": 0,
    }
    return {
        "records": len(rows),
        "excluded_native_failures": excluded_native_failures,
        "claim_count": predicted_claim_count,
        "predicted_claim_count": predicted_claim_count,
        "matched_predicted_claim_count": matched_predicted_claim_count,
        "gold_claim_count": gold_count,
        "matched_gold_claim_count": matched_gold_claim_count,
        "grounded_claim_precision": round(grounded_predicted / max(1, predicted_claim_count), 6),
        "grounded_claim_recall": round(grounded_gold / max(1, gold_count), 6),
        "unsupported_claim_leakage": round(leaked / max(1, predicted_claim_count), 6),
        "contradicted_claim_leakage": round(contradicted_leaked / max(1, predicted_claim_count), 6),
        "citation_precision": round(citation_precision, 6),
        "citation_coordinate_validity": round(coordinate_valid / max(1, coordinate_total), 6),
        "citation_recall": round(link_recall, 6),
        "citation_completeness": round(complete_hit / max(1, complete_total), 6),
        "claim_citation_precision": round(link_precision, 6),
        "claim_citation_recall": round(link_recall, 6),
        "claim_citation_f1": round(2 * link_precision * link_recall / max(1e-12, link_precision + link_recall), 6),
        "abstention_precision": round(tp / max(1, tp + fp), 6),
        "abstention_recall": round(tp / max(1, tp + fn), 6),
        "reason_accuracy": round(sum(p == g for p, g in reason_pairs) / max(1, len(reason_pairs)), 6),
        "brier_score": calibration["brier_score"],
        "ece": calibration["ece"],
        "calibration_count": calibration["count"],
        "schema_invalid_rate": round(sum(not row.get("schema_valid", True) for row in rows) / max(1, len(rows)), 6),
        "abstention_reason_counts": dict(reasons),
        "denominators": {
            "records": len(rows), "predicted_claims": predicted_claim_count,
            "gold_claims": gold_count, "citations": citation_total,
            "gold_citation_links": gold_links, "predicted_citation_links": predicted_links,
            "predicted_abstentions": tp + fp, "gold_abstentions": tp + fn,
            "abstention_reasons": len(reason_pairs),
        },
    }
