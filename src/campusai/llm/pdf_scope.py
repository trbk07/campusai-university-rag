"""Bounded, hash-checked PDF request parts; no network or source-path access."""
from __future__ import annotations

import base64
import hashlib
import json
import re


MAX_PDF_BYTES = 8 * 1024 * 1024
MAX_PDF_PAGES = 100
MAX_PDF_DOCUMENTS = 4


def body_hash(body: dict) -> str:
    return hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def pdf_parts(documents):
    """Verify actual binary identity/page counts instead of caller estimates."""
    import pymupdf
    if (not isinstance(documents, (list, tuple)) or not documents
            or len(documents) > MAX_PDF_DOCUMENTS):
        raise ValueError('invalid bounded PDF scope')
    parts, seen, total_bytes, total_pages = [], set(), 0, 0
    for item in documents:
        if (not isinstance(item, dict) or set(item) != {'sha256', 'data'}
                or not isinstance(item['sha256'], str)
                or not re.fullmatch(r'[0-9a-f]{64}', item['sha256'])
                or item['sha256'] in seen or not isinstance(item['data'], str)
                or len(item['data']) > ((MAX_PDF_BYTES + 2) // 3) * 4):
            raise ValueError('invalid PDF identity or encoding')
        data = base64.b64decode(item['data'], validate=True)
        total_bytes += len(data)
        if (total_bytes > MAX_PDF_BYTES or not data.startswith(b'%PDF-')
                or hashlib.sha256(data).hexdigest() != item['sha256']):
            raise ValueError('PDF identity or byte budget mismatch')
        with pymupdf.open(stream=data, filetype='pdf') as pdf:
            if pdf.needs_pass or pdf.embfile_count():
                raise ValueError('encrypted or embedded-file PDF scope unavailable')
            total_pages += len(pdf)
            if not len(pdf) or total_pages > MAX_PDF_PAGES:
                raise ValueError('PDF page scope exceeded')
        seen.add(item['sha256'])
        parts.append({'inlineData': {'mimeType': 'application/pdf', 'data': item['data']}})
    return parts


def measured_budget(body, measured_tokens):
    """Bind measured input to this full request and retain text/output guards."""
    from .quota import estimate_gemini_tokens
    if type(measured_tokens) is not int or not 0 < measured_tokens <= 1_000_000_000:
        raise ValueError('invalid provider token measurement')
    text_body = json.loads(json.dumps(body, allow_nan=False))
    for content in text_body.get('contents', []):
        content['parts'] = [part for part in content.get('parts', []) if 'inlineData' not in part]
    text_input, output = estimate_gemini_tokens(text_body)
    # Measurement is advisory: keep framing headroom and reconcile upwards
    # from actual generation usage through the existing durable governor.
    return max(text_input, measured_tokens + max(1024, measured_tokens // 10)), output
