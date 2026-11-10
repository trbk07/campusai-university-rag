"""Offline boundaries for automated blind review; never a gold author or RAG input.

Only a separate reviewer worker may supply private-gold review receipts. This
module validates its public manifest and scores every case, including missing
predictions. A syntactically valid receipt is not proof of worker isolation:
the gate requires a separately verified, pinned isolation receipt as well.
No provider calls, credentials, private answers or generated reports live here.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone

from .verify_answers import inference_payload, response_errors


MIN_CASES = 200
MIN_ACCURACY = .95


def expand_source_quote(quote, proposed_quote, page_text):
    """Recover an elided quote's full literal source span, never an approval.

    All reviewer paragraphs, including punctuation, must occur unchanged and
    in order inside the already proposed span. Both endpoints must agree. The
    returned evidence retains ALL omitted source words, exceptions and numbers.
    Callers must independently validate reviewer/fact/document/page bindings.
    No fuzzy matching, spelling repair, value correction or verdict changes.
    """
    def normalize(value):
        return ' '.join(unicodedata.normalize('NFKC', value).split())

    if any(not isinstance(value, str) or not value.strip()
           for value in (quote, proposed_quote, page_text)):
        return None
    short, full, source = map(normalize, (quote, proposed_quote, page_text))
    if full not in source:
        return None
    wanted, available = short.split(), full.split()
    if (len(wanted) < 8 or len(wanted) >= len(available)
            or wanted[0] != available[0] or wanted[-1] != available[-1]):
        return None
    paragraphs = [normalize(part).split() for part in
                  re.split(r'\n\s*\n', proposed_quote.strip()) if part.strip()]
    if len(paragraphs) < 3:
        return None
    # Only whole intervening paragraphs may be omitted. Never drop a negation,
    # exception, operator or quantity from inside a retained paragraph.
    positions = {0}
    for index, paragraph in enumerate(paragraphs):
        following = set(positions) if 0 < index < len(paragraphs)-1 else set()
        for position in positions:
            if wanted[position:position+len(paragraph)] == paragraph:
                following.add(position+len(paragraph))
        positions = following
    return proposed_quote if len(wanted) in positions else None


def normalize_review_indices(review, proposals, *, quarantine_invalid=False):
    """Canonicalize consistent zero-based fact references, never review content.

    This is representation repair only: no verdict, expected fact, quote, page
    or approval changes. Mixed/out-of-range references within a turn fail
    closed, or remain unmodified with an explicit quarantine flag. Downstream
    approval must reject quarantined turns and verify full fact/source coverage.
    """
    if not isinstance(review, dict) or set(review) != {'cases'}:
        raise ValueError('review_cases_required')
    if ([c.get('case_id') for c in review['cases']] != [c.get('case_id') for c in proposals]
            or len({c.get('case_id') for c in proposals}) != len(proposals)):
        raise ValueError('review_case_binding_mismatch')
    canonical = json.loads(json.dumps(review))
    bases = set(); reference_count = 0; quarantined = []; shifts = 0
    for case, gold in zip(canonical['cases'], proposals):
        if len(case['turns']) != len(gold['turns']):
            raise ValueError('review_turn_binding_mismatch')
        for n, (turn, proposed) in enumerate(zip(case['turns'], gold['turns']), 1):
            if turn['turn'] != n:
                raise ValueError('review_turn_binding_mismatch')
            size = len(proposed['required_facts'])
            values = list(turn['approved_fact_indices']) + [e['fact_index'] for e in turn['approved_evidence']]
            reference_count += len(values)
            error = ('review_integer_fact_references_required' if any(type(v) is not int for v in values) else None)
            base = 0 if 0 in values else 1
            if error is None and any(not (0 <= v < size if base == 0 else 1 <= v <= size) for v in values):
                error = 'review_indices_mixed_or_out_of_range'
            if error:
                if not quarantine_invalid:
                    raise ValueError(error)
                quarantined.append({'case_id':case['case_id'],'turn':n,'error':error})
                continue
            if values:bases.add(base)
            if base == 0:
                turn['approved_fact_indices'] = [value + 1 for value in turn['approved_fact_indices']]
                for evidence in turn['approved_evidence']:
                    evidence['fact_index'] += 1
                shifts += 1
    source_base = next(iter(bases)) if len(bases)==1 else 'mixed_by_turn' if bases else 1
    return canonical, {'source_base':source_base,'canonical_base':1,
        'shift':int(bool(shifts)),'reference_count':reference_count,
        'normalized_turns':shifts,'quarantined_turns':quarantined}


def canonicalize_fact_id_review(review, proposals, *, quarantine_invalid=False):
    """Bind reviewer evidence to exact opaque fact IDs; never guess indices."""
    if (not isinstance(review,dict) or set(review)!={'cases'}
            or [c.get('case_id') for c in review['cases']]!=[c.get('case_id') for c in proposals]
            or len({c.get('case_id') for c in proposals})!=len(proposals)):
        raise ValueError('review_case_binding_mismatch')
    canonical=json.loads(json.dumps(review));quarantine=[]
    for case,proposed in zip(canonical['cases'],proposals):
        if len(case['turns'])!=len(proposed['turns']):raise ValueError('review_turn_binding_mismatch')
        for n,(turn,gold) in enumerate(zip(case['turns'],proposed['turns']),1):
            if turn['turn']!=n:raise ValueError('review_turn_binding_mismatch')
            ids=[f.get('fact_id') for f in gold['required_facts']]
            if any(not isinstance(i,str) or not i for i in ids) or len(set(ids))!=len(ids):
                raise ValueError('proposal_fact_ids_invalid')
            mapping={ident:i for i,ident in enumerate(ids,1)}
            approved=turn['approved_fact_ids'];values=approved+[e['fact_id'] for e in turn['approved_evidence']]
            error=('unknown_review_fact_id' if any(not isinstance(i,str) or i not in mapping for i in values)
                   else 'duplicate_review_fact_id' if len(set(approved))!=len(approved) else None)
            if error:
                if not quarantine_invalid:raise ValueError(error)
                quarantine.append({'case_id':case['case_id'],'turn':n,'error':error});continue
            turn['approved_fact_indices']=[mapping[i] for i in turn.pop('approved_fact_ids')]
            for evidence in turn['approved_evidence']:evidence['fact_index']=mapping[evidence.pop('fact_id')]
    return canonical,{'source_representation':'opaque_fact_ids','canonical_base':1,'quarantined_turns':quarantine}


def commitment(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def _hash(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def _time(value):
    if not isinstance(value, str):
        raise ValueError('utc_timestamp_required')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError('utc_timestamp_required')
    return parsed


def validate_public_cases(cases):
    """Allow no expected, gold, grading label or source-page hints in cases."""
    if not isinstance(cases, list) or len(cases) < MIN_CASES:
        raise ValueError('at_least_200_cases_required')
    identifiers = set(); inputs = set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != {'id', 'doc_ids', 'language', 'turns', 'family_commitments'}:
            raise ValueError('public_case_fields_only')
        ident = case['id']
        if not isinstance(ident, str) or not ident or ident in identifiers:
            raise ValueError('unique_case_ids_required')
        identifiers.add(ident)
        docs, turns, families = case['doc_ids'], case['turns'], case['family_commitments']
        if (not isinstance(docs, list) or not docs
                or any(not isinstance(doc, str) or not doc for doc in docs)
                or len(set(docs)) != len(docs)):
            raise ValueError('explicit_source_selection_required')
        if case['language'] not in {'vi', 'en'}:
            raise ValueError('unsupported_language')
        if not isinstance(turns, list) or not turns or any(not isinstance(q, str) or not q.strip() for q in turns):
            raise ValueError('literal_question_turns_required')
        identity=(tuple(sorted(docs)),case['language'],tuple(' '.join(q.casefold().split()) for q in turns))
        if identity in inputs:raise ValueError('duplicate_question_not_an_additional_case')
        inputs.add(identity)
        if not isinstance(families, list) or not families or not all(_hash(x) for x in families):
            raise ValueError('source_intent_family_commitments_required')
    return identifiers


def public_request(case, turn, history):
    """Build only the actual app's question/scope/history payload, without labels.

    The collector supplies actual previous user/assistant messages in this case.
    Additional annotation fields are rejected rather than copied to inference.
    """
    if type(turn) is not int or not 0 <= turn < len(case['turns']):
        raise ValueError('invalid_turn')
    if (not isinstance(history, list) or any(not isinstance(item, dict)
            or set(item) != {'role', 'content'} or item['role'] not in {'user', 'assistant'}
            or not isinstance(item['content'], str) for item in history)):
        raise ValueError('actual_conversation_messages_only')
    if turn == 0 and history:
        raise ValueError('independent_case_must_start_without_history')
    if turn > 0 and not history:
        raise ValueError('context_turn_requires_actual_history')
    if (len(history) != 2*turn
            or any(item['role'] != ('user' if n%2==0 else 'assistant') for n,item in enumerate(history))
            or [item['content'] for item in history if item['role']=='user'] != case['turns'][:turn]):
        raise ValueError('case_history_order_or_session_mismatch')
    return inference_payload(case['turns'][turn], case['doc_ids'], history, case['language'])


def _native_status(case, prediction, chunks):
    from campusai.rag.grounding import validate_citation
    from campusai.retrieval.hybrid import RetrievalResult
    turns = prediction.get('turns')
    if (set(prediction) != {'case_id','prediction_kind','turns'}
            or prediction.get('prediction_kind') != 'real_application_http'
            or not isinstance(turns,list) or len(turns)!=len(case['turns'])):
        return 'invalid'
    history = []; provider_failure = False
    for n,turn in enumerate(turns):
        if (not isinstance(turn,dict) or set(turn)!={'http_status','request_id','request','response'}
                or type(turn.get('http_status')) is not int
                or not isinstance(turn.get('request_id'),str) or not turn['request_id']
                or turn.get('request')!=public_request(case,n,history)
                or not isinstance(turn.get('response'),dict)):
            return 'invalid'
        response=turn['response']
        failed=turn['http_status']!=200 or bool(response.get('provider_status'))
        provider_failure=provider_failure or failed
        if not failed:
            if response.get('partial') or response.get('fallback') or response_errors(response,chunks):
                return 'invalid'
            for citation in response['answer']['citations']:
                if citation['doc_id'] not in case['doc_ids']:return 'invalid'
                source=chunks.get((citation['doc_id'],citation['chunk_id']))
                if not isinstance(source,dict) or not isinstance(source.get('content'),str):return 'invalid'
                original=RetrievalResult(citation['chunk_id'],citation['doc_id'],source['page'],source['content'],
                    source.get('content_type','text'),1.,'frozen_holdout_audit',source.get('metadata',{}))
                if not validate_citation(citation,original,require_quote=True).valid:return 'invalid'
        assistant=response.get('answer');text=assistant.get('answer','') if isinstance(assistant,dict) else ''
        if not isinstance(text,str):return 'invalid'
        history.extend([{'role':'user','content':case['turns'][n]},
                        {'role':'assistant','content':text}])
    return 'provider_failure' if provider_failure else 'valid'


def score_review(cases, predictions, verdicts, protocol, *, observed_candidate_sha256,
                 isolation_receipt=None, chunks=None):
    """Fail closed; this never generates reviewer evidence or approves gold.

    `chunks` is the frozen source registry used by the existing API validator.
    The isolation receipt must have been verified outside the developing Codex
    context. Its pinned digest prevents replacing it with a later assertion.
    Local process separation or a claimed human/owner approval does not qualify.
    """
    ids = validate_public_cases(cases)
    errors = []
    required = {'version', 'candidate_sha256', 'case_manifest_sha256', 'gold_commitment',
                'frozen_at_utc', 'inference_started_at_utc', 'reviewer', 'exposed_families',
                'isolation_receipt_sha256'}
    if not isinstance(protocol, dict) or set(protocol) != required:
        raise ValueError('complete_frozen_protocol_required')
    if protocol['version'] != 1 or type(protocol['version']) is not int:
        errors.append('unsupported_protocol')
    if not _hash(protocol['candidate_sha256']) or protocol['candidate_sha256'] != observed_candidate_sha256:
        errors.append('candidate_changed_or_unpinned')
    if protocol['case_manifest_sha256'] != commitment(cases):
        errors.append('public_cases_changed')
    if not _hash(protocol['gold_commitment']):
        errors.append('gold_not_committed')
    if _time(protocol['frozen_at_utc']) >= _time(protocol['inference_started_at_utc']):
        errors.append('not_frozen_before_inference')
    exposed = protocol['exposed_families']
    if not isinstance(exposed, list) or not exposed or not all(_hash(x) for x in exposed):
        errors.append('exposure_history_missing')
    elif set(exposed) & {f for case in cases for f in case['family_commitments']}:
        errors.append('exposed_family_in_holdout')
    reviewer = protocol['reviewer']
    fields = {'kind', 'actual_model', 'author_context_id', 'review_context_id',
              'raw_author_response_sha256', 'raw_review_response_sha256', 'reviewed_gold_case_ids'}
    if (not isinstance(reviewer, dict) or set(reviewer) != fields
            or reviewer['kind'] != 'independent_ai' or not isinstance(reviewer['actual_model'],str)
            or not reviewer['actual_model'].strip()
            or not reviewer['author_context_id'] or not reviewer['review_context_id']
            or reviewer['author_context_id'] == reviewer['review_context_id']
            or not _hash(reviewer['raw_author_response_sha256'])
            or not _hash(reviewer['raw_review_response_sha256'])
            or reviewer['raw_author_response_sha256'] == reviewer['raw_review_response_sha256']
            or not isinstance(reviewer['reviewed_gold_case_ids'],list)
            or len(reviewer['reviewed_gold_case_ids'])!=len(ids)
            or any(not isinstance(ident,str) for ident in reviewer['reviewed_gold_case_ids'])
            or set(reviewer['reviewed_gold_case_ids'])!=ids):
        errors.append('independent_ai_review_receipts_missing')
    receipt = isolation_receipt
    receipt_fields = {'verified', 'gold_commitment', 'developer_gold_access', 'worker_job_identity',
                      'candidate_sha256', 'sealed_at_utc'}
    if (not isinstance(receipt, dict) or set(receipt) != receipt_fields
            or receipt['verified'] is not True or receipt['developer_gold_access'] is not False
            or not receipt['worker_job_identity'] or not _hash(protocol['isolation_receipt_sha256'])
            or commitment(receipt) != protocol['isolation_receipt_sha256']
            or receipt['candidate_sha256'] != observed_candidate_sha256
            or receipt['gold_commitment'] != protocol['gold_commitment']
            or _time(receipt['sealed_at_utc']) > _time(protocol['frozen_at_utc'])):
        errors.append('gold_isolation_unverified')
    # Extra, duplicate or missing cases are never silently discarded.
    def index(rows, key):
        if not isinstance(rows, list) or any(not isinstance(x, dict) or key not in x for x in rows):
            raise ValueError('structured_prediction_and_review_rows_required')
        result = {}
        for row in rows:
            ident = row[key]
            if not isinstance(ident, str) or ident not in ids or ident in result:
                raise ValueError('duplicate_or_unexpected_case')
            result[ident] = row
        return result
    native, review = index(predictions, 'case_id'), index(verdicts, 'case_id')
    passed = hallucinations = unsafe = uncertain = provider_failures = 0
    for case in cases:
        ident = case['id']; prediction = native.get(ident); verdict = review.get(ident)
        if prediction is None or verdict is None:
            errors.append('missing_case_prediction_or_review'); continue
        native_status = _native_status(case,prediction,chunks or {})
        valid_native = native_status=='valid'
        provider_failures += native_status=='provider_failure'
        fields = {'case_id', 'prediction_sha256', 'gold_commitment', 'all_required_facts',
                  'source_scope_correct', 'citation_grounded', 'hallucination'}
        valid_review = (set(verdict) == fields and verdict['prediction_sha256'] == commitment(prediction)
            and verdict['gold_commitment'] == protocol['gold_commitment']
            and all(type(verdict[key]) is bool for key in
                    ['all_required_facts', 'source_scope_correct', 'citation_grounded'])
            and isinstance(verdict['hallucination'],str)
            and verdict['hallucination'] in {'absent', 'detected', 'uncertain'})
        if native_status=='invalid': errors.append('native_case_incomplete_or_invalid')
        if not valid_review:
            errors.append('invalid_or_unbound_review'); continue
        hallucinations += verdict['hallucination'] == 'detected'
        uncertain += verdict['hallucination'] == 'uncertain'
        unsafe += not verdict['source_scope_correct'] or not verdict['citation_grounded']
        passed += (valid_native and verdict['all_required_facts'] and verdict['source_scope_correct']
                   and verdict['citation_grounded'] and verdict['hallucination'] == 'absent')
    accuracy = passed / len(cases)
    return {'cases': len(cases), 'passed': passed, 'failed_or_unverified': len(cases)-passed,
            'accuracy': accuracy, 'detected_hallucinations': hallucinations,
            'uncertain_hallucination_reviews': uncertain, 'scope_or_grounding_errors': unsafe,
            'provider_failure_cases': provider_failures,
            'errors': sorted(set(errors)), 'review_kind': 'independent_ai',
            'holdout_quality_pass': not errors and accuracy >= MIN_ACCURACY
                and hallucinations == unsafe == uncertain == 0,
            'overall_rag95_complete': False}


def main(argv=None):
    """Score a public worker export offline; print aggregates only, never gold.

    The bundle contains cases, native predictions, redacted verdicts, protocol
    and the candidate's file/hash map. Index chunks are loaded from disk rather
    than accepted from the review model. Run only after a frozen candidate and
    an independently verified isolation receipt exist. This command creates
    neither that receipt nor private answers and performs no network calls.
    """
    import argparse
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',type=Path,required=True)
    parser.add_argument('--isolation-receipt',type=Path,required=True)
    parser.add_argument('--index',type=Path,required=True)
    parser.add_argument('--workspace',type=Path,default=Path.cwd())
    args=parser.parse_args(argv)
    try:
        bundle=json.loads(args.bundle.read_text(encoding='utf-8'))
        if not isinstance(bundle,dict) or set(bundle)!={'cases','predictions','verdicts','protocol','candidate_files_sha256'}:
            raise ValueError('public_worker_export_required')
        validate_public_cases(bundle['cases'])
        pins=bundle['candidate_files_sha256']
        if not isinstance(pins,dict) or not pins or not all(isinstance(k,str) and _hash(v) for k,v in pins.items()):
            raise ValueError('candidate_file_pins_required')
        workspace=args.workspace.resolve();observed={};selected={doc for c in bundle['cases'] for doc in c['doc_ids']}
        def file_hash(path):
            with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
        for relative in pins:
            path=(workspace/relative).resolve()
            if Path(relative).is_absolute() or not path.is_relative_to(workspace):
                raise ValueError('candidate_file_outside_workspace')
            observed[relative]=file_hash(path)
        if observed!=pins:raise ValueError('candidate_files_changed')
        chunks={};index=args.index.resolve()
        for doc in selected:
            path=(index/doc/'bm25.json').resolve()
            if not path.is_relative_to(index) or not path.is_relative_to(workspace):
                raise ValueError('source_index_outside_frozen_workspace')
            relative=path.relative_to(workspace).as_posix()
            if relative not in pins or file_hash(path)!=pins[relative]:
                raise ValueError('source_index_not_pinned')
            for row in json.loads(path.read_text(encoding='utf-8'))['items']:
                if row['doc_id']!=doc:raise ValueError('wrong_source_in_index')
                if (doc,row['chunk_id']) in chunks:raise ValueError('duplicate_source_chunk')
                chunks[(doc,row['chunk_id'])]=row
        receipt=json.loads(args.isolation_receipt.read_text(encoding='utf-8'))
        summary=score_review(bundle['cases'],bundle['predictions'],bundle['verdicts'],bundle['protocol'],
            observed_candidate_sha256=commitment(observed),isolation_receipt=receipt,chunks=chunks)
        # Protect against a source/index rewrite while the audit was running.
        if any(file_hash(workspace/name)!=sha for name,sha in observed.items()):
            raise ValueError('candidate_changed_during_review')
        print(json.dumps(summary,ensure_ascii=False,allow_nan=False))
        return 0 if summary['holdout_quality_pass'] else 1
    except (OSError,ValueError,TypeError,KeyError):
        # Do not echo malformed worker content or paths in an exception/log.
        print(json.dumps({'holdout_quality_pass':False,'overall_rag95_complete':False,
                          'errors':['invalid_or_unverifiable_worker_export']}))
        return 1


if __name__=='__main__':
    raise SystemExit(main())
