"""Bounded progress transport; only the existing verified response is public."""
import io
import json
import queue
import threading
import uuid

from .llm.streaming import capture_stream


def stream_response(environ, start_response, run, body, slots, security_headers):
    from .web_documents import WebError
    if not slots.acquire(blocking=False):
        raise WebError('query_busy', 429, 1)
    environ['campusai.stream_handled'] = True
    request_id = environ.setdefault('campusai.request_id', uuid.uuid4().hex)
    child = {**environ, 'HTTP_ACCEPT': 'application/json', 'wsgi.input': io.BytesIO(body)}
    child.pop('campusai.stream_handled', None)
    events = queue.Queue(maxsize=8)
    cancelled = threading.Event()

    def progress(event):
        if cancelled.is_set():
            return
        # Allow only fixed phase names, never arbitrary model/provider fields.
        if event.get('type') != 'progress' or event.get('phase') not in {'generating', 'verifying'}:
            return
        try:
            events.put_nowait({'type': 'progress', 'phase': event['phase']})
        except queue.Full:
            pass

    def finish(value):
        while not cancelled.is_set():
            try:
                events.put(value, timeout=.1)
                return
            except queue.Full:
                pass

    def worker():
        response = {}
        iterable = None
        try:
            with capture_stream(progress, cancelled.is_set):
                iterable = run(child, lambda status, headers, exc_info=None:
                    response.update(status=status, headers=headers))
                result = b''.join(iterable)
            if len(result) > 4 * 1024 * 1024:
                raise ValueError('response limit')
            finish({'type': 'result', **response, 'body': result})
        except Exception:
            # No exception text, credentials, source paths or partial model text.
            finish({'type': 'result', 'status': '503 Error',
                'headers': [('Content-Type', 'application/json'), *security_headers],
                'body': b'{"ok":false,"error_code":"service_unavailable"}'})
        finally:
            try:
                if iterable is not None and hasattr(iterable, 'close'):
                    iterable.close()
            except Exception:
                pass
            finally:
                slots.release()

    thread = threading.Thread(target=worker, daemon=True, name='campusai-query-stream')
    try:
        thread.start()
    except Exception:
        slots.release()
        raise WebError('service_unavailable', 503) from None
    first = events.get()
    if first['type'] == 'result':
        # Cache/local answers and failures before the first actual model delta
        # keep their original JSON status/headers; none is counted as streaming.
        start_response(first['status'], first['headers'])
        return [first['body']]
    start_response('200 OK', [('Content-Type', 'application/x-ndjson; charset=utf-8'),
        ('X-Request-ID', request_id), ('X-Accel-Buffering', 'no'), *security_headers])

    def encode(value):
        return (json.dumps(value, ensure_ascii=False, allow_nan=False) + '\n').encode('utf8')

    def output():
        try:
            yield encode(first)
            while True:
                value = events.get()
                if value['type'] == 'result':
                    try:
                        payload = json.loads(value['body'])
                    except (ValueError, UnicodeError, RecursionError):
                        payload = {'ok': False, 'error_code': 'service_unavailable'}
                        value['status'] = '503 Error'
                    yield encode({'type': 'result', 'status': int(value['status'].split()[0]),
                                  'value': payload})
                    return
                yield encode(value)
        finally:
            # The model reader observes cancellation at the next I/O checkpoint;
            # its existing socket timeout bounds a stalled provider read.
            cancelled.set()
    class Output:
        def __init__(self):
            self.iterator = output()
        def __iter__(self):
            return self
        def __next__(self):
            return next(self.iterator)
        def close(self):
            cancelled.set()
            self.iterator.close()
    return Output()
