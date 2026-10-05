# Phase 7 validated dev inheritance — 2026-10-04

Actual preflight reconstructs **817 records**: all 804 consumed r18 rows and
the 13 previously exposed r12 absent-field dev rows. Authorship remains
**180 human / 637 AI**. Original questions, scope, gold, expected behavior,
review timestamps and authorization hashes are preserved. Only allocation
changes to dev, including 164 prior test and 162 prior holdout records.

The loader validates historical review/source packets against the original
10-document index, verifies completed candidate observations against exact
r18 split bytes, and verifies r12's selected dev-only extension. It checks
all 22 original index files and all 54 parent benchmark artifacts; the expanded
12-document index must retain every historical document byte. Three historical
authorizations retain their original index and timestamps. No old receipt is
rebound to the expanded index.

The inherited manifest is bound by the successor's generation authorization.
Artifacts cannot inject internal validation metadata. Mixed audit exports keep
new authorizations separate from verified historical provenance. Every inherited
row is rejected if assigned to test or holdout, or if its content/owner/hash changes.

Actual loader replay reconstructs all 817 records and audit entries exactly,
returns no row/review errors, and rejects **817/817** attempted heldout
reassignments. The dev-only pool intentionally fails the four missing test/holdout
coverage checks; it is not a complete benchmark or release freeze. The final
offline suite has **810 passed, 2 opt-in live LLM tests skipped, coverage 89.51%**.

An exact-byte restore recovers the original 22-file index with manifest SHA
`9952da0f42bde725d08c6a676ca260e70ac12313fa33c401ca6a387a90419f38`
from the source-expansion index archive plus `source_parent_index_manifest.json`.
The expanded index remains
`f944f088bc01f173c340f92b94b8f3f89b0f61af9fabec84a38a51440d91ac3d`.

Git previously normalized 16 provenance files to LF while their physical frozen
bytes were CRLF. The r18 directory now uses `* -text`. Those Git blobs store the
existing exact bytes; no physical benchmark records, approvals, source banks or
locks changed. `parent_git_serialization_audit.json` verifies that all differences
are newline serialization only. Primary r18 split bytes remain unchanged.

The active r18 validator was rechecked through M2: M0/M1/S1 PASS, M2 FAIL,
`status=conditional`, score null, `all_release_gates_pass=false`. This task does
not promote any release gate. No new question or model score was generated.

Reproduction uses an absent output directory:

```powershell
$env:PYTHONPATH='.;src'
$env:PYTHONUTF8='1'
.venv/Scripts/python.exe -m scripts.benchmarks.prepare_phase7_dev_inheritance --source data/benchmark/phase7_review_cycles/phase7-release-20261004-r18 --old-index .tmp/hybrid-index --new-index .tmp/phase7-source-expansion-20261004/index --candidate-report evaluation/results/phase7-source-context-20261004-r18/candidate_coverage.json --dev-extension data/benchmark/phase7_review_cycles/phase7-dev-extension-20261003-r12 --destination .tmp/phase7-inheritance-replay
```

Next: complete the semantic source/history audit, ensure enough fresh independent
groups for novel dev and both heldout splits, integrate exact dev inheritance
with source-checked questions, freeze the successor and measure all gates in order.
Roadmap: [plan.md](../../../plan.md).
