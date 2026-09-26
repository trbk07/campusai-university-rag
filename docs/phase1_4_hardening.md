# Phase 1–4 hardening record

This release closes the production gaps that are safely verifiable in the
repository and records the opt-in live-provider evidence supplied for the
current release run.

## Implemented

- Phase 1: document registry writes now use an OS-level lock, reload state
  before reads/writes, and ingestion jobs expose list/stat snapshots for an
  operator dashboard.
- Phase 2: existing structure-aware chunking remains fail-closed; the new API
  boundary keeps chunk provenance available to UI adapters instead of forcing
  transport code to rebuild it.
- Phase 3: calibrated thresholds are represented by an auditable
  `RetrievalPolicy`, loaded from a calibration report, bound to its retrieval
  mode, and enforced by `HybridRetriever`. RRF and reranker score spaces are
  never treated as interchangeable.
- Phase 4: query execution records latency/error metrics and exposes a
  dependency-free application adapter with structured query, readiness, job,
  and metrics contracts. An accessible HTML/WSGI shell is available for local
  deployment smoke tests.

## Verification

```text
115 offline tests passed, 2 live integration tests passed
compileall: passed
Phase 1/2 real-corpus acceptance: all exit criteria true.
Recovery check: one persisted index loaded; checksum corruption rejected.
Load test: 1/5/20 concurrent application calls completed successfully.
Live Gemini + live Phase 4 grounding: 2 passed in 16.54 seconds.
```

## Remaining release gates

The repository must not claim a full product 10/10 until these external gates
are attached to a release report: a larger reviewed retrieval holdout,
deployment-level UI accessibility checks, and a real public deployment/recovery
drill. Live provider and local concurrency/recovery smoke tests now have
passing evidence.
