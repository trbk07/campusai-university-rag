"""Opt-in routing across explicitly independent Gemini projects.

One call uses one credential and never retries here. Shared admission budgets
and endpoint-wide 503 cooldowns remain owned by GeminiClient. Only project quota
cooldowns are isolated, so changing keys cannot bypass a provider-wide outage.
"""
from dataclasses import dataclass, field
import hashlib
import re
from threading import Lock
from urllib.parse import urlsplit, parse_qsl
from urllib.request import Request

from .overload import OverloadCircuit, ProviderCoolingDown


@dataclass(frozen=True)
class ProjectRoute:
    request: Request = field(repr=False)
    circuit: OverloadCircuit = field(repr=False)
    generation: int
    reference: str


class GeminiProjectRouter:
    def __init__(self, credentials, *, health_path, model):
        if (not isinstance(credentials, list) or not 2 <= len(credentials) <= 3
                or not isinstance(model, str) or not re.fullmatch(r'gemini-[A-Za-z0-9._-]+', model)):
            raise ValueError('independent project routing requires two or three Gemini credentials')
        references, secrets, prepared = set(), set(), []
        for entry in credentials:
            if not isinstance(entry, (tuple, list)) or len(entry) != 2:
                raise ValueError('project credentials must contain reference/secret pairs')
            reference, secret = entry
            if (not isinstance(reference, str) or not re.fullmatch(r'[A-Z][A-Z0-9_]{0,63}', reference)
                    or not isinstance(secret, str) or not secret or secret.strip() != secret
                    or reference in references or secret in secrets):
                raise ValueError('project references and credentials must be nonempty and distinct')
            references.add(reference)
            secrets.add(secret)
            identity = hashlib.sha256(secret.encode()).hexdigest()
            prepared.append((reference, secret, identity))
        # Validate the complete pool before creating durable health state.
        prepared = [(reference, secret, {
            kind: OverloadCircuit(health_path, f'gemini-project:{model}:{identity}:{kind}')
            for kind in ('inference', 'countTokens')})
            for reference, secret, identity in prepared]
        self._projects, self.model = prepared, model
        self._next, self._lock = 0, Lock()

    def __repr__(self):
        return f'GeminiProjectRouter(projects={len(self._projects)}, model={self.model!r})'

    def route(self, request, timeout):
        parsed = urlsplit(request.full_url)
        prefix = f'/v1beta/models/{self.model}:'
        operation = parsed.path[len(prefix):] if parsed.path.startswith(prefix) else ''
        if (parsed.scheme != 'https' or parsed.hostname != 'generativelanguage.googleapis.com'
                or parsed.port not in (None, 443) or parsed.username or parsed.password or parsed.fragment
                or operation not in {'generateContent', 'streamGenerateContent', 'countTokens'}
                or parse_qsl(parsed.query, keep_blank_values=True) not in ([], [('alt', 'sse')])):
            raise ValueError('project credentials require the configured official Gemini endpoint')
        family = 'countTokens' if operation == 'countTokens' else 'inference'
        blocked = []
        with self._lock:
            for step in range(len(self._projects)):
                index = (self._next + step) % len(self._projects)
                reference, secret, circuits = self._projects[index]
                circuit = circuits[family]
                try:
                    generation = circuit.acquire(timeout)
                except ProviderCoolingDown as error:
                    blocked.append(error.retry_after_seconds)
                    continue
                headers = {k: v for k, v in request.header_items()
                           if k.lower() not in {'x-goog-api-key', 'authorization'}}
                routed = Request(request.full_url, data=request.data, headers=headers,
                                 method=request.get_method())
                routed.add_header('x-goog-api-key', secret)
                self._next = (index + 1) % len(self._projects)
                return ProjectRoute(routed, circuit, generation, reference)
        raise ProviderCoolingDown(min(blocked), 'provider_rate_limited')
