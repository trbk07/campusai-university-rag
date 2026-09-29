# Phase 5 operations and rollback

Start the local transport with `python scripts/serve.py`. Probe `/live` for
process liveness, `/ready` for index readiness, `/health` for service health,
and `/metrics` for bounded latency/error summaries. Query responses are safe
only when `ok=true`; abstentions are normal safety outcomes.

Ingestion jobs are asynchronous. Inspect the job endpoint/adapter, retry only
jobs marked `retryable`, and do not re-submit a running content hash. During a
provider outage, keep retrieval available but publish only structured
abstentions. Never bypass the grounding validator.

For index corruption, stop traffic, retain the corrupt directory for audit,
restore the last immutable index version, run `scripts/recovery_check.py`, and
only restore readiness after every checksum loads. For rollback, point the
deployment at the previous immutable code, calibration and index bundle, clear
answer caches by corpus/policy version, run `scripts/rollback_check.py`, then
repeat deployment smoke probes. Database and document metadata backups must be
restored before indexes because citations depend on stable document IDs.

Graceful shutdown calls `CampusAIApplication.close()`, drains the ingestion
executor, and closes query/cache resources. Forced termination may leave a job
in progress; restart from immutable source input and verify the resulting
index checksum rather than trusting a partial directory.
