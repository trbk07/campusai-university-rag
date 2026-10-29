"""Request-local citation handles; no evidence text or source IDs are rewritten."""
POLICY = 'citation-handles-v1'


class InvalidCitationHandle(ValueError):
    pass


def evidence_handles(results):
    """Derive handles from actual retrieval order, never model/evaluation labels."""
    return {identifier: f'ev{i}' for i, identifier in
            enumerate(dict.fromkeys(result.chunk_id for result in results), 1)}


def reference_context(value, handles, field=None):
    """Translate typed reference fields in system-resolved auxiliary context."""
    if isinstance(value, dict):
        return {key: reference_context(item, handles, key) for key, item in value.items()}
    if isinstance(value, list):
        return [reference_context(item, handles, field) for item in value]
    reference = isinstance(field, str) and (field in {'chunk_id', 'chunk_ids', 'citation_ids'}
                                           or field.endswith(('_chunk_id', '_chunk_ids')))
    return handles.get(value, value) if reference and isinstance(value, str) else value


def restore_citations(payload, handles):
    """Resolve only citation fields; reject foreign/full IDs and preserve extras.

    The mapping belongs to the current answer call. It is never accepted from
    model output, shared between requests, or applied to free-form text.
    """
    reverse = {handle: identifier for identifier, handle in handles.items()}
    def resolve(value):
        if not isinstance(value, str) or value not in reverse:
            raise InvalidCitationHandle('citation handle is not in the current evidence')
        return reverse[value]
    if not isinstance(payload, dict):
        return payload
    restored = dict(payload)
    if 'citations' in payload:
        if not isinstance(payload['citations'], list):
            raise InvalidCitationHandle('invalid citation list')
        citations = []
        for item in payload['citations']:
            if not isinstance(item, dict):
                raise InvalidCitationHandle('invalid citation object')
            citations.append({**item, 'chunk_id': resolve(item.get('chunk_id'))})
        restored['citations'] = citations
    if isinstance(payload.get('claims'), list):
        claims = []
        for item in payload['claims']:
            if not isinstance(item, dict):
                raise InvalidCitationHandle('invalid claim object')
            claim = dict(item)
            for field in ('citation_ids', 'citation_chunk_ids'):
                if field not in item:
                    continue
                if not isinstance(item[field], list):
                    raise InvalidCitationHandle('invalid claim citation list')
                claim[field] = [resolve(value) for value in item[field]]
            claims.append(claim)
        restored['claims'] = claims
    return restored
