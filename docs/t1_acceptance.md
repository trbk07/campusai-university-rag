# CampusAI Task 1 acceptance report

## Scope

CampusAI Task 1 provides a provider-neutral LLM foundation with Gemini and
OpenAI-compatible clients, SQLite response caching, rate limiting, bounded
retry/backoff, JSON parsing/schema checks, and an environment-only factory.

The supported JSON Schema subset is `type`, `required`, `properties`,
`items`, `enum`, `additionalProperties: false`, string length/pattern, and
numeric minimum/maximum. This is intentionally not a full JSON Schema engine.

## Offline validation

Run from `D:\Project`:

```powershell
# Task 1 acceptance tests only
uv run --extra dev pytest -q tests/test_llm.py tests/test_llm_acceptance.py

# Full repository regression suite and coverage gate
uv run --extra dev pytest -q
uv run --extra dev pytest -q --cov=campusai.llm --cov-fail-under=90
```

On Windows without `make`, use:

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m pytest -q --cov=campusai.llm --cov-fail-under=90
.venv\Scripts\python.exe scripts\secret_scan.py
```

The acceptance suite verifies:

- canonical cache keys contain provider/endpoint/request semantics and never API keys;
- concurrent identical misses make exactly one provider call (single-flight);
- cache hits preserve response text, usage, and original latency and skip the limiter/provider;
- SQLite `:memory:` and file-backed caches work across repeated operations;
- Gemini request/response parsing works offline and sends credentials in a header;
- timeout, network, 408, 429, 5xx, retry exhaustion, and both `Retry-After` forms;
- non-retryable 4xx and authentication errors are classified without leaking provider details;
- factory BOM handling, nested YAML values, provider selection, environment keys, and validation;
- fenced JSON, malformed JSON, and the documented schema subset.

Latest local offline result after the CampusAI namespace/domain migration:

```text
Task 1 acceptance: 33 passed
Full repository: 63 passed, 1 skipped
```

The one skipped test is the opt-in live Gemini contract test. The test is
intentionally skipped unless a newly issued, unexposed `GEMINI_API_KEY` and
`RUN_LLM_INTEGRATION=1` are supplied. It uses a temporary SQLite cache and
checks that the second identical request is cached with unchanged usage and
latency. Live verification is therefore **not claimed by offline CI**.

A previous local live verification was recorded on 2026-09-21:

```text
1 passed in 3.94s
```

That historical run used `gemini-3.8-flash` and supplied the credential only
through the process environment. It is not part of offline CI and was not
re-run as part of the current repository validation. The credential value is
intentionally not recorded in this report.

## Configuration and security

`configs/default.yaml` is read with PyYAML when installed. A strict standard
library fallback handles the repository's nested mapping configuration and
rejects malformed structure. API keys are read only from environment
variables. Gemini uses the `x-goog-api-key` header; keys are not put in URLs,
cache keys, exception messages, or logs by the client.

The cache is not encrypted at rest. Do not use a shared or unprotected cache
path for sensitive prompts/responses; filesystem permissions remain the
operator's responsibility. The process-local single-flight lock prevents
duplicate concurrent calls within one process. SQLite's timeout/WAL settings
provide safe file-backed operation across cache instances; a distributed
multi-process lock is outside T1 scope.

Run the repository's lightweight tracked-file secret scan with:

```powershell
python scripts/secret_scan.py
```

## Live contract test

```powershell
$env:RUN_LLM_INTEGRATION = "1"
$env:GEMINI_API_KEY = "<new key, supplied only in the environment>"
uv run --extra dev pytest -q tests/integration/test_gemini.py
```

Do not commit the key, `.env`, cache databases, or live response artifacts.
