# Phase 7 M3 current-source measurement — 2026-10-04

The active r17 candidate has a fresh M3 measurement bound to the source and
runtime currently in the workspace. It uses the existing pinned model snapshot
`1427fd652930e4ba29e8149678df786c240d8825` on CUDA (`float16`, `full_chunk`).
The physical smoke loaded the weights, warmed the model, scored the fixed probe
twice, and measured batches of 10, 20 and 40 candidates. The repeated score
delta was `0.0`; the model identity and file manifest stayed identical to the
previous measurement. The provider fault contract also passed all recorded
injections.

The M3 prerequisite validator passed M0–M3 using a fresh scratch results
directory. This avoided the active r17 route freeze while checking M3. The
scratch directory included existing M0–M2 evidence and S1 raw files; no route
or policy lock was copied. M3 model/fault inference did not score test or
holdout questions or create a heldout lock. The prerequisite validator did
re-read benchmark files to recompute the earlier M0–M2 gates; that validation
did not run a new heldout measurement.

S2 remains the same four previously authorized Gemini responses. The current
receipt changes only `commit` and `source_sha256` in the already audited S2
observation metadata. Its prior raw SHA-256 is
`3853298b99c1c8942d4968687f6a23026653d37dd4cb15d40eb5b6f785e1f0a6`; the new
raw artifact hash is recorded in `reranker_context_lifecycle.json`. The runtime,
index, model identity, requests, answers, citations, lifecycle counters and
cache probes are unchanged. No Gemini calls were added. The supplemental
recomputation returns no S2 errors.

Current full validator result: M0–M3 and S1–S2 PASS; M4 FAIL; M5–M12 and S3–S6
BLOCKED. M4's immutable route freeze binds the previous `model_snapshot_smoke`
file hash and source snapshot `618a6ef`. Replacing M3 evidence correctly makes
that lock fail. The test/holdout freeze is retained as-is; it must not be
rewritten or replayed as fresh evidence. A new M4 cycle needs a new reviewed
benchmark with untouched test and holdout groups.

Verification performed:

- `check_model_snapshot`: PASS, physical CUDA smoke, deterministic delta `0.0`.
- `check_reranker_faults --gate M3`: PASS, provider contract injections.
- `validate_reranker_release --through M3`: M0–M3 PASS.
- `validate_reranker_release --through M12`: M0–M3 and S1–S2 PASS; M4 FAIL;
  remaining gates BLOCKED.
- Related focused suite: 62 passed.
