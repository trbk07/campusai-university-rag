# Phase 5 release notes

Phase 5 adds fail-closed citation/claim validation, deterministic abstention,
dev-only confidence calibration, a 400-record split-hygiene gate, more than 50
offline adversarial cases, and checksum-bound release packaging. It also adds
live-provider, load, security, deployment, recovery and rollback evidence
collectors plus operational and data-governance runbooks.

Known limitations: independent annotation must be performed and signed by a
person who did not create the benchmark; live-provider evidence requires a
runtime secret; deployment and rollback evidence require staging or production
infrastructure and immutable current/previous indexes. Until those external
artifacts pass, the release remains a release candidate and must not be called
production-ready.
