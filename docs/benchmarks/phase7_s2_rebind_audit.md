# S2 source rebind audit — 2026-10-03

The existing r17 S2 receipt reuses four already authorized live Gemini
responses from r16. This audit makes no network request and opens no heldout
rows. Run it with the GPU runtime:

```powershell
$env:PYTHONPATH='src;.'
.tmp\phase7-gpu-runtime\Scripts\python.exe -m scripts.benchmarks.audit_phase7_context_rebind
```

Result: **22 checks pass; supplemental S2 recomputation passes**. The auditor
reads all seven archived context/lifecycle cases, confirms their observations
are identical to the original raw file, maps the four prompts to the same
dev questions, checks lifecycle query identity, unchanged scope/index/model/
runtime, and hashes the test/holdout files without parsing their rows. No new
Gemini call is made.

The older `binding_replay.verification.source_commit_changed_paths` list was
incorrect because it listed the contents of an old commit instead of the diff
between the measurement and target commits. The correct changed paths from
the original b795437 measurement to the 618a6ef cycle are
`configs/phase7_release_cycle.json` and
`scripts/benchmarks/revise_dev_difficulty.py`. Recomputed metadata changes in
the dev split are limited to difficulty, tags, review timestamp and owner
confirmation hash; question, answerability, scope and gold remain unchanged.
The replay audit retains that discrepancy and the corrected Git range as
separate evidence instead of rewriting the original raw observation.

Current source additions since the 618a6ef cycle are also inventoried. None
changes `src/campusai` or the installed runtime fingerprint. They do change the
repository source SHA, so M3 currently needs a source-bound smoke receipt and
M4 is blocked until M3 passes. See the active status in [plan.md](../../plan.md).
