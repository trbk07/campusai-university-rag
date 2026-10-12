"""Bounded neighboring source text for reranking short extracted fragments.

Only records already in the request-scoped candidate pool are inspected. The
original evidence bytes and citation coordinates remain unchanged.
"""
from __future__ import annotations

import hashlib

from .tokenizer_vi import source_body

VERSION = 'scoped-neighbor-context-v1'


def contextual_pool(pool):
    if len({(x['doc_id'], x['chunk_id']) for x in pool}) != len(pool):
        raise ValueError('duplicate request-scoped candidate')
    output = []
    for item in pool:
        body = source_body(item)
        section = item.get('metadata', {}).get('section_index')
        neighbors = []
        if item.get('content_type') != 'table' and len(body) <= 600 and type(section) is int:
            for direction in (-1, 1):
                matches = [x for x in pool if x['doc_id'] == item['doc_id'] and x['page'] == item['page']
                           and x.get('content_type') != 'table'
                           and x.get('metadata', {}).get('section_index') == section + direction]
                if matches:
                    neighbor = min(matches, key=lambda x: x['chunk_id'])
                    original = source_body(neighbor)
                    excerpt = original[-500:] if direction < 0 else original[:250]
                    neighbors.append((direction, neighbor, excerpt))
        context = (body + ''.join('\n\n' + ('Preceding' if direction < 0 else 'Following')
            + ' source fragment (context only):\n' + excerpt for direction, _neighbor, excerpt in neighbors)) if neighbors else item['content']
        output.append({**item, 'scoring_content': context,
            'scoring_context_version': VERSION,
            'scoring_context_sources': [{'doc_id':n['doc_id'],'chunk_id':n['chunk_id'],'page':n['page'],
                'content_sha256':hashlib.sha256(n['content'].encode()).hexdigest(),
                'excerpt_sha256':hashlib.sha256(excerpt.encode()).hexdigest()}
                for _direction,n,excerpt in neighbors]})
    return output
