"""Bounded original-source excerpts for an explicitly degraded response.

This performs no synthesis or translation and makes no claim that the excerpt
answers the question. Every quote is verified against its request-scoped chunk.
"""
import json
import re

from ..retrieval.tokenizer_vi import source_body
from .grounding import Citation, validate_citation


STOP_WORDS = frozenset('what which when where does from with this that have should '
                      'the and for are how why của các những được trong theo nào '
                      'thế một này làm khi là hay tài liệu'.split())


def _terms(question):
    return {word.casefold() for word in re.findall(r'\w{3,}', question)
            if word.casefold() not in STOP_WORDS}


def _score(text, terms):
    words = set(re.findall(r'\w{3,}', text.casefold()))
    return len(words & terms)


def _quote(result, terms, limit=900):
    body = source_body({'content': result.content}, decode_tables=False).strip()
    if result.content_type == 'table':
        start = body.find('{"headers"')
        if start < 0:
            return ''
        try:
            table = json.loads(body[start:])
        except (TypeError, ValueError):
            return ''
        rows = table.get('rows', []) if isinstance(table, dict) else []
        options = [json.dumps(row, ensure_ascii=False) for row in rows
                   if isinstance(row, list) and row and all(isinstance(v, str) for v in row)]
        options = [quote for quote in options if len(quote) <= limit]
        return max(options, key=lambda quote: _score(quote, terms), default='')
    if len(body) <= limit:
        return body
    # Windows remain contiguous in the original text. Never splice sentences
    # from separate locations or turn a translated paraphrase into a quote.
    matches = [m for m in re.finditer(r'\w{3,}', body) if m.group().casefold() in terms]
    offsets = [0, *(max(0, m.start()-160) for m in matches)]
    start = max(offsets, key=lambda offset: _score(body[offset:offset+limit], terms))
    if start:
        boundary = body.find('\n', start, min(len(body), start+160))
        start = boundary+1 if boundary >= 0 else start
    end = min(len(body), start+limit)
    if end < len(body):
        boundary = body.rfind('\n', start+limit//2, end)
        end = boundary if boundary >= 0 else body.rfind(' ', start, end)
    return body[start:end].strip()


def source_excerpts(question, results, *, maximum=3):
    terms, excerpts, seen = _terms(question), [], set()
    for result in results:
        quote = _quote(result, terms)
        if not quote or quote in seen:
            continue
        raw = {'chunk_id': result.chunk_id, 'page': result.page, 'quote': quote}
        if result.metadata.get('table_id') is not None:
            raw['table_id'] = result.metadata['table_id']
        if not validate_citation(raw, result, require_quote=True).valid:
            continue
        citation = Citation(result.chunk_id, result.doc_id, result.page, quote,
            ' > '.join(result.metadata.get('heading_path', [])),
            str(result.metadata.get('source_name', '')),
            tuple(result.metadata.get('page_range', [result.page, result.page])),
            str(result.metadata.get('table_id', ''))).to_dict()
        citation.pop('source_hash', None)
        excerpts.append(citation)
        seen.add(quote)
        if len(excerpts) == maximum:
            break
    return excerpts
