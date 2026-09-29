# Data governance

CampusAI stores source PDFs, extracted text/tables, document metadata, indexes,
job state and bounded operational metrics. Provider requests receive only the
selected evidence excerpts and the user question; local paths, source hashes,
cache keys, internal scores and system diagnostics are excluded from public
responses.

API credentials are environment-only and must never be committed, cached in a
request body, or included in logs. The release secret scan covers tracked text
files; deployment logging must additionally redact authorization headers and
provider payloads. Metrics contain latency and counts, not questions or source
content.

Retention and deletion are deployment policy: configure a documented TTL for
uploads, provider caches and logs. A document deletion must remove its source,
store artifacts, index directory, registry entry and answer-cache generation.
Backups follow the same retention and access controls. Users must receive a
privacy notice naming the configured provider and data residency before live
provider use.
