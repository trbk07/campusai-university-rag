"""Public operational errors, without provider messages or credentials."""
import math
from urllib.error import HTTPError, URLError

from .client import (LLMAuthenticationError, LLMRateLimitError, LLMResponseError,
                     _retry_after_seconds)


def public_provider_failure(error):
    cause = error.__cause__
    code = getattr(error, 'provider_error_code', None)
    if isinstance(error, LLMAuthenticationError):
        code = 'provider_authentication_failed'
    elif isinstance(error, LLMRateLimitError):
        code = 'provider_busy' if code == 'provider_busy' else 'provider_rate_limited'
    elif isinstance(cause, HTTPError) and cause.code == 503:
        code = 'provider_overloaded'
    elif isinstance(cause, TimeoutError) or (isinstance(cause, URLError) and isinstance(cause.reason, TimeoutError)):
        code = 'provider_timeout'
    elif isinstance(error, LLMResponseError):
        code = 'provider_invalid_response'
    allowed = {'provider_authentication_failed', 'provider_rate_limited', 'provider_busy', 'provider_overloaded',
               'provider_timeout', 'provider_invalid_response'}
    value = {'error_code': code if code in allowed else 'provider_unavailable'}
    delay = getattr(error, 'retry_after_seconds', None)
    if delay is None and isinstance(cause, HTTPError) and cause.headers:
        delay = _retry_after_seconds(cause.headers.get('Retry-After'))
    if isinstance(delay, (int, float)) and math.isfinite(delay) and delay > 0:
        value['retry_after_seconds'] = math.ceil(delay)
    return value
