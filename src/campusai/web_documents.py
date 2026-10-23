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
from contextlib import contextmanager
from pathlib import Path

from .documents.registry import DocumentRegistry
from .ingestion.pipeline import delete_document_full
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
        # Queries share a read lease. Deletes retain an exclusive lease so a
        # source cannot disappear while an answer is being grounded.
        self.corpus_lock = CorpusAccessLock()
        self.responses: dict[str, tuple[float, set[str]]] = {}
        self._legacy_coverage = {}

    @property
    def registry(self):
        contained(self.store, self.store / "registry.json")
        return DocumentRegistry(self.store / "registry.json")

    @staticmethod
    def allowed(doc_id, environ):
        scope = environ.get("campusai.authorized_doc_ids")
        return scope is None or doc_id in scope

    def record(self, doc_id, environ):
        if not re.fullmatch(r"[0-9a-f]{64}", doc_id) or not self.allowed(doc_id, environ):
            raise WebError("not_found", 404)
        record = self.registry.get(doc_id)
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
        if (available and record.get('status') == 'succeeded'
                and meta.get('text_coverage_version') != 1
                and meta.get('parser_version') != 'rapidocr-onnx-v1'):
            stat = source.stat()
            identity = (stat.st_mtime_ns, stat.st_size)
            cached = self._legacy_coverage.get(doc_id)
            if cached is None or cached[0] != identity:
                from .ingestion.docling_parser import parse_pdf
                unread = [page['page'] for page in parse_pdf(source) if page.get('requires_ocr')]
                self._legacy_coverage[doc_id] = (identity, unread)
            else:
                unread = cached[1]
        ready = record.get("status") == "succeeded" and self.index is not None and all(
            contained(self.index, self.index / doc_id / name).is_file() for name in ("bm25.json", "dense.json"))
        ready = ready and not unread
        safe_meta = {key: meta[key] for key in ("document_type", "academic_year", "program", "university", "version", "semester")
                     if isinstance(meta.get(key), (str, int))}
        if latest_job is ...:
            latest_job = self.latest_jobs_snapshot().get(doc_id)
        if latest_job is not None and (latest_job['state'] != 'succeeded' or not latest_job.get('ready')):
            ready = False
        return {"doc_id": doc_id, "name": source.name, "page_count": record.get("page_count", 0),
                "metadata": safe_meta, "ready": ready, "status": "review_required" if unread else "ready" if ready else record.get("status", "review_required"),
                "review_reason": 'ocr_required' if unread else record.get('review_reason'),
                "unread_pages": unread,
                "ocr_available": self.application.jobs is not None and available and not ready
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

    def documents(self, environ, *, job_rows=None):
        latest_jobs = self.latest_jobs_snapshot(job_rows)
        records = [self.public_document(record, latest_job=latest_jobs.get(record['doc_id']))
                   for record in self.registry.list() if self.allowed(record["doc_id"], environ)]
        return sorted(records, key=lambda record: record.get("uploaded_at") or 0, reverse=True)

    def answer_document_info(self, question, options, environ):
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
        selected = [d for d in self.documents(environ) if d['ready'] and (ids is None or d['doc_id'] in ids)]
        filters = validate_filters(options.get('filters'))
        selected = [d for d in selected if all(str(d['metadata'].get(k, '')).casefold() == str(v).casefold()
                                             for k, v in filters.items())]
        response = document_info_response(question, selected, options.get('language', 'vi'))
        if response is not None:
            resolve_query(question, history=options.get('history'), selected_text=options.get('selected_text'),
                          requires_context=options.get('requires_context', False))
            self.application.query_service.reset_request_state()
            return response
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
                content = self.answer_document_info(clauses[1-index],options,environ)
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
        resolve_query(question, history=options.get('history'), selected_text=options.get('selected_text'),
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
                pdf[page-1].get_text(), 'text',1.0,'source_pages',
                {'source_name':doc['name'],'source_hash':doc['doc_id'],'page_range':[page,page],
                 'heading_path':[f'PDF page {page}']}) for page in pages]
        if any(not r.content.strip() for r in results):
            info['answer'].update(answer='Một số trang chỉ có ảnh hoặc chưa đọc được chữ; cần OCR trước khi trả lời.'
                if options.get('language','vi') == 'vi' else 'Some pages have no readable text and require OCR.',
                abstained=True,confidence='low')
            info['document_info']['kind'] = 'page_text_unavailable'
            return info
        answer = service.ask_source_pages(question,results,language=options.get('language','vi'),
            history=options.get('history'),selected_text=options.get('selected_text'),
            requires_context=options.get('requires_context',False))
        if answer.reason == 'llm_error':
            return {'ok':False, **(answer.provider_failure or {'error_code':'provider_unavailable'})}
        return {'ok':True,'answer':answer.to_public_dict(),'cache_hit':service.last_cache_hit}

    def public_job(self, job, environ):
        if not job:
            raise WebError("not_found", 404)
        source = contained(self.store, Path(job["source_path"]))
        doc_id = job.get("document_id") or source.parent.name
        if not self.allowed(doc_id, environ):
            raise WebError("not_found", 404)
        fields = ("job_id", "state", "stage", "progress", "document_id", "ready", "retryable",
                  "created_at", "updated_at", "ingestion_status", "index_status")
        value = {key: job.get(key) for key in fields}
        value["name"] = source.name
        value["error_code"] = ("processing_interrupted" if job.get('error_code')=='processing_interrupted' else
                               "processing_failed" if job.get("state") == "failed" else None)
        return value

    def jobs(self, environ, *, job_rows=None):
        values = []
        job_rows = self.application.jobs_snapshot()["jobs"] if job_rows is None else job_rows
        for job in job_rows:
            try:
                values.append(self.public_job(job, environ))
            except WebError:
                continue
        return values

    def upload(self, data, name, environ):
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
        if existing and self.public_document(existing)['ready']:
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
        if action == "cancel":
            accepted = self.application.jobs.cancel(job_id)
            if not accepted:
                raise WebError("job_terminal", 409)
            return {"ok": True, "job": self.public_job(self.application.jobs.get(job_id), environ)}
        if job["state"] != "failed" or not job["retryable"]:
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
                if needle in normalize_text(pdf[page - 1].get_text()):
                    return {'ok':True, 'page':page, 'matched':True, 'page_range':interval}
        return {'ok':True, 'page':interval[0], 'matched':False, 'page_range':interval}

    def delete(self, doc_id, environ):
        record = self.record(doc_id, environ)
        if any(job.get("document_id") == doc_id or Path(job["source_path"]).parent.name == doc_id
               for job in self.application.jobs_snapshot()["jobs"] if job["state"] in {"staging", "queued", "running"}):
            raise WebError("document_busy", 409)
        # Validate *all* artifact bindings before removing any data.
        contained(self.store, self.store / doc_id)
        if self.index is not None:
            contained(self.index, self.index / doc_id)
        source = None
        try:
            source = contained(self.store, Path(record["source_path"]))
        except WebError:
            pass
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
        if source is not None and source.parent == self.uploads / doc_id:
            shutil.rmtree(contained(self.store, source.parent))
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
