"""Local MVP document transport; core ingestion/retrieval remain authoritative.

The default host is single-user. Trusted middleware may narrow every operation
with campusai.authorized_doc_ids. Client payloads never grant permissions.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import threading
import time
import uuid
from collections import OrderedDict
from contextlib import contextmanager
from pathlib import Path

from .documents.registry import DocumentRegistry
from .ingestion.pipeline import delete_document_full
from .ingestion.docling_parser import visible_page_text
from .ingestion.validate import validate_pdf
from .ingestion.jobs import JobQueueFull, JobStoreUnavailable


class WebError(ValueError):
    def __init__(self, code: str, status: int = 400, retry_after_seconds=None):
        self.code, self.status = code, status
        self.retry_after_seconds = retry_after_seconds
        super().__init__(code)


class CorpusAccessLock:
    """Allow parallel read-only queries while keeping corpus changes exclusive.

    Writers take priority once queued, so a stream of questions cannot starve
    document deletion. Index publication itself remains per-document atomic.
    """

    def __init__(self):
        self._condition = threading.Condition()
        self._readers = 0
        self._writer = False
        self._waiting_writers = 0

    @contextmanager
    def read(self):
        with self._condition:
            while self._writer or self._waiting_writers:
                self._condition.wait()
            self._readers += 1
        try:
            yield
        finally:
            with self._condition:
                self._readers -= 1
                if not self._readers:
                    self._condition.notify_all()

    @contextmanager
    def write(self):
        with self._condition:
            self._waiting_writers += 1
            try:
                while self._writer or self._readers:
                    self._condition.wait()
                self._writer = True
            finally:
                self._waiting_writers -= 1
        try:
            yield
        finally:
            with self._condition:
                self._writer = False
                self._condition.notify_all()

    @property
    def busy(self):
        with self._condition:
            return bool(self._readers or self._writer or self._waiting_writers)


def contained(root: Path, path: Path) -> Path:
    """Reject symlinks and junction escapes, including intermediate parents."""
    root = Path(root).absolute()
    absolute = path.absolute()
    try:
        relative = absolute.relative_to(root)
        current = root
        for part in relative.parts:
            current = current / part
            if current.is_symlink() or (hasattr(current, "is_junction") and current.is_junction()):
                raise ValueError
        # Resolve both sides at the same time. On Windows an existing child may
        # resolve to an extended ``\\?\`` path while the root was resolved
        # before its directory existed; comparing those mixed forms rejects a
        # safe path during simultaneous first uploads.
        resolved_root = str(root.resolve())
        resolved_path = absolute.resolve()
        resolved = str(resolved_path)
        if os.name == "nt":
            # pathlib may return an extended path for an existing file while a
            # just-created directory still resolves as a drive path.
            def comparable(value):
                if value.startswith("\\\\?\\UNC\\"):
                    value = "\\\\" + value[8:]
                elif value.startswith("\\\\?\\"):
                    value = value[4:]
                return os.path.normcase(value)
            resolved_root, resolved = comparable(resolved_root), comparable(resolved)
        Path(resolved).relative_to(Path(resolved_root))
        return resolved_path
    except ValueError as error:
        raise WebError("not_found", 404) from error


class WebDocuments:
    def __init__(self, application):
        self.application = application
        defaults = getattr(application, "ingestion_defaults", {})
        self.store = Path(defaults.get("store_dir", "data/store")).resolve()
        configured_index = defaults.get("index_dir", getattr(getattr(application.query_service, "retriever", None), "index_root", None))
        self.index = Path(configured_index).resolve() if configured_index is not None else None
        self.uploads = self.store / "uploads"
        self.max_mb = int(defaults.get("max_mb", 50))
        self.max_pages = int(defaults.get("max_pages", 218))
        self.lock = threading.RLock()
        self._registry = None
        # Queries share a read lease. Deletes retain an exclusive lease so a
        # source cannot disappear while an answer is being grounded.
        self.corpus_lock = CorpusAccessLock()
        self.responses: dict[str, tuple[float, set[str]]] = {}
        self._legacy_coverage = {}
        self._thumbnail_cache = OrderedDict()
        from .web_deletions import DocumentDeletions
        self.deletions = DocumentDeletions(self)
        self._ocr_upgrade_thread = None
        if (getattr(application, 'jobs', None) is not None and defaults.get('enable_ocr')
                and defaults.get('progressive_ocr') and (self.store / 'registry.json').is_file()):
            # Existing uploads need the same automatic workflow as new ones.
            # Never make a GET request start processing or re-upload the PDF.
            self._ocr_upgrade_thread = threading.Thread(target=self._resume_legacy_ocr,
                name='campusai-ocr-upgrade', daemon=True)
            self._ocr_upgrade_thread.start()

    def _resume_legacy_ocr(self):
        def eligible(record):
            return (record.get('status') == 'review_required'
                and record.get('review_reason') in {'ocr_required', 'ocr_unavailable'}
                and 'coverage_complete' not in record.get('metadata', {}))
        try:
            candidates = [r['doc_id'] for r in self.registry.metadata_list() if eligible(r)]
        except (OSError, ValueError):
            return
        for doc_id in candidates:
            if not re.fullmatch('[0-9a-f]{64}', doc_id):
                continue
            while True:
                try:
                    with self.deletions.file_lock(doc_id), self.lock:
                        record = self.record(doc_id, {})
                        latest = self.latest_jobs_snapshot().get(doc_id)
                        # Preserve explicit cancellation, failures and crash
                        # recovery. Do not retry work already attempted here.
                        if (not eligible(record) or latest is not None
                                and latest['state'] not in {'succeeded', 'review_required'}):
                            break
                        source = self.source(doc_id, {})
                        self.application.jobs.submit(source, expected_sha256=doc_id,
                            reprocess_review=True, **self.application.ingestion_defaults)
                    break
                except JobQueueFull:
                    # Wait for capacity, without creating jobs or discarding
                    # the remaining documents. Shutdown makes submit fail.
                    threading.Event().wait(.25)
                except JobStoreUnavailable:
                    return
                except (OSError, ValueError):
                    break

    @property
    def registry(self):
        with self.lock:
            contained(self.store, self.store / "registry.json")
            if self._registry is None:
                self._registry = DocumentRegistry(self.store / "registry.json")
            return self._registry

    @staticmethod
    def allowed(doc_id, environ):
        scope = environ.get("campusai.authorized_doc_ids")
        return scope is None or doc_id in scope

    def record(self, doc_id, environ):
        if not re.fullmatch(r"[0-9a-f]{64}", doc_id) or not self.allowed(doc_id, environ):
            raise WebError("not_found", 404)
        if doc_id in self.deletions.pending:
            raise WebError('document_deleting', 409)
        record = self.registry.metadata_get(doc_id)
        if record is None:
            raise WebError("not_found", 404)
        return record

    def public_document(self, record, *, latest_job=...):
        doc_id = record["doc_id"]
        source = Path(record["source_path"])
        # Only a server-managed upload can be downloaded, even if a historical
        # registry happens to contain an arbitrary local path.
        available = False
        try:
            source = contained(self.store, source)
            available = source.parent == self.uploads / doc_id and source.suffix.lower() == ".pdf" and source.is_file()
        except WebError:
            pass
        meta = record.get("metadata", {})
        unread = list(meta.get('unread_pages', []))
        # Older indexes may have silently skipped image-only pages in mixed
        # PDFs. Audit their immutable local source once, without re-embedding
        # already readable native PDFs or trusting an old success flag.
        from .ingestion.docling_parser import TEXT_COVERAGE_VERSION
        if (available and record.get('status') == 'succeeded'
                and meta.get('text_coverage_version') != TEXT_COVERAGE_VERSION):
            stat = source.stat()
            identity = (stat.st_mtime_ns, stat.st_size)
            cached = self._legacy_coverage.get(doc_id)
            if cached is None or cached[0] != identity:
                from .ingestion.docling_parser import parse_pdf
                # Historical successful OCR already covered its recorded physical
                # pages. Re-audit the remaining pages for newly detected hybrids.
                recognized = set((meta.get('ocr') or {}).get('page_numbers', []))
                unread = [page['page'] for page in parse_pdf(source)
                          if (meta.get('text_coverage_version') != 3
                              and page.get('ignored_invisible_spans'))
                          or page.get('untrusted_native_mapping')
                          or page.get('requires_ocr') and page['page'] not in recognized]
                self._legacy_coverage[doc_id] = (identity, unread)
            else:
                unread = cached[1]
        partial = record.get('status') == 'partial' and meta.get('coverage_complete') is False and bool(meta.get('readable_pages'))
        ready = (record.get("status") == "succeeded" or partial) and self.index is not None and all(
            contained(self.index, self.index / doc_id / name).is_file() for name in ("bm25.json", "dense.json"))
        deleting = doc_id in self.deletions.pending
        ready = ready and (not unread or partial) and not deleting
        safe_meta = {key: meta[key] for key in ("document_type", "academic_year", "program", "university", "version", "semester")
                     if isinstance(meta.get(key), (str, int))}
        if latest_job is ...:
            latest_job = self.latest_jobs_snapshot().get(doc_id)
        if latest_job is not None and not latest_job.get('ready'):
            ready = False
        return {"doc_id": doc_id, "name": source.name, "page_count": record.get("page_count", 0),
                "deleting": deleting, "delete_failed": doc_id in self.deletions.failed,
                "metadata": safe_meta, "ready": ready, "status": "partial" if partial and ready else "review_required" if unread else "ready" if ready else record.get("status", "review_required"),
                "review_reason": 'ocr_required' if unread else record.get('review_reason'),
                "unread_pages": unread,
                "readable_pages": meta.get('readable_pages', []),
                "coverage_complete": not bool(unread),
                "ocr_available": self.application.jobs is not None and available and not ready and not deleting
                    and bool(unread or record.get('review_reason') in {'ocr_required','ocr_unavailable'}),
                "file_available": available, "size_bytes": source.stat().st_size if available else None,
                "uploaded_at": source.stat().st_mtime if available else None}

    def latest_jobs_snapshot(self, rows=None):
        latest_jobs = {}
        rows = self.application.jobs_snapshot()['jobs'] if rows is None else rows
        for job in rows:
            doc_id = job.get('document_id') or Path(job['source_path']).parent.name
            current = latest_jobs.get(doc_id)
            if current is None or (job['created_at'],job.get('retry_count',0)) > (
                    current['created_at'],current.get('retry_count',0)):
                latest_jobs[doc_id] = job
        return latest_jobs

    def documents(self, environ, *, job_rows=None, doc_ids=None):
        latest_jobs = self.latest_jobs_snapshot(job_rows)
        wanted = None if doc_ids is None else set(doc_ids)
        records = [self.public_document(record, latest_job=latest_jobs.get(record['doc_id']))
                   for record in self.registry.metadata_list(doc_ids=wanted) if self.allowed(record["doc_id"], environ)
                   and (wanted is None or record['doc_id'] in wanted)]
        return sorted(records, key=lambda record: record.get("uploaded_at") or 0, reverse=True)

    def named_query_scope(self, question, options, source_documents):
        """Honor explicit PDF-source phrases before retrieval/model inference.

        This only narrows the already authorized, ready source list. A filename
        mentioned as document content is not automatically a source selection.
        """
        if not isinstance(question, str) or not source_documents:
            return source_documents, None
        import unicodedata
        from .document_info import match_pdf_names, folded
        from .rag.context import resolve_query
        resolved = resolve_query(question, history=options.get('history'), selected_text=options.get('selected_text'),
                                 requires_context=options.get('requires_context', False))
        known = sorted({unicodedata.normalize('NFC', doc['name']) for doc in source_documents}
                       | {folded(doc['name']) for doc in source_documents}, key=len, reverse=True)
        filename = '(?:' + '|'.join(re.escape(name) for name in known) + r'|[\w .-]{1,160}?\.pdf)(?![\w-]|\.\w)'
        prefix = r'\b(?:trong|theo|từ|tu|ở|o|còn|con|what\s+about|in|from|according\s+to|using|use(?:\s+only)?)\s+(?:(?:the|uploaded|file|pdf|document|tài\s+liệu|tai\s+lieu|tep|tệp)\s+)*["\x27`“]?'
        pattern = re.compile(prefix + filename + r'(?:["\x27`”]?\s*(?:,|và|va|and|với|voi|&)\s*["\x27`“]?' + filename + r')*', re.I)
        negative = False
        def references(text):
            nonlocal negative
            raw = unicodedata.normalize('NFC', text)
            matches = list(pattern.finditer(raw))
            negative |= any(re.search(r'\b(?:not|don t|do not|khong|dung)\s*(?:read|use|lay|doc)?\s*$',
                                     re.sub(r'[^\w\s]', ' ', folded(raw[max(0,match.start()-40):match.start()]))) for match in matches)
            return [match.group() for match in matches]
        fragments = references(resolved.raw)
        if not fragments and resolved.contextual:
            fragments = references(resolved.resolved)
        comparison = re.search(r'\b(?:so sanh|compare|comparison|difference between)\b', folded(resolved.raw))
        names = match_pdf_names(resolved.raw if comparison else '\n'.join(fragments), source_documents)
        if not fragments and not (comparison and names.mentioned):
            return source_documents, None
        if names.mentioned and not names.ambiguous and not names.unknown and not negative:
            selected = {doc['doc_id'] for doc in names.documents}
            options['doc_ids'] = sorted(selected)
            return [doc for doc in source_documents if doc['doc_id'] in selected], None
        from .rag.grounding import GroundedAnswer
        self.application.query_service.reset_request_state()
        english = options.get('language', 'vi') == 'en'
        message = ('The PDF name is missing or ambiguous within the selected sources. Select the intended PDF or give its exact name.'
                   if english else 'Chưa xác định đúng PDF trong các nguồn đang chọn. Hãy chọn riêng tài liệu cần hỏi hoặc ghi đúng tên file.')
        message += '\n' + '\n'.join('- ' + doc['name'] for doc in source_documents[:6])
        answer = GroundedAnswer(message, (), 'low', True, reason='ambiguous_question', evidence_status='ambiguous')
        return source_documents, {'ok':True, 'answer':answer.to_public_dict(), 'cache_hit':False}

    def answer_document_info(self, question, options, environ, *, metadata_only=False, source_documents=None):
        from .document_info import document_info_response
        # Ordinary content queries must not enumerate the upload registry or
        # introduce document-transport dependencies into core API adapters.
        if not isinstance(question, str) or not re.search(
                r'(?:trang|pages?|page\s+count)', question, re.I):
            return None
        from .rag.context import resolve_query, authorized_scope
        from .retrieval.contracts import validate_filters
        resolve_query(question, history=options.get('history'), selected_text=options.get('selected_text'),
                      requires_context=options.get('requires_context',False))
        ids = authorized_scope(options.get('doc_ids'), options.get('authorized_doc_ids'))
        source_documents = self.documents(environ, doc_ids=ids) if source_documents is None else source_documents
        selected = [d for d in source_documents if d['ready'] and (ids is None or d['doc_id'] in ids)]
        filters = validate_filters(options.get('filters'))
        selected = [d for d in selected if all(str(d['metadata'].get(k, '')).casefold() == str(v).casefold()
                                             for k, v in filters.items())]
        response = document_info_response(question, selected, options.get('language', 'vi'))
        if response is not None:
            resolve_query(question, history=options.get('history'), selected_text=options.get('selected_text'),
                          requires_context=options.get('requires_context', False))
            self.application.query_service.reset_request_state()
            return response
        if metadata_only:
            return None
        # Split only independent explicit clauses. Keep the original question
        # intact when no structural PDF question is present in a component.
        clauses = [p.strip() for p in re.split(r'\?+\s*|;\s*|\s+(?:và|and)\s+', question, flags=re.I) if p.strip()]
        if len(clauses) == 2:
            for index,clause in enumerate(clauses):
                info = document_info_response(clause, selected, options.get('language','vi'))
                if info is None:
                    continue
                if info['answer']['abstained']:
                    return info
                content = self.answer_document_info(clauses[1-index],options,environ,source_documents=source_documents)
                if content is None:
                    content = self.application.query(clauses[1-index], **options)
                if not content.get('ok'):
                    visible = dict(info['answer'])
                    visible['answer'] += '\n' + ('AI is temporarily unavailable for the remaining question.'
                        if options.get('language') == 'en' else 'AI tạm thời chưa trả lời được phần nội dung còn lại.')
                    visible.update(schema_version='document-composite-v1',abstained=True,confidence='low')
                    return {'ok':True,'answer':visible,'document_info':info['document_info'],
                        'cache_hit':False,'partial':True,'provider_status':content,
                        'parts':[{'kind':'document_info','response':info['answer']},
                                 {'kind':'grounded_answer','response':content}]}
                answer = dict(content['answer'])
                answer['answer'] = info['answer']['answer'] + '\n\n' + answer['answer']
                answer['schema_version'] = 'document-composite-v1'
                return {'ok':True, 'answer':answer, 'cache_hit':content.get('cache_hit',False),
                    'partial':bool(content['answer'].get('abstained')),
                    'document_info':info['document_info'], 'parts':[
                        {'kind':'document_info','response':info['answer']},
                        {'kind':'grounded_answer','response':content['answer']}]}
        from .rag.page_queries import page_intervals
        if page_intervals(question):
            return self.answer_physical_pages(question, selected, options, environ)
        return None

    def answer_physical_pages(self, question, selected, options, environ):
        from .document_info import folded, document_info_response
        from .rag.context import resolve_query
        from .rag.page_queries import select_physical_pages
        from .retrieval.hybrid import RetrievalResult
        resolved = resolve_query(question, history=options.get('history'), selected_text=options.get('selected_text'),
                                 requires_context=options.get('requires_context',False))
        service = self.application.query_service
        service.reset_request_state()
        named = [doc for doc in selected if re.search(r'(?<!\w)'+re.escape(folded(doc['name']))+r'(?!\w)',folded(question))]
        unnamed = folded(question)
        for doc in named:
            unnamed = unnamed.replace(folded(doc['name']),' ')
        if re.search(r'(?<!\w)[\w.-]+\.pdf\b',unnamed):
            info = document_info_response('number of pages',[],options.get('language','vi'))
            info['answer']['answer'] = ('Không tìm thấy PDF có tên được hỏi trong tài liệu đã chọn.'
                if options.get('language','vi') == 'vi' else 'That PDF name is not in the selected documents.')
            return info
        if named:
            selected = named
        # A physical page belongs to the named/remembered source, not whichever
        # selected PDF happens to rank first. Resolve within authorization before
        # asking for a filename; scan/image labels are not institution choices.
        if hasattr(service, '_institution_request') and hasattr(service, '_temporal_documents'):
            documents = service._temporal_documents([d['doc_id'] for d in selected], options.get('filters'))
            institution = service._institution_request(resolved.resolved, documents, resolved.history)
            if institution.needs_clarification:
                from .rag.grounding import GroundedAnswer
                answer = GroundedAnswer(institution.clarification(options.get('language','vi')),(), 'low',True,
                                        reason='ambiguous_question',evidence_status='ambiguous')
                return {'ok':True,'answer':answer.to_public_dict(),'cache_hit':False}
            if institution.doc_ids:
                selected = [d for d in selected if d['doc_id'] in institution.doc_ids]
        info = document_info_response('total number of pages', selected, options.get('language','vi'))
        if len(selected) != 1:
            info['answer'].update(answer='Bạn muốn hỏi trang của PDF nào?' if options.get('language','vi') == 'vi'
                                 else 'Which selected PDF do these pages belong to?', abstained=True, confidence='low')
            info['document_info']['needs_clarification'] = True
            return info
        doc = selected[0]
        pages, problem = select_physical_pages(question, doc['page_count'])
        if problem:
            info['document_info']['kind'] = problem
            info['document_info']['needs_clarification'] = True
            message = (f"PDF {doc['name']} có {doc['page_count']} trang. " if options.get('language','vi') == 'vi'
                       else f"PDF {doc['name']} has {doc['page_count']} pages. ")
            message += (('Hãy chọn trang hợp lệ và tối đa 12 trang mỗi lượt.' if options.get('language','vi') == 'vi'
                         else 'Choose a valid range of at most 12 pages.') )
            info['answer'].update(answer=message, abstained=True, confidence='low')
            return info
        import fitz
        with fitz.open(stream=self.source_bytes(doc['doc_id'],environ), filetype='pdf') as pdf:
            if len(pdf) != doc['page_count']:
                raise WebError('source_unavailable',404)
            results = [RetrievalResult(f"{doc['doc_id']}_physical_page_{page}",doc['doc_id'],page,
                visible_page_text(pdf[page-1]), 'text',1.0,'source_pages',
                {'source_name':doc['name'],'source_hash':doc['doc_id'],'page_range':[page,page],
                 'heading_path':[f'PDF page {page}']}) for page in pages]
        # Reuse the already-ingested per-page OCR, retaining the exact physical
        # page boundary. Never OCR the file again on every chat question, and
        # never use text from another page to fill an unreadable requested page.
        parsed = {}
        if any(not r.content.strip() for r in results):
            try:
                parsed_path = contained(self.store, self.store / doc['doc_id'] / 'parsed.md')
                with parsed_path.open('rb') as stream:
                    data = stream.read(4 * 1024 * 1024 + 1)
                if len(data) <= 4 * 1024 * 1024:
                    blocks = re.split(r'(?m)^## Page (\d+)\s*\n', data.decode('utf-8'))
                    numbers = [int(n) for n in blocks[1::2]]
                    if len(numbers) == len(set(numbers)) and all(1 <= n <= doc['page_count'] for n in numbers):
                        readable = set(doc.get('readable_pages', []))
                        if not readable:
                            # Non-progressive ingestion records OCR pages but
                            # predates the progressive readable-pages field.
                            # Reuse only its current, complete source-bound OCR;
                            # an explicit empty/partial list must stay unreadable.
                            from .ingestion.docling_parser import TEXT_COVERAGE_VERSION
                            record = self.record(doc['doc_id'], environ)
                            metadata = record.get('metadata', {})
                            if ('readable_pages' not in metadata
                                    and record.get('status') == 'succeeded'
                                    and doc.get('ready') and doc.get('coverage_complete') is True
                                    and metadata.get('coverage_complete') is not False
                                    and metadata.get('text_coverage_version') == TEXT_COVERAGE_VERSION):
                                ocr = metadata.get('ocr')
                                recognized = ocr.get('page_numbers') if isinstance(ocr, dict) else None
                                if (isinstance(recognized, list)
                                        and all(type(n) is int and 1 <= n <= doc['page_count'] for n in recognized)
                                        and len(recognized) == len(set(recognized))):
                                    readable = set(recognized)
                        parsed = {int(n):text.strip() for n,text in zip(blocks[1::2],blocks[2::2])
                                  if int(n) in readable}
            except (OSError, ValueError, WebError):
                parsed = {}
        from dataclasses import replace
        results = [replace(r, content=parsed[r.page]) if not r.content.strip() and parsed.get(r.page,'').strip()
                   else r for r in results]
        if any(not r.content.strip() for r in results):
            info['answer'].update(answer='Một số trang chỉ có ảnh hoặc chưa đọc được chữ; cần OCR trước khi trả lời.'
                if options.get('language','vi') == 'vi' else 'Some pages have no readable text and require OCR.',
                abstained=True,confidence='low')
            info['document_info']['kind'] = 'page_text_unavailable'
            return info
        table_reader=getattr(service,'source_page_tables',None)
        if callable(table_reader):
            # Keep headed cells next to their exact physical page text. This
            # preserves code/credit relationships lost by plain PDF extraction.
            results=table_reader(question,doc['doc_id'],pages)+results
        answer = service.ask_source_pages(question,results,language=options.get('language','vi'),
            history=options.get('history'),selected_text=options.get('selected_text'),
            requires_context=options.get('requires_context',False))
        if answer.reason == 'llm_error':
            return {'ok':False, **(answer.provider_failure or {'error_code':'provider_unavailable'})}
        return {'ok':True,'answer':answer.to_public_dict(),'cache_hit':service.last_cache_hit}

    def public_job(self, job, environ, *, _validated_source=None):
        if not job:
            raise WebError("not_found", 404)
        source = _validated_source if _validated_source is not None else contained(self.store, Path(job["source_path"]))
        doc_id = job.get("document_id") or source.parent.name
        if not self.allowed(doc_id, environ):
            raise WebError("not_found", 404)
        fields = ("job_id", "state", "stage", "progress", "document_id", "ready", "retryable",
                  "created_at", "updated_at", "ingestion_status", "index_status")
        value = {key: job.get(key) for key in fields}
        value["name"] = source.name
        value['deleting'] = doc_id in self.deletions.pending
        value['delete_failed'] = doc_id in self.deletions.failed
        value["error_code"] = ("processing_interrupted" if job.get('error_code')=='processing_interrupted' else
                               "processing_failed" if job.get("state") == "failed" else None)
        return value

    def jobs(self, environ, *, job_rows=None):
        values = []
        validated_sources = {}
        job_rows = self.application.jobs_snapshot()["jobs"] if job_rows is None else job_rows
        for job in job_rows:
            try:
                # History often contains multiple jobs for the same source.
                # Reuse path validation only inside this metadata response;
                # every row still checks authorization, and actions validate anew.
                path = job['source_path']
                if path not in validated_sources:
                    validated_sources[path] = contained(self.store, Path(path))
                values.append(self.public_job(job, environ, _validated_source=validated_sources[path]))
            except WebError:
                continue
        return values

    def upload(self, data, name, environ):
        digest = hashlib.sha256(data).hexdigest()
        with self.deletions.file_lock(digest):
            with self.lock:
                if digest in self.deletions.pending:
                    raise WebError('document_deleting', 409)
            return self._upload(data, name, environ)

    def _needs_ocr_upgrade(self, record):
        defaults = self.application.ingestion_defaults
        ocr = record.get('metadata', {}).get('ocr')
        if not (defaults.get('enable_ocr') and defaults.get('ocr_backend') == 'tesseract' and isinstance(ocr, dict)):
            return False
        from .ingestion.tesseract_worker import RENDER_POLICY
        identity = ocr.get('model_identity')
        return (ocr.get('backend') != 'tesseract' or not isinstance(identity, dict)
                or identity.get('render_policy') != RENDER_POLICY)

    def _upload(self, data, name, environ):
        if "campusai.authorized_doc_ids" in environ:
            # Assignment of a new document to a user requires real ownership
            # middleware; a caller cannot self-extend a trusted allowlist.
            raise WebError("upload_scope_unavailable", 403)
        if self.application.jobs is None:
            raise WebError("jobs_not_configured", 503)
        if len(data) > self.max_mb * 1024 * 1024:
            raise WebError("upload_too_large", 413)
        if not data.startswith(b"%PDF-") or not name.lower().endswith(".pdf"):
            raise WebError("invalid_pdf")
        name = re.sub(r"[^\w .()-]", "_", name.replace("\\", "/").split("/")[-1])
        name = (name[:-4][:156] or 'document')+name[-4:]
        digest = hashlib.sha256(data).hexdigest()
        directory = contained(self.store, self.uploads / digest)
        source = contained(self.store, directory / name)
        existing = self.registry.get(digest)
        if existing and self.public_document(existing)['ready'] and not self._needs_ocr_upgrade(existing):
            return {"ok": True, "document": self.public_document(existing), "duplicate": True}
        previous = next((job for job in self.application.jobs_snapshot()["jobs"]
                         if Path(job["source_path"]).parent == directory and job["state"] in {"staging","queued","running"}), None)
        if previous:
            return {"ok": True, "job": self.public_job(previous, environ), "duplicate": True}
        try:
            job_id,created = self.application.jobs.prepare_upload(source,digest,**self.application.ingestion_defaults)
        except JobQueueFull:
            raise WebError('ingestion_busy',429,2) from None
        except JobStoreUnavailable:
            raise WebError('job_store_unavailable',503) from None
        if not created:
            return {'ok':True,'job':self.public_job(self.application.jobs.get(job_id),environ),'duplicate':True}
        # Durable intent and capacity admission precede every upload file.
        temporary = contained(self.store,Path(self.application.jobs.get(job_id)['upload_temporary_path']))
        try:
            directory.mkdir(parents=True,exist_ok=True)
            with temporary.open('xb') as output:
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
            validate_pdf(temporary, max_mb=self.max_mb, max_pages=self.max_pages, upload_root=self.uploads, check_text=False)
            temporary.replace(source)
            self.application.jobs.activate(job_id)
        except ValueError as error:
            self.application.jobs.reject_upload(job_id,code='invalid_pdf')
            raise WebError("invalid_pdf") from error
        except (OSError,JobStoreUnavailable):
            try:
                self.application.jobs.reject_upload(job_id,code='upload_interrupted',retryable=True)
            except JobStoreUnavailable:
                pass
            raise WebError('job_store_unavailable',503) from None
        finally:
            temporary.unlink(missing_ok=True)
            if directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()
        return {'ok':True,'job':self.public_job(self.application.jobs.get(job_id),environ)}

    def ocr(self, doc_id, environ):
        record = self.record(doc_id, environ)
        public = self.public_document(record)
        if self.application.jobs is None:
            raise WebError('jobs_not_configured', 503)
        if not public['ocr_available']:
            raise WebError('ocr_unavailable', 409)
        if any(job.get('document_id') == doc_id and job['state'] in {'staging','queued','running'}
               for job in self.application.jobs_snapshot()['jobs']):
            raise WebError('document_busy', 409)
        options = {**self.application.ingestion_defaults, 'enable_ocr': True}
        options['ocr_max_pages'] = min(options.get('ocr_max_pages', 50), 50)
        options['ocr_timeout_seconds'] = min(options.get('ocr_timeout_seconds', 120.0), 120.0)
        if len(public['unread_pages']) > options['ocr_max_pages']:
            raise WebError('ocr_page_limit', 413)
        source = self.source(doc_id, environ)
        try:
            job_id = self.application.jobs.submit(source, expected_sha256=doc_id,
                reprocess_review=True, **options)
        except JobQueueFull:
            raise WebError('ingestion_busy', 429, 2) from None
        except ValueError:
            raise WebError('job_source_changed', 409) from None
        return {'ok': True, 'job': self.public_job(self.application.jobs.get(job_id), environ)}

    def job_action(self, job_id, action, environ):
        job = self.application.job(job_id).get("job")
        self.public_job(job, environ)
        if job.get('document_id') in self.deletions.pending:
            raise WebError('document_deleting', 409)
        if action == "cancel":
            accepted = self.application.jobs.cancel(job_id)
            if not accepted:
                raise WebError("job_terminal", 409)
            return {"ok": True, "job": self.public_job(self.application.jobs.get(job_id), environ)}
        if job["state"] not in {"failed", "review_required"} or not job["retryable"]:
            raise WebError("retry_unavailable", 409)
        try:
            retry_id = self.application.jobs.retry(job_id)
        except JobQueueFull:
            raise WebError('ingestion_busy',429,2) from None
        except JobStoreUnavailable:
            raise WebError('job_store_unavailable',503) from None
        except ValueError:
            raise WebError('job_source_changed',409) from None
        return {"ok": True, "job": self.public_job(self.application.jobs.get(retry_id), environ)}

    def source(self, doc_id, environ):
        record = self.record(doc_id, environ)
        source = contained(self.store, Path(record["source_path"]))
        if source.parent != self.uploads / doc_id or source.suffix.lower() != ".pdf" or not source.is_file():
            raise WebError("source_unavailable", 404)
        return source



    def source_bytes(self, doc_id, environ):
        data = self.source(doc_id, environ).read_bytes()
        if hashlib.sha256(data).hexdigest() != doc_id:
            raise WebError("source_unavailable", 404)
        return data

    def thumbnail(self, doc_id, environ):
        """Small first-page preview only; no OCR, inference or disk artifacts.

        Caller holds the document lock. Authorization/path checks precede cache
        access; changing/removing the source invalidates its cached image.
        """
        source = self.source(doc_id, environ)
        def identity():
            stat = source.stat()
            return (str(source), stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
        try:
            current = identity()
            cached = self._thumbnail_cache.get(doc_id)
            if cached and cached[0] == current:
                self._thumbnail_cache.move_to_end(doc_id)
                return cached[1]
            import pymupdf
            with pymupdf.open(stream=self.source_bytes(doc_id, environ), filetype='pdf') as pdf:
                if pdf.needs_pass or not len(pdf):
                    raise WebError('source_unavailable', 404)
                page = pdf[0]
                scale = min(320 / max(1, page.rect.width), 210 / max(1, page.rect.height))
                image = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), colorspace=pymupdf.csRGB,
                                        alpha=False, annots=False).tobytes('png')
            if identity() != current:
                raise WebError('source_unavailable', 404)
            self._thumbnail_cache[doc_id] = (current, image)
            self._thumbnail_cache.move_to_end(doc_id)
            while len(self._thumbnail_cache) > 32:
                self._thumbnail_cache.popitem(last=False)
            return image
        except (OSError, RuntimeError, ValueError):
            self._thumbnail_cache.pop(doc_id, None)
            raise WebError('source_unavailable', 404) from None

    def locate_quote(self, doc_id, payload, environ):
        """Resolve a multi-page chunk's quote to its physical PDF page.

        A chunk's citation.page is its start page, so it is not necessarily
        the page containing the quoted sentence. This preview-only lookup
        preserves the original public citation and never invents coordinates.
        """
        record = self.record(doc_id, environ)
        quote, interval = payload.get('quote'), payload.get('page_range')
        if (not isinstance(quote, str) or not quote.strip() or len(quote) > 1200
                or not isinstance(interval, list) or len(interval) != 2
                or any(type(page) is not int for page in interval)
                or not 1 <= interval[0] <= interval[1] <= record['page_count']):
            raise WebError('invalid_source_location')
        import fitz
        from .rag.claims import normalize_text
        needle = normalize_text(quote)
        end = min(interval[1], interval[0] + 15)
        with fitz.open(stream=self.source_bytes(doc_id, environ), filetype='pdf') as pdf:
            for page in range(interval[0], end + 1):
                if needle in normalize_text(visible_page_text(pdf[page - 1])):
                    return {'ok':True, 'page':page, 'matched':True, 'page_range':interval}
        return {'ok':True, 'page':interval[0], 'matched':False, 'page_range':interval}

    def cancel_document_jobs(self, doc_id):
        active = False
        for job in self.application.jobs_snapshot()['jobs']:
            if (job.get('document_id') == doc_id and job['state'] in {'staging','queued','running'}):
                active = True
                self.application.jobs.cancel(job['job_id'])
        return active

    def delete(self, doc_id, environ):
        if not re.fullmatch('[0-9a-f]{64}', doc_id) or not self.allowed(doc_id, environ):
            raise WebError('not_found', 404)
        with self.deletions.file_lock(doc_id):
            with self.lock:
                record = self.registry.get(doc_id)
                jobs = [job for job in self.application.jobs_snapshot()['jobs']
                        if job.get('document_id') == doc_id]
                if not record and not jobs and doc_id not in self.deletions.pending:
                    raise WebError('not_found', 404)
                # Check every root before recording the irreversible intent.
                contained(self.store, self.store / doc_id)
                contained(self.store, self.uploads / doc_id)
                if self.index is not None:
                    contained(self.index, self.index / doc_id)
                self.deletions.mark(doc_id)
                if self.cancel_document_jobs(doc_id) or self.corpus_lock.busy:
                    self.deletions.start()
                    return {'ok':True, 'deleting':True}
            with self.corpus_lock.write(), self.lock:
                try:
                    result = self._delete_artifacts(doc_id)
                    self.deletions.finish(doc_id)
                    return result
                except Exception:
                    self.deletions.failed.add(doc_id)
                    raise

    def _delete_artifacts(self, doc_id):
        # Validate *all* artifact bindings before removing any data.
        contained(self.store, self.store / doc_id)
        if self.index is not None:
            contained(self.index, self.index / doc_id)
        # Only remove managed uploads; historical sources elsewhere are retained.
        uploads = contained(self.store, self.uploads / doc_id)
        delete_document_full(doc_id, store_dir=self.store, index_dir=self.index, registry=self.registry)
        self._legacy_coverage.pop(doc_id, None)
        retriever = self.application.query_service.retriever
        remove = getattr(retriever, "remove_document", None)
        if remove:
            remove(doc_id)
        # Versioned RAG keys already bind actual index bytes. Remove cached
        # answer bodies too; this local host has one corpus and one cache.
        cache = getattr(self.application.query_service, "cache", None)
        if cache is not None:
            cache.clear()
        provider_cache = getattr(getattr(self.application.query_service.answer_generator, "llm", None), "cache", None)
        if provider_cache is not None:
            provider_cache.clear()
        if self.index is not None:
            from .retrieval.index_builder import _write_corpus_manifest
            _write_corpus_manifest(self.index, doc_id, [], {})
        if uploads.is_dir():
            shutil.rmtree(uploads)
        if self.application.jobs is not None:
            self.application.jobs.forget_document(doc_id)
        for key, (_, ids) in list(self.responses.items()):
            if doc_id in ids:
                self.responses.pop(key, None)
        return {"ok": True}

    def remember(self, request_id, doc_ids):
        cutoff = time.time() - 86400
        self.responses = {key: entry for key, entry in self.responses.items() if entry[0] > cutoff}
        while len(self.responses) >= 1000:
            self.responses.pop(next(iter(self.responses)))
        self.responses[request_id] = (time.time(), set(doc_ids))

    def feedback(self, payload, environ):
        response_id = payload.get("response_id")
        kind = payload.get("kind")
        entry = self.responses.get(response_id) if isinstance(response_id, str) else None
        if kind not in {"helpful", "incorrect"} or entry is None:
            raise WebError("invalid_feedback")
        if not all(self.allowed(doc_id, environ) for doc_id in entry[1]):
            raise WebError("not_found", 404)
        destination = contained(self.store, self.store / "feedback.jsonl")
        with destination.open("a", encoding="utf-8") as output:
            output.write(json.dumps({"response_id": response_id, "kind": kind, "created_at": time.time()}) + "\n")
        return {"ok": True}
