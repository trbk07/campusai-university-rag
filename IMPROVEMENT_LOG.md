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

## 2026-10-23 — mixed PDF correctness and parser memory

Reproduced four failures before repair: scan page undetected, mixed document
incorrectly succeeded, scan content omitted despite OCR opt-in, and empty OCR
output accepted. The parser now excludes unused image bytes and marks no-text
pages containing images/vector content. The pipeline requests bounded OCR only
for those physical pages, preserves native page content, and rejects incomplete
OCR. Blank pages in mixed documents need no OCR. OCR warnings survive metadata
assembly; old extraction caches and job identities cannot bypass the new policy.

Legacy ready sources without coverage metadata receive a cached local page audit;
incomplete documents cannot enter query scope. Document details explain which
pages need OCR. Existing fully readable PDFs avoid re-embedding. Web OCR opt-in
controls remain QA-05, not implicitly completed by this backend fix.

Focused PDF/web/job regression: 52 PASS. Real local OCR recovered the expected
advisor text on physical page 2 while preserving page 1. Parser benchmark on
five real PDFs/104 pages: median wall 0.8493 to 0.1194 s, sampled peak RSS
93,302,784 to 76,345,344 bytes; exact native text/layout hashes unchanged.
See PERFORMANCE_REPORT.md for scope and measurement limits. No provider egress.

Final worktree regression: **2,376 PASS, 2 opt-in live SKIP** in 255.80 s;
focused 52 PASS. Exact staged Git source exported without local files:
**106 app tests PASS** in 11.68 s. Preserve final JUnit and parser-run evidence;
remove intermediate stores/exports. Full-app goal remains active: end-to-end
OCR/index resource measurements, partially text-bearing scan pages, OCR/table
quality, UI OCR opt-in and native model quality still require work.

## 2026-10-23 — preserve existing journal compatibility

Restarting the actual idle local app exposed an upgrade failure that isolated
fresh-store tests missed: changing the job identity salt made the journal reject
old valid rows. Fixed validation to accept only the exact canonical legacy or
current identity; preserve historical rows unchanged, and use only current
identities for new admission. Corrupt identities continue to fail closed.
Migration/PDF/jobs regression: 33 PASS. The actual app was restored on port 8000,
with two documents still ready and five historical jobs retained. No journal
reset, document deletion, credential change or provider request was used.

Post-upgrade final regression: **2,378 PASS / 2 live SKIP**, 254.39 s. Clean
staged tree `4b9e11da8779b74f20893baf959dcdc9114757e9`: **108 app tests PASS**,
12.94 s. Current receipt replaces the pre-compatibility receipt at the same path;
the earlier 2,376-test receipt remains in commit `12ed6bd9`. Live local backend
coverage fields and exact UTF-8 frontend asset bytes were verified after restart.

Post-upgrade final regression: **2,378 PASS / 2 live SKIP**, 254.39 s. Clean
staged tree `4b9e11da8779b74f20893baf959dcdc9114757e9`: **108 app tests PASS**,
12.94 s. Current receipt replaces the pre-compatibility receipt at the same path;
the earlier 2,376-test receipt remains in commit `12ed6bd9`. Live local backend
coverage fields and exact UTF-8 frontend asset bytes were verified after restart.

Final worktree regression: **2,376 PASS, 2 opt-in live SKIP** in 255.80 s;
focused 52 PASS. Exact staged Git source exported without local files:
**106 app tests PASS** in 11.68 s. Preserve final JUnit and parser-run evidence;
remove intermediate stores/exports. Full-app goal remains active: end-to-end
OCR/index resource measurements, partially text-bearing scan pages, OCR/table
quality, UI OCR opt-in and native model quality still require work.
