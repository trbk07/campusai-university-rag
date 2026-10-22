"""Read only typed Google quota metadata; never infer limits from error prose."""
import math
import re
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

_KINDS = {
    'GenerateRequestsPerDayPerProjectPerModel-FreeTier': 'requests_per_day',
    'GenerateRequestsPerMinutePerProjectPerModel-FreeTier': 'requests_per_minute',
    'GenerateContentInputTokensPerModelPerMinute-FreeTier': 'input_tokens_per_minute',
}


def google_quota_hints(payload):
    result = {'retry_delay_seconds': None, 'violations': []}
    if not isinstance(payload, dict) or not isinstance(payload.get('error'), dict):
        return result
    details = payload['error'].get('details', [])
    if not isinstance(details, list):
        return result
    for detail in details[:64]:
        if not isinstance(detail, dict):
            continue
        if detail.get('@type') == 'type.googleapis.com/google.rpc.RetryInfo':
            duration = detail.get('retryDelay')
            if isinstance(duration, str) and re.fullmatch(r'\d{1,6}(?:\.\d{1,9})?s', duration):
                value = float(duration[:-1])
                if math.isfinite(value) and 0 <= value <= 86400:
                    result['retry_delay_seconds'] = max(result['retry_delay_seconds'] or 0, value)
        if detail.get('@type') != 'type.googleapis.com/google.rpc.QuotaFailure':
            continue
        violations = detail.get('violations', [])
        if not isinstance(violations, list):
            continue
        for item in violations[:64]:
            if not isinstance(item, dict):
                continue
            kind = _KINDS.get(item.get('quotaId')) if isinstance(item.get('quotaId'), str) else None
            metric = item.get('quotaMetric')
            dimensions = item.get('quotaDimensions', {})
            if (kind is None or not isinstance(metric, str)
                    or not metric.startswith('generativelanguage.googleapis.com/')
                    or not isinstance(dimensions, dict)):
                continue
            model = dimensions.get('model')
            if not isinstance(model, str) or not re.fullmatch(r'(?:models/)?gemini-[A-Za-z0-9._-]{1,100}', model):
                continue
            value = item.get('quotaValue')
            if isinstance(value, str) and re.fullmatch(r'\d{1,10}', value):
                value = int(value)
            if type(value) is not int or not 0 <= value <= 1_000_000_000:
                value = None
            # No subject, description, project identifiers or future rollout value.
            result['violations'].append({'kind': kind, 'model': model.removeprefix('models/'), 'value': value})
    return result


def scoped_quota_hint(hints, model):
    violations = [v for v in hints['violations'] if v['model'] == model]
    delay = hints['retry_delay_seconds']
    if any(v['kind'] == 'requests_per_day' for v in violations):
        local = datetime.fromtimestamp(time.time(), ZoneInfo('America/Los_Angeles'))
        reset = (local + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        delay = max(delay or 0, reset.timestamp() - time.time())
    return delay, violations
