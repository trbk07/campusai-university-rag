"""Small, source-bound temporal eligibility resolver (no model or network).

Version labels select an explicitly requested source; they never prove legal
effectiveness. Unknown precedence is deliberately not resolved by date sorting.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import hashlib
import json
import re
import unicodedata

from ..ingestion.metadata_detector import _iso_date
from ..retrieval.tokenizer_vi import source_body

POLICY_VERSION = 'temporal-v1'


def fold(value):
    value = unicodedata.normalize('NFKD', str(value).casefold().replace('đ', 'd'))
    return ' '.join(''.join(c for c in value if not unicodedata.combining(c)).split())


def version_key(value):
    return re.sub(r'[^a-z0-9]', '', fold(value))


@dataclass(frozen=True)
class TemporalIntent:
    kind: str = 'none'
    versions: tuple[str, ...] = ()
    as_of: str | None = None
    reference_date: str | None = None
    conflict: bool = False
    period_kind: str | None = None


@dataclass(frozen=True)
class TemporalResolution:
    status: str
    reason: str
    eligible_doc_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    groups: tuple[tuple[str, ...], ...] = ()
    policy_version: str = POLICY_VERSION


def parse_temporal_intent(question: str, *, reference_date: date, filters=None):
    text = fold(question)
    # A source table's "current column" is a column label, not a request for
    # legal validity today. Likewise Nhật Bản and khóa luận are not versions.
    text = re.sub(r'\b(?:cot|column)\s+(?:khung\s+)?(?:hien hanh|current)\b', 'source column', text)
    # A student's current exam result describes their input, not whether a
    # policy is legally effective today. Explicit "as of" requests below
    # still require verified temporal provenance.
    text = re.sub(r'\b(my|your)\s+current\s+(?=(?:examination|exam|test)\s+(?:result|score)\b)', r'\1 ', text)
    # Recency attached to an assessment is a factual attribute inside a
    # source, not a request for the newest document version. Explicit document
    # nouns and independent latest-version phrases keep their normal meaning.
    text = re.sub(r'\b(?:latest|newest|most recent)\s+'
        r'(?:(?:process|assessment|examination|exam|test|semester)\s+)?'
        r'(?:scores?|marks?|results?|gpa)\b'
        r'(?!\s+(?:policy|regulation|document|version|rules)\b)', 'assessment value', text)
    if re.search(r'\b(?:tai ngay|as of|on date)\b', text):
        value = _iso_date(text)
        return TemporalIntent('as_of', as_of=value, reference_date=reference_date.isoformat(), conflict=value is None)
    if re.search(r'\b(?:hien hanh|hien tai|currently|current|today)\b', text):
        return TemporalIntent('as_of', as_of=reference_date.isoformat(), reference_date=reference_date.isoformat())
    if re.search(r'\b(?:moi nhat|latest|newest)\b', text):
        return TemporalIntent('latest', reference_date=reference_date.isoformat())
    selected = re.match(r'^(?:use only (?:the )?uploaded|chi dung tai lieu da tai len) [\w.-]+\.pdf\.\s*', text)
    if selected:
        content_question = text[selected.end():]
        # These request a dated fact *inside that source*, not a different
        # document version. The normal grounding/full-source audit must decide
        # whether it is present; a filename never proves the requested fact.
        factual_period = re.search(r'\b(?:hoc phi|tuition|han nop don.*ky tuc xa|dormitory application deadline|my personal gpa|diem (?:trung binh )?ca nhan)\b', content_question)
        version_request = re.search(r'\b(?:version|ban chuong trinh|ban quy che|ban quy dinh|so sanh|compare)\b', content_question)
        if factual_period and not version_request:
            return TemporalIntent()
    framed = re.search(r'\b(?:ban\s+(?:chuong trinh|quy che|quy dinh|nam\s+\d|qh\s*[-–]?\s*\d|\d)|version\b|cohort\s+\d|khoa\s+(?:qh\s*[-–]?\s*)?\d|nam hoc\s+\d|academic year\s+\d)', text)
    if not framed:
        return TemporalIntent()
    labels = re.findall(r'\b(qh\s*[-–]?\s*(?:19|20|21)\d{2}|(?:19|20|21)\d{2})\b', text[framed.start():])
    labels = tuple(dict.fromkeys('QH-' + re.search(r'\d{4}', x)[0] if x.startswith('qh') else x for x in labels))
    if not labels:
        return TemporalIntent('explicit_period', conflict=True)
    compare = bool(re.search(r'\b(?:so sanh|compare|comparison|difference|versus)\b', text))
    compare = compare and not re.search(r'\b(?:khong|not|do not)\s+(?:so sanh|compare)\b', text)
    period_kind = 'cohort' if re.match(r'(?:khoa|cohort)\b', framed[0]) else None
    if re.match(r'(?:nam hoc|academic year)\b', framed[0]):
        period_kind = 'academic_year'
        if len(labels) == 2 and not compare:
            labels = ('-'.join(labels),)
    conflict = len(labels) != (2 if compare else 1)
    year_filter = (filters or {}).get('academic_year')
    if year_filter is not None and any(str(year_filter) != re.search(r'\d{4}', label)[0] for label in labels):
        conflict = True
    return TemporalIntent('compare' if compare else 'explicit_period', labels, conflict=conflict, period_kind=period_kind)


def verified_documents(records):
    """Admit system-owned annotations only with a quote in that exact source.

    A quote establishes provenance, not arbitrary annotation semantics. Date
    fields additionally require matching parsed calendar values and date labels.
    Curated family/version annotations are independently source-reviewed at ingest.
    """
    result = []
    for doc in records:
        items = {i['chunk_id']: i for i in doc.get('items', [])}
        block = doc.get('temporal') or {}
        if not isinstance(block, dict) or not isinstance(block.get('proofs'), dict):
            continue
        proven, evidence = {}, []
        for field, proof in block.get('proofs', {}).items():
            if field not in {'family_id', 'version_label', 'effective_start', 'effective_end', 'published_on', 'replaces', 'cohort_start', 'cohort_end', 'academic_period'} or not isinstance(proof, dict):
                continue
            item = items.get(proof.get('chunk_id'))
            quote = proof.get('quote', '')
            if (not item or not quote or quote not in source_body(item, decode_tables=False)
                    or proof.get('page') != item.get('page')):
                continue
            value = block.get(field)
            if value is None:
                continue
            if field in {'cohort_start', 'cohort_end'}:
                if (type(value) is not int or not 1900 <= value <= 2199 or str(value) not in quote
                        or not re.search(r'\b(?:khoa|tuyen sinh|cohort|intake)\b', fold(quote))):
                    continue
            elif field == 'replaces':
                if not isinstance(value, list) or any(not isinstance(v, str) or not v for v in value):
                    continue
            elif not isinstance(value, str) or not value.strip():
                continue
            if field in {'effective_start', 'effective_end', 'published_on'}:
                markers = (r'\b(?:published|publication|cong bo)\b' if field == 'published_on'
                           else r'\b(?:effective|hieu luc|het hieu luc|valid until|expires?)\b')
                if _iso_date(quote) != value or not re.search(markers, fold(quote)):
                    continue
                try:
                    date.fromisoformat(value)
                except (ValueError, TypeError):
                    continue
            if field == 'version_label' and version_key(value) not in version_key(quote):
                continue
            if field == 'academic_period' and (not re.fullmatch(r'\d{4}-\d{4}', value)
                    or version_key(value) not in version_key(quote)
                    or not re.search(r'\b(?:nam hoc|academic year)\b', fold(quote))):
                continue
            if field == 'replaces' and not re.search(r'\b(?:replaces?|thay the)\b', fold(quote)):
                continue
            proven[field] = value
            evidence.append(item['chunk_id'])
        if proven:
            result.append(dict(doc_id=doc['doc_id'], **proven,
                               evidence_ids=tuple(sorted(set(evidence))),
                               partial_amendment=bool(block.get('partial_amendment'))))
    return result


def resolve_temporal(intent: TemporalIntent, records) -> TemporalResolution:
    docs = verified_documents(records)
    if intent.conflict:
        return TemporalResolution('needs_clarification', 'temporal_request_conflict')
    if intent.kind == 'none':
        families = {}
        for doc in docs:
            if doc.get('family_id') and doc.get('version_label'):
                families.setdefault(doc['family_id'], set()).add(doc['version_label'])
        if any(len(values) > 1 for values in families.values()):
            return TemporalResolution('needs_clarification', 'temporal_version_required')
        return TemporalResolution('not_applicable', 'no_temporal_intent')
    if not docs or len(docs) != len(records):
        return TemporalResolution('insufficient_evidence', 'temporal_metadata_missing')
    by_id = {doc['doc_id']: doc for doc in docs}
    selected = []
    groups = []
    if intent.kind in {'explicit_period', 'compare'}:
        for label in intent.versions:
            if intent.period_kind == 'cohort':
                year = int(re.search(r'\d{4}', label)[0])
                matches = [d for d in docs if d.get('cohort_start', 9999) <= year
                           and year <= d.get('cohort_end', 9999)]
            elif intent.period_kind == 'academic_year':
                matches = [d for d in docs if d.get('academic_period') == label]
            else:
                matches = [doc for doc in docs if version_key(doc.get('version_label', '')) == version_key(label)]
            if not matches:
                return TemporalResolution('insufficient_evidence', 'temporal_version_unavailable')
            if len(matches) != 1:
                return TemporalResolution('conflict', 'temporal_duplicate_version')
            selected.extend(matches)
            groups.append((matches[0]['doc_id'],))
        if intent.kind == 'compare' and (len(selected) != 2 or
                not selected[0].get('family_id') or selected[0].get('family_id') != selected[1].get('family_id')):
            return TemporalResolution('conflict', 'temporal_cross_family_comparison')
    elif intent.kind == 'latest':
        # Latest published is distinct from effective now, including a published
        # future-effective version. Unknown publication dates cannot be ranked.
        if any(not d.get('published_on') for d in docs):
            return TemporalResolution('insufficient_evidence', 'temporal_publication_date_unknown')
        eligible = [d for d in docs if d['published_on'] <= (intent.reference_date or '')]
        if not eligible:
            return TemporalResolution('insufficient_evidence', 'temporal_no_published_version')
        families = {d.get('family_id') for d in eligible}
        if len(eligible) > 1 and (len(families) != 1 or None in families):
            return TemporalResolution('needs_clarification', 'temporal_family_required')
        latest = max(d['published_on'] for d in eligible)
        selected = [d for d in eligible if d['published_on'] == latest]
        if len(selected) != 1:
            return TemporalResolution('conflict', 'temporal_publication_tie')
        groups = [(selected[0]['doc_id'],)]
    else:
        if not intent.as_of and intent.kind == 'as_of':
            return TemporalResolution('needs_clarification', 'temporal_date_required')
        reference = intent.as_of or intent.reference_date
        if not reference:
            return TemporalResolution('insufficient_evidence', 'temporal_reference_date_missing')
        # Labels, signing/upload dates and missing dates cannot establish current.
        if any(not d.get('effective_start') for d in docs):
            return TemporalResolution('insufficient_evidence', 'temporal_effective_date_unknown')
        eligible = [d for d in docs if d['effective_start'] <= reference
                    and (not d.get('effective_end') or reference < d['effective_end'])]
        if not eligible:
            return TemporalResolution('insufficient_evidence', 'temporal_no_effective_version')
        families = {d.get('family_id') for d in eligible}
        if len(eligible) > 1 and (len(families) != 1 or None in families):
            return TemporalResolution('needs_clarification', 'temporal_family_required')
        if any(d.get('partial_amendment') for d in eligible):
            return TemporalResolution('conflict', 'temporal_partial_amendment_scope_required')
        superseded = {old for d in eligible for old in d.get('replaces', []) if old in by_id}
        selected = [d for d in eligible if d['doc_id'] not in superseded]
        if len(selected) != 1:
            return TemporalResolution('conflict', 'temporal_overlapping_versions')
        groups = [(selected[0]['doc_id'],)]
    ids = tuple(sorted(d['doc_id'] for d in selected))
    evidence = tuple(sorted({e for d in selected for e in d['evidence_ids']}))
    return TemporalResolution('resolved', 'temporal_source_selected', ids, evidence, tuple(groups))


def temporal_fingerprint(intent, resolution, records):
    payload = dict(intent=asdict(intent), resolution=asdict(resolution),
                   annotations=[dict(doc_id=d['doc_id'], temporal=d.get('temporal')) for d in records])
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def document_from_items(doc_id, items):
    """Adapt existing ingest metadata without a corpus-wide migration.

    Curated temporal blocks retain their own bindings. Ordinary ingest fields
    are admitted only if their exact label/evidence exists in the source body.
    """
    metadata = items[0].get('metadata', {}) if items else {}
    if items and not metadata.get('temporal'):
        # Legacy indexes predate temporal ingest fields. Reuse the current
        # source parser, then require the same exact chunk/page proof below;
        # document titles and benchmark annotations never supply these values.
        from ..ingestion.metadata_detector import detect_metadata
        source = '\n'.join(f"## Page {item['page']}\n{source_body(item, decode_tables=False)}"
                           for item in items)
        metadata = {**metadata, 'temporal': detect_metadata(source).get('temporal', {})}
    block = dict(metadata.get('temporal') or {})
    if 'proofs' in block:
        return dict(doc_id=doc_id, items=items, temporal=block)
    block['proofs'] = {}

    def proof_for(quote, page):
        for item in items:
            if item.get('page') == page and quote and quote in source_body(item, decode_tables=False):
                return dict(quote=quote, page=page, chunk_id=item['chunk_id'])

    for name, target in [('effective_date', 'effective_start')]:
        entry = block.get('dates', {}).get(name)
        if entry and entry.get('precision') == 'day':
            proof = proof_for(entry.get('quote'), entry.get('source_page'))
            if proof:
                block[target] = entry['value']
                block['proofs'][target] = proof
    for field in ('cohort_start', 'academic_period'):
        entry = block.get(field)
        if isinstance(entry, dict):
            proof = proof_for(entry.get('quote'), entry.get('source_page'))
            block.pop(field)
            if proof:
                block[field] = entry['value']
                block['proofs'][field] = proof
    labels = metadata.get('metadata_evidence', {})
    version = labels.get('version') or {}
    proof = proof_for(version.get('evidence'), version.get('source_page'))
    if proof and version.get('value'):
        block['version_label'] = str(version['value'])
        block['proofs']['version_label'] = proof
    identity = []
    identity_proofs = []
    for field in ('institution', 'program', 'degree_level', 'document_type'):
        entry = labels.get(field) or {}
        proof = proof_for(entry.get('evidence'), entry.get('source_page'))
        if proof and entry.get('value') and fold(entry['value']) in fold(proof['quote']):
            identity.append(fold(entry['value']))
            identity_proofs.append(proof)
    if len(identity) == 4:
        block['family_id'] = hashlib.sha256('|'.join(identity).encode()).hexdigest()
        block['proofs']['family_id'] = identity_proofs[-1]
    return dict(doc_id=doc_id, items=items, temporal=block)
