"""Local-only checks for a complete, bounded textual source scope.

This reader performs no inference and sends no data. It cannot by itself
establish semantic absence. Image-bearing,
unreadable, redacted or budget-truncated sources fail closed.
"""
from __future__ import annotations

from dataclasses import dataclass
import base64
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from ..retrieval.hybrid import RetrievalResult

SCOPE_POLICY = "complete-document-source-v3"


class DocumentScopeUnavailable(ValueError):
    """The complete authorized textual scope cannot be established."""


@dataclass(frozen=True)
class CompleteDocumentScope:
    results: tuple[RetrievalResult, ...]
    documents: tuple[dict, ...]
    context_sha256: str
    pdf_documents: tuple[dict, ...] = ()

    def trace(self):
        return {"policy": SCOPE_POLICY, "documents": list(self.documents),
                "pages": sum(doc['page_count'] for doc in self.documents),
                "context_sha256": self.context_sha256,
                "coverage": ("complete_pdf_bytes_with_extracted_text_index" if self.pdf_documents
                    else "complete_extracted_text_no_image_content")}


class RegisteredDocumentScopeReader:
    """Read registered SHA256 identities only within operator-approved roots."""

    def __init__(self, store: str | Path, *, source_roots=None,
                 max_documents=4, max_pages=100, max_bytes=20 * 1024 * 1024,
                 max_context_chars=96000, allow_pdf_scope=False):
        self.store = Path(store).resolve()
        self.source_roots = tuple(Path(p).resolve() for p in
                                  (source_roots if source_roots is not None else [self.store / "uploads"]))
        for value in (max_documents, max_pages, max_bytes, max_context_chars):
            if type(value) is not int or value <= 0:
                raise ValueError("document-scope limits must be positive integers")
        self.max_documents, self.max_pages = max_documents, max_pages
        self.max_bytes, self.max_context_chars = max_bytes, max_context_chars
        if type(allow_pdf_scope) is not bool:
            raise ValueError('allow_pdf_scope must be boolean')
        self.allow_pdf_scope = allow_pdf_scope
        if allow_pdf_scope:
            self.max_documents = min(self.max_documents, 4)
            self.max_pages = min(self.max_pages, 100)
            self.max_context_chars = min(self.max_context_chars, 96000)

    def policy_identity(self):
        return {"policy": SCOPE_POLICY, "store": str(self.store),
                "source_roots": [str(p) for p in self.source_roots],
                "max_documents": self.max_documents, "max_pages": self.max_pages,
                "max_bytes": self.max_bytes, "max_context_chars": self.max_context_chars,
                "allow_pdf_scope": self.allow_pdf_scope, "max_pdf_bytes": 8 * 1024 * 1024}

    @staticmethod
    def _inside(path, roots):
        absolute = path.absolute()
        if not any(absolute.is_relative_to(root) for root in roots):
            raise DocumentScopeUnavailable("source_outside_authorized_roots")
        current = absolute
        while current != current.parent:
            if current.is_symlink() or (hasattr(current, "is_junction") and current.is_junction()):
                raise DocumentScopeUnavailable("source_link_unavailable")
            current = current.parent
        resolved = absolute.resolve()
        if not any(resolved.is_relative_to(root) for root in roots):
            raise DocumentScopeUnavailable("source_outside_authorized_roots")
        return resolved

    def read(self, doc_ids):
        import pymupdf
        from .grounding import _context_block, build_context

        if (not isinstance(doc_ids, (list, tuple)) or not doc_ids
                or any(not isinstance(d, str) or not re.fullmatch(r"[0-9a-f]{64}", d) for d in doc_ids)
                or len(doc_ids) != len(set(doc_ids)) or len(doc_ids) > self.max_documents):
            raise DocumentScopeUnavailable("document_scope_unavailable")
        try:
            registry_path = self._inside(self.store / "registry.json", [self.store])
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            results, documents, binaries, byte_count, needs_pdf = [], [], [], 0, False
            for doc_id in sorted(doc_ids):
                record = registry.get(doc_id)
                if (not isinstance(record, dict) or record.get("doc_id") != doc_id
                        or record.get("status") != "succeeded"
                        or type(record.get("page_count")) is not int or record["page_count"] < 1):
                    raise DocumentScopeUnavailable("registered_source_unavailable")
                source = self._inside(Path(record["source_path"]), self.source_roots)
                if source.suffix.lower() != ".pdf":
                    raise DocumentScopeUnavailable("registered_source_unavailable")
                if byte_count + source.stat().st_size > self.max_bytes:
                    raise DocumentScopeUnavailable("source_byte_budget_exceeded")
                with source.open("rb") as stream:
                    data = stream.read(self.max_bytes - byte_count + 1)
                byte_count += len(data)
                if byte_count > self.max_bytes or hashlib.sha256(data).hexdigest() != doc_id:
                    raise DocumentScopeUnavailable("source_hash_mismatch")
                with pymupdf.open(stream=data, filetype="pdf") as pdf:
                    if (pdf.needs_pass or pdf.embfile_count() or len(pdf) != record["page_count"]
                            or sum(doc['page_count'] for doc in documents) + len(pdf) > self.max_pages):
                        raise DocumentScopeUnavailable("source_page_scope_unavailable")
                    visual_pages, blank_text_pages = [], []
                    for number, page in enumerate(pdf, 1):
                        text = page.get_text()
                        # Resource dictionaries omit inline images and may
                        # retain images that are never displayed. Inspect the
                        # actual page display, including inline image content.
                        visual = bool(page.get_image_info() or page.get_drawings())
                        if visual: visual_pages.append(number)
                        if not text.strip(): blank_text_pages.append(number)
                        if not text.strip() or visual:
                            if not self.allow_pdf_scope:
                                raise DocumentScopeUnavailable("source_text_coverage_incomplete")
                            needs_pdf = True
                        if not text.strip():
                            continue  # Covered by PDF bytes, never fabricated as citation text.
                        result = RetrievalResult(f"{doc_id}_physical_page_{number}", doc_id, number,
                            text, "text", 1.0, "complete_document_scope",
                            {"source_name": source.name, "source_hash": doc_id,
                             "page_range": [number, number], "heading_path": [f"PDF page {number}"]})
                        normalize = lambda s: " ".join(unicodedata.normalize("NFC", s).split())
                        if normalize(_context_block(result)[1]) != normalize(text):
                            raise DocumentScopeUnavailable("source_text_redacted")
                        results.append(result)
                    documents.append({"doc_id": doc_id, "source_name": source.name,
                                      "source_sha256": doc_id, "page_count": len(pdf)})
                    if visual_pages or blank_text_pages:
                        documents[-1].update(visual_pages=visual_pages, blank_text_pages=blank_text_pages)
                    if self.allow_pdf_scope:
                        binaries.append((doc_id, data))
            if not results:
                raise DocumentScopeUnavailable('source_text_index_unavailable')
            if needs_pdf and byte_count > 8 * 1024 * 1024:
                raise DocumentScopeUnavailable('source_pdf_byte_budget_exceeded')
            context = build_context(results, self.max_context_chars)
            full = "\n\n".join(header + content for r in results for header, content in [_context_block(r)])
            if context != full:
                raise DocumentScopeUnavailable("complete_source_context_budget_exceeded")
            pdf_documents = tuple({'sha256':identity, 'data':base64.b64encode(data).decode('ascii')}
                for identity,data in binaries) if needs_pdf else ()
            return CompleteDocumentScope(tuple(results), tuple(documents),
                hashlib.sha256(context.encode()).hexdigest(), pdf_documents)
        except DocumentScopeUnavailable:
            raise
        except (OSError, ValueError, TypeError, KeyError, AttributeError, RuntimeError) as error:
            raise DocumentScopeUnavailable("registered_source_unavailable") from error
