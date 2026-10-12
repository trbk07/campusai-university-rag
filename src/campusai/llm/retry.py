"""One bounded retry for HTTP 503; no transport or other-status retries."""
from __future__ import annotations

from email.utils import parsedate_to_datetime
import math
import random
import time
from urllib.error import HTTPError


def retry503(request, transport, *, timeout, max_retries=1, attempts=None,
             before_attempt=None, before_retry=None, on_change=None,
             min_wait_seconds=30.0, max_wait_seconds=60.0):
    """Keep the request identical and expose every attempt/wait to an auditor.

    Acceptance callers reserve their shared retry budget before sleeping and
    enforce global spacing in ``before_attempt``. A denied reservation or
    observer failure aborts before another external request.
    """
    if type(max_retries) is not int or max_retries not in (0, 1):
        raise ValueError("503 policy allows zero or one retry")
    if (not isinstance(min_wait_seconds, (int, float)) or isinstance(min_wait_seconds, bool)
            or not isinstance(max_wait_seconds, (int, float)) or isinstance(max_wait_seconds, bool)
            or not math.isfinite(min_wait_seconds) or not math.isfinite(max_wait_seconds)
            or min_wait_seconds < 0 or max_wait_seconds < min_wait_seconds):
        raise ValueError("503 retry wait bounds must be finite and ordered")
    attempts = [] if attempts is None else attempts
    notify = on_change or (lambda: None)
    for ordinal in range(max_retries + 1):
        if before_attempt:
            before_attempt()
        event = {"attempt": ordinal + 1, "provider_start": time.time(),
                 "status": "attempted", "http_status": None}
        attempts.append(event)
        notify()  # Durable attempted-call record precedes transport I/O.
        began = time.perf_counter()
        try:
            response = transport(request, timeout=timeout)
        except Exception as error:
            event.update(status="failed", error_type=type(error).__name__,
                         http_status=getattr(error, "code", None),
                         latency_ms=(time.perf_counter() - began) * 1000)
            notify()
            if not isinstance(error, HTTPError) or error.code != 503 or ordinal == max_retries:
                raise
            if before_retry:
                try:
                    before_retry()
                except Exception:
                    event["retry_denied"] = True
                    notify()
                    error.close()
                    raise
            hint = error.headers.get("Retry-After") if error.headers else None
            delay = None
            if hint is not None:
                try:
                    delay = float(hint)
                except (TypeError, ValueError):
                    try:
                        delay = parsedate_to_datetime(hint).timestamp() - time.time()
                    except (TypeError, ValueError, IndexError, OverflowError, AttributeError):
                        pass
            if delay is not None and math.isfinite(delay) and delay > max_wait_seconds:
                event["retry_skipped"] = "retry_after_exceeds_wait_budget"
                notify()
                error.close()
                raise error
            if delay is None or not math.isfinite(delay):
                delay = min_wait_seconds + random.random() * (max_wait_seconds - min_wait_seconds)
            delay = min(max_wait_seconds, max(min_wait_seconds, delay))
            event["retry_wait_seconds"] = delay
            notify()
            # Close the discarded HTTP-error response before a new connection.
            error.close()
            waited = time.perf_counter()
            time.sleep(delay)
            event["retry_wait_ms"] = (time.perf_counter() - waited) * 1000
            notify()
        else:
            event.update(status="completed", latency_ms=(time.perf_counter() - began) * 1000)
            notify()
            return response
