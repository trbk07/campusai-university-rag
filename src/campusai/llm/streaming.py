"""Request-local model streaming, with raw output kept server-side."""
from contextlib import contextmanager
from contextvars import ContextVar
import json
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


_current = ContextVar('campusai_model_stream', default=None)
MAX_EVENT_BYTES = 1024 * 1024
MAX_STREAM_BYTES = 4 * MAX_EVENT_BYTES
_SSE_DONE = object()


class StreamCancelled(Exception):
    """A disconnected consumer cannot publish or cache a new answer."""


class StreamCapture:
    def __init__(self, notify=None, cancelled=None):
        self.notify = notify or (lambda _event: None)
        self.cancelled = cancelled or (lambda: False)
        self.started = time.perf_counter()
        self.calls = []
        self.call_started = None
        self.protocol = 'gemini-sse'

    def check(self):
        if self.cancelled():
            raise StreamCancelled()

    def select_protocol(self, protocol):
        if self.calls and self.protocol != protocol:
            from .client import LLMResponseError
            raise LLMResponseError('provider protocol changed inside one capture')
        self.protocol = protocol

    def begin(self, model, protocol='gemini-sse'):
        self.check()
        self.select_protocol(protocol)
        self.call_started = time.perf_counter()
        self.calls.append({'model': model, 'first_text_delta_ms': None,
                           'request_to_first_text_ms': None, 'text_characters': 0,
                           'status': 'incomplete'})

    def headers(self):
        self.check()
        self.calls[-1]['http_headers_ms'] = (time.perf_counter() - self.call_started) * 1000

    def text(self, value):
        self.check()
        row = self.calls[-1]
        if row['first_text_delta_ms'] is None:
            now = time.perf_counter()
            row['first_text_delta_ms'] = (now - self.call_started) * 1000
            row['request_to_first_text_ms'] = (now - self.started) * 1000
            # No unvalidated text, thought parts, prompts or source data leave
            # this module through progress notifications.
            self.notify({'type': 'progress', 'phase': 'generating'})
        row['text_characters'] += len(value)

    def finish(self):
        self.check()
        self.calls[-1]['status'] = 'complete'
        self.calls[-1]['total_ms'] = (time.perf_counter() - self.call_started) * 1000
        self.notify({'type': 'progress', 'phase': 'verifying'})

    def summary(self):
        return {'protocol': self.protocol, 'calls': [dict(row) for row in self.calls],
                'raw_text_exposed': False}


@contextmanager
def capture_stream(notify=None, cancelled=None):
    value = StreamCapture(notify, cancelled)
    token = _current.set(value)
    try:
        yield value
    finally:
        _current.reset(token)


def current_stream():
    return _current.get()


def stream_endpoint(endpoint):
    url = urlsplit(endpoint)
    if not url.path.endswith(':generateContent'):
        return None
    query = [(key, value) for key, value in parse_qsl(url.query, keep_blank_values=True)
             if key.lower() not in {'alt', 'key', 'api_key', 'apikey', 'access_token', 'token'}]
    query.append(('alt', 'sse'))
    return urlunsplit((url.scheme, url.netloc,
        url.path.removesuffix(':generateContent') + ':streamGenerateContent', urlencode(query), ''))


def sse_objects(response, capture, deadline, *, allow_done=False):
    """Read bounded UTF-8 SSE frames, including fragmented/multiline data."""
    from .client import LLMProviderError, LLMResponseError
    pending = b''
    data = []
    event_bytes = total = events = 0
    first_line = True
    read = getattr(response, 'read1', response.read)
    while True:
        capture.check()
        if time.perf_counter() > deadline:
            raise LLMProviderError('provider stream timed out') from TimeoutError()
        try:
            block = read(8192)
        except OSError as error:
            raise LLMProviderError('provider stream connection failed') from error
        if not isinstance(block, bytes):
            raise LLMResponseError('provider stream must contain bytes')
        total += len(block)
        if total > MAX_STREAM_BYTES:
            raise LLMResponseError('provider stream size limit exceeded')
        pending += block
        while pending:
            positions = [i for i in (pending.find(b'\n'), pending.find(b'\r')) if i >= 0]
            if not positions:
                break
            end = min(positions)
            if pending[end:] == b'\r' and block:
                break  # A following read may complete CRLF.
            width = 2 if pending[end:end + 2] == b'\r\n' else 1
            line, pending = pending[:end], pending[end + width:]
            event_bytes += len(line) + width
            if event_bytes > MAX_EVENT_BYTES:
                raise LLMResponseError('provider event size limit exceeded')
            if first_line:
                line = line.removeprefix(b'\xef\xbb\xbf')
                first_line = False
            if not line:
                if data:
                    events += 1
                    if events > 4096:
                        raise LLMResponseError('provider event count limit exceeded')
                    raw = b'\n'.join(data)
                    if allow_done and raw == b'[DONE]':
                        value = _SSE_DONE
                    else:
                        try:
                            value = json.loads(raw.decode('utf8'))
                        except (UnicodeError, ValueError, RecursionError):
                            raise LLMResponseError('provider stream contains malformed JSON') from None
                        if not isinstance(value, dict):
                            raise LLMResponseError('provider event must be a JSON object')
                    yield value
                data, event_bytes = [], 0
            elif line.startswith(b'data:'):
                field = line[5:]
                data.append(field[1:] if field.startswith(b' ') else field)
        if len(pending) + event_bytes > MAX_EVENT_BYTES:
            raise LLMResponseError('provider event size limit exceeded')
        if not block:
            if pending or data:
                raise LLMResponseError('provider stream ended inside an event')
            return


def read_gemini_stream(response, capture, timeout):
    """Assemble only candidate-zero final text; never publish partial output."""
    from .client import LLMResponseError
    capture.headers()
    pieces, usage, model, response_id, finished = [], {}, None, None, False
    for value in sse_objects(response, capture, capture.call_started + timeout):
        for name, previous in (('modelVersion', model), ('responseId', response_id)):
            current = value.get(name)
            if name in value and (not isinstance(current, str) or not current or previous is not None and current != previous):
                raise LLMResponseError('provider stream identity changed')
        model = value.get('modelVersion', model)
        response_id = value.get('responseId', response_id)
        if isinstance(value.get('usageMetadata'), dict):
            usage = value['usageMetadata']
        candidates = value.get('candidates', [])
        if not isinstance(candidates, list):
            raise LLMResponseError('provider stream candidates are invalid')
        feedback = value.get('promptFeedback', {})
        if not isinstance(feedback, dict):
            raise LLMResponseError('provider stream feedback is invalid')
        if feedback.get('blockReason'):
            raise LLMResponseError('provider blocked the streaming response')
        for candidate in candidates:
            if not isinstance(candidate, dict):
                raise LLMResponseError('provider stream candidate is invalid')
            index = candidate.get('index', 0)
            if type(index) is not int or index < 0:
                raise LLMResponseError('provider stream candidate index is invalid')
            if index != 0:
                continue
            content = candidate.get('content', {})
            if not isinstance(content, dict):
                raise LLMResponseError('provider stream content is invalid')
            parts = content.get('parts', [])
            if not isinstance(parts, list):
                raise LLMResponseError('provider stream content is invalid')
            for part in parts:
                if not isinstance(part, dict):
                    raise LLMResponseError('provider stream part is invalid')
                if 'thought' in part and type(part['thought']) is not bool:
                    raise LLMResponseError('provider stream thought flag is invalid')
                if part.get('thought') is True:
                    continue
                text = part.get('text')
                if text is not None and not isinstance(text, str):
                    raise LLMResponseError('provider stream text is invalid')
                if text:
                    if finished:
                        raise LLMResponseError('provider text follows its finish marker')
                    pieces.append(text)
                    capture.text(text)
            reason = candidate.get('finishReason')
            if reason:
                if finished or reason != 'STOP':
                    raise LLMResponseError('provider stream did not finish normally')
                finished = True
    if not finished or not pieces:
        raise LLMResponseError('provider stream ended without complete final text')
    capture.finish()
    return {'candidates': [{'content': {'parts': [{'text': ''.join(pieces)}]}, 'finishReason': 'STOP'}],
            'usageMetadata': usage, 'modelVersion': model}


def read_openai_stream(response, capture, timeout):
    """Assemble final choice-zero text; require both stop and wire terminator."""
    from .client import LLMResponseError
    capture.headers()
    pieces, usage, identity, model = [], {}, None, None
    finished = done = False
    for value in sse_objects(response, capture, capture.call_started + timeout, allow_done=True):
        if done:
            raise LLMResponseError('provider event follows stream terminator')
        if value is _SSE_DONE:
            done = True
            continue
        if 'error' in value:
            raise LLMResponseError('provider reported an error inside the stream')
        for name, previous in (('id', identity), ('model', model)):
            current = value.get(name)
            if name in value and (not isinstance(current, str) or not current
                    or previous is not None and current != previous):
                raise LLMResponseError('provider stream identity changed')
        identity, model = value.get('id', identity), value.get('model', model)
        if value.get('usage') is not None:
            if not isinstance(value['usage'], dict):
                raise LLMResponseError('provider stream usage is invalid')
            usage = value['usage']
        choices = value.get('choices')
        if not isinstance(choices, list):
            raise LLMResponseError('provider stream choices are invalid')
        for choice in choices:
            if not isinstance(choice, dict) or type(choice.get('index')) is not int or choice['index'] < 0:
                raise LLMResponseError('provider stream choice is invalid')
            if choice['index'] != 0:
                continue
            delta = choice.get('delta')
            if not isinstance(delta, dict):
                raise LLMResponseError('provider stream delta is invalid')
            if (delta.get('role') not in (None, 'assistant') or delta.get('refusal')
                    or delta.get('tool_calls') not in (None, []) or delta.get('function_call') is not None):
                raise LLMResponseError('provider stream did not return a final text answer')
            text = delta.get('content')
            if text is not None and not isinstance(text, str):
                raise LLMResponseError('provider stream text is invalid')
            if text:
                if finished:
                    raise LLMResponseError('provider text follows its finish marker')
                pieces.append(text)
                capture.text(text)
            reason = choice.get('finish_reason')
            if reason is not None:
                if finished or reason != 'stop':
                    raise LLMResponseError('provider stream did not finish normally')
                finished = True
    if not done or not finished or not pieces:
        raise LLMResponseError('provider stream ended without complete final text')
    capture.finish()
    return {'choices': [{'message': {'content': ''.join(pieces)}, 'finish_reason': 'stop'}],
            'usage': usage, 'model': model, 'id': identity}
