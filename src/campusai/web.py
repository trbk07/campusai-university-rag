"""CampusAI WSGI UI and HTTP adapters. No frontend build step is required."""
from __future__ import annotations

import json
import threading
import uuid
from pathlib import Path
from typing import Callable
from urllib.parse import unquote, urlsplit

from .api import CampusAIApplication
from .retrieval.calibration import CalibrationError
from .request_timings import capture_request, timed_stage
from .web_documents import WebDocuments, WebError
from .ingestion.jobs import JobStoreUnavailable

STATIC = Path(__file__).with_name("ui")
INDEX_HTML = (STATIC / "pages" / "index.html").read_text(encoding="utf-8")
ASSETS = {**{f"styles/{name}.css": "text/css" for name in ("tokens", "layout", "components", "responsive")},
          **{f"scripts/{name}.js": "text/javascript" for name in ("app", "api", "shared")},
          **{f"features/{name}.js": "text/javascript" for name in ("documents", "chat", "excerpts")}}
SECURITY_HEADERS = [("X-Content-Type-Options", "nosniff"), ("Referrer-Policy", "same-origin"),
    ("Cache-Control", "no-store"), ("X-Frame-Options", "SAMEORIGIN"),
    ("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-src 'self'; object-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'self'")]


def _bytes_response(body, start_response, content_type, status=200, extra=()):
    start_response(f"{status} {'OK' if status < 400 else 'Error'}", [
        ("Content-Type", content_type), ("Content-Length", str(len(body))), *SECURITY_HEADERS, *extra])
    return [body]


def _read(environ, maximum):
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError as error:
        raise WebError("invalid_body") from error
    if length > maximum:
        raise WebError("upload_too_large", 413)
    if length <= 0:
        raise WebError("invalid_body")
    body = environ["wsgi.input"].read(length)
    if len(body) != length:
        raise WebError("invalid_body")
    return body


def _payload(environ):
    try:
        payload = json.loads(_read(environ, 64000))
        if not isinstance(payload, dict):
            raise ValueError
        return payload
    except (ValueError, UnicodeDecodeError) as error:
        raise WebError("invalid_json") from error


def make_wsgi_app(application: CampusAIApplication, *, telemetry_hook: Callable | None = None,
                  max_concurrent_queries: int | None = None) -> Callable:
    # Deployment admission is explicit; historical evaluation transports keep
    # their own frozen concurrency profile instead of inheriting local limits.
    if max_concurrent_queries is not None and (type(max_concurrent_queries) is not int or not 1 <= max_concurrent_queries <= 32):
        raise ValueError('max_concurrent_queries must be between 1 and 32')
    documents = WebDocuments(application)
    query_slot = threading.BoundedSemaphore(max_concurrent_queries) if max_concurrent_queries else None

    def dispatch(environ, start_response):
        path = environ.get("PATH_INFO", "/")
        method = environ.get("REQUEST_METHOD", "GET").upper()
        request_id = environ.get("campusai.request_id") or uuid.uuid4().hex
        try:
            origin = environ.get("HTTP_ORIGIN")
            if method in {"POST", "DELETE"} and (environ.get("HTTP_SEC_FETCH_SITE") == "cross-site" or
                    (origin and urlsplit(origin).netloc != environ.get("HTTP_HOST"))):
                raise WebError("cross_origin_denied", 403)
            if path == "/" and method == "GET":
                return _bytes_response(INDEX_HTML.encode("utf-8"), start_response, "text/html; charset=utf-8")
            if path.startswith("/assets/") and method == "GET":
                name = path.removeprefix("/assets/")
                if name not in ASSETS:
                    raise WebError("not_found", 404)
                return _bytes_response((STATIC / name).read_bytes(), start_response, ASSETS[name] + "; charset=utf-8")
            if path in {"/health", "/live", "/ready", "/metrics"} and method == "GET":
                value = {"/health": application.health, "/live": application.liveness,
                         "/ready": application.readiness, "/metrics": application.metrics_snapshot}[path]()
                return _json_response(value, start_response, 503 if path == "/ready" and value.get("status") != "ready" else 200)
            if path == "/api/documents" and method == "GET":
                with documents.lock:
                    job_rows = application.jobs_snapshot()['jobs']
                    value = {"ok": True, "documents": documents.documents(environ, job_rows=job_rows),
                        "jobs": documents.jobs(environ, job_rows=job_rows),
                        "limits": {"max_mb": documents.max_mb, "max_pages": documents.max_pages},
                        "upload_available": application.jobs is not None and "campusai.authorized_doc_ids" not in environ,
                        "runtime": {"ai_configured": getattr(getattr(application.query_service, "answer_generator", None), "llm", None) is not None}}
                    return _json_response(value, start_response)
            if path == "/api/documents/upload" and method == "POST":
                if environ.get("CONTENT_TYPE", "").split(";")[0] != "application/pdf":
                    raise WebError("invalid_pdf")
                data = _read(environ, documents.max_mb * 1024 * 1024)
                # Upload bodies and per-document validation/write work can run
                # concurrently. Job identity/capacity and the registry provide
                # their own synchronization; the global UI lock serialized a
                # whole PDF at a time and blocked five-file batches.
                value = documents.upload(data, unquote(environ.get("HTTP_X_FILENAME", "document.pdf")), environ)
                return _json_response(value, start_response, 200 if value.get("duplicate") else 202)
            parts = path.strip("/").split("/")
            if len(parts) in {3, 4} and parts[:2] == ["api", "documents"]:
                doc_id = parts[2]
                if len(parts) == 3 and method == 'DELETE':
                    value = documents.delete(doc_id, environ)
                    return _json_response(value, start_response, 202 if value.get('deleting') else 200)
                with documents.lock:
                    if len(parts) == 3 and method == "GET":
                        return _json_response({"ok": True, "document": documents.public_document(documents.record(doc_id, environ))}, start_response)
                    if len(parts) == 4 and parts[3] == 'ocr' and method == 'POST':
                        if _payload(environ):
                            raise WebError('invalid_json')
                        return _json_response(documents.ocr(doc_id, environ), start_response, 202)
                    if len(parts) == 4 and parts[3] == "file" and method == "GET":
                        pdf = documents.source_bytes(doc_id, environ)
                        return _bytes_response(pdf, start_response, "application/pdf", extra=[("Content-Disposition", 'inline; filename="source.pdf"')])
                    if len(parts) == 4 and parts[3] == "locate" and method == "POST":
                        return _json_response(documents.locate_quote(doc_id, _payload(environ), environ), start_response)
            if len(parts) in {3, 4} and parts[:2] == ["api", "jobs"]:
                with documents.lock:
                    if len(parts) == 3 and method == "GET":
                        value = documents.public_job(application.job(parts[2]).get("job"), environ)
                        return _json_response({"ok": True, "job": value}, start_response)
                    if len(parts) == 4 and parts[3] in {"cancel", "retry"} and method == "POST":
                        return _json_response(documents.job_action(parts[2], parts[3], environ), start_response)
            if path == "/api/feedback" and method == "POST":
                with documents.lock:
                    return _json_response(documents.feedback(_payload(environ), environ), start_response)
            if path == "/api/query" and method == "POST":
                payload = _payload(environ)
                options = {key: payload[key] for key in ("doc_ids", "filters", "top_k", "language", "history", "selected_text", "requires_context") if key in payload}
                if "doc_ids" in options and (not isinstance(options["doc_ids"], list)
                        or any(not isinstance(doc, str) or not doc for doc in options["doc_ids"])):
                    raise WebError("invalid_json")
                if "filters" in options and not isinstance(options["filters"], dict):
                    raise WebError("invalid_json")
                if "top_k" in options and (type(options["top_k"]) is not int or not 1 <= options["top_k"] <= 40):
                    raise WebError("invalid_json")
                if not isinstance(options.get("language", "vi"), str) or options.get("language", "vi") not in {"vi", "en"}:
                    raise WebError("invalid_json")
                options["request_id"] = request_id
                if "campusai.authorized_doc_ids" in environ:
                    options["authorized_doc_ids"] = environ["campusai.authorized_doc_ids"]
                if query_slot is not None and not query_slot.acquire(blocking=False):
                    return _json_response({"ok": False, "error_code": "query_busy", "retry_after_seconds": 1},
                        start_response, 429, extra=[("Retry-After", "1"), ("X-Request-ID", request_id)])
                try:
                    with documents.corpus_lock.read():
                        with documents.lock:
                            if documents.deletions.pending and 'doc_ids' not in options:
                                raise WebError('document_deleting', 409)
                            if "doc_ids" in options and getattr(application, "jobs", None) is not None:
                                if not options["doc_ids"]:
                                    raise WebError("empty_scope")
                                latest_jobs = documents.latest_jobs_snapshot()
                                for doc_id in options["doc_ids"]:
                                    if not documents.public_document(documents.record(doc_id, environ),
                                            latest_job=latest_jobs.get(doc_id))["ready"]:
                                        raise WebError("document_not_ready", 409)
                        try:
                            value = documents.answer_document_info(payload.get("question", ""), options, environ)
                            if value is None:
                                value = application.query(payload.get("question", ""), **options)
                        except TimeoutError:
                            raise WebError("provider_timeout", 504)
                        except (CalibrationError, OSError, json.JSONDecodeError):
                            raise WebError("retrieval_not_ready", 503)
                        except ValueError:
                            raise WebError("invalid_json")
                        if value.get("ok"):
                            ids = options.get("doc_ids", options.get("authorized_doc_ids"))
                            if ids is None:
                                ids = [item["doc_id"] for item in value.get("answer", {}).get("citations", [])]
                            with documents.lock:
                                documents.remember(request_id, ids)
                finally:
                    if query_slot is not None:
                        query_slot.release()
                status = 200 if value.get("ok") else {
                    "provider_overloaded": 503, "provider_rate_limited": 429,
                    "provider_timeout": 504, "provider_authentication_failed": 503,
                    "provider_invalid_response": 502, "provider_unavailable": 503,
                }.get(value.get("error_code"), 400)
                headers = [("X-Request-ID", request_id)]
                if value.get("retry_after_seconds"):
                    headers.append(("Retry-After", str(value["retry_after_seconds"])))
                return _json_response(value, start_response, status, extra=headers)
            raise WebError("not_found", 404)
        except WebError as error:
            retry = {'retry_after_seconds':error.retry_after_seconds} if error.retry_after_seconds else {}
            headers = [('Retry-After',str(error.retry_after_seconds))] if error.retry_after_seconds else []
            return _json_response({'ok':False,'error_code':error.code,**retry},start_response,error.status,extra=headers)
        except JobStoreUnavailable:
            return _json_response({'ok':False,'error_code':'job_store_unavailable'},start_response,503)
        except (OSError, ValueError, KeyError, TypeError):
            return _json_response({"ok": False, "error_code": "service_unavailable"}, start_response, 503)

    def app(environ, start_response):
        # Protect corpus writes without holding the read-only UI metadata lock
        # while Gemini responds. Query admission happens before its corpus lease.
        path = environ.get('PATH_INFO', '')
        source_lookup = path.startswith('/api/documents/') and path.endswith('/locate')
        upload_route = path == '/api/documents/upload'
        delete_route = path.startswith('/api/documents/') and environ.get('REQUEST_METHOD', '').upper() == 'DELETE'
        if (environ.get('REQUEST_METHOD', 'GET').upper() in {'POST', 'DELETE'}
                and path != '/api/query' and not source_lookup and not upload_route and not delete_route):
            with documents.corpus_lock.write():
                return dispatch(environ, start_response)
        return dispatch(environ, start_response)

    if telemetry_hook is None:
        return app

    def measured(environ, start_response):
        reset = getattr(application.query_service, "reset_request_state", None)
        if reset is not None:
            reset()
        request_id = uuid.uuid4().hex
        environ["campusai.request_id"] = request_id
        def respond(status, headers, exc_info=None):
            headers = [(key, value) for key, value in headers if key != "X-Request-ID"] + [("X-Request-ID", request_id)]
            return start_response(status, headers) if exc_info is None else start_response(status, headers, exc_info)
        with capture_request() as trace:
            body = app(environ, respond)
        trace["request_id"] = request_id
        trace["cache_hit"] = application.query_service.last_cache_hit
        retrieval = getattr(application.query_service.retriever, "last_trace", None)
        trace["retrieval_trace"] = retrieval.to_dict() if retrieval is not None else None
        telemetry_hook(trace)
        return body
    return measured


@timed_stage("serialization")
def _json_response(value, start_response, status: int = 200, extra=()):
    return _bytes_response(json.dumps(value, ensure_ascii=False).encode("utf-8"), start_response, "application/json; charset=utf-8", status, extra)
