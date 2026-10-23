# App improvement log

## 2026-10-23 — clean-source reproducibility

Detected a P1 packaging failure after exporting pushed commit `0ef54f90`:
`campusai.web` could not import because `ingestion.background` was not tracked.
Other app runtime modules were also local-only. Adding these dependencies exposed
a second integration mismatch: the worker passes the model revision/corpus
identity to an index builder whose published signature was older.

Repair: retain the existing implemented runtime modules in Git and include the
compatible index-builder signature, without changing grounding thresholds or
provider authorization. Validate from an isolated source export so editable
imports cannot hide missing files. The minimal repaired candidate passes all 98
local app/upload/conversation/page-scope tests.

The exact staged Git tree `360f670b2d5b078e11afa6a27fac4f6c8300d273` was then
exported independently and passed the same 98 tests in 11.49 s. QA-01 is fixed
on this verified runtime source. Other Phase 5 edits/results remain separate.

Prior cycle: five-file upload with per-file progress, three ingestion workers,
eight queued jobs and four query slots; 2,368 offline regression tests and 39
browser checks passed. Details and measurement limits are in
[PERFORMANCE_REPORT.md](PERFORMANCE_REPORT.md) and the Phase 12 handoff.

Next priorities: representative large/scan PDF latency and memory; live answer
quality remains tracked by Phase 5. The full-app goal stays active.
