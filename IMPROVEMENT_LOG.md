# App improvement log

## 2026-10-23 - clean-source reproducibility

Exporting pushed commit 0ef54f90 exposed missing runtime dependencies and an
older worker/index-builder interface. Fix commit 3a04b7f1 retains the runtime
modules in Git. Exact clean staged source passed 98 app tests in 11.49 s;
the minimal candidate previously passed 98 tests in 10.62 s. The original
import failure is retained in QA history; no live provider was called.

## 2026-10-23 - mixed PDFs and parser memory

Commit 12ed6bd9 detects unread image/vector pages, selectively OCRs physical
pages, preserves native content and rejects incomplete OCR. Four pre-fix
failures reproduced silent missing scan content. Cache/job identities and
legacy readiness are checked. Five real public PDFs (104 pages, 28,184,916
bytes) retained exact native text/layout hashes while median parser time
fell from 0.8493 to 0.1194 s and sampled peak RSS from 93,302,784 to 76,345,344
bytes. Real local OCR recovered the expected advisor text on page 2, retained
native page 1 and skipped blank page 3. See PERFORMANCE_REPORT.md for limits.
Pre-compatibility regression: 2,376 PASS / 2 live SKIP; focused 52 PASS;
clean Git source 106 app tests PASS. Receipt retained by commit 12ed6bd9.

## 2026-10-23 - preserve existing job journals

The real local restart exposed a policy-upgrade failure missed by fresh-store
tests: new job identity validation rejected valid historical journal rows.
Commit 49a0fe52 accepts only exact canonical old/current identities, retains
history and uses current identities for new work; forged identities fail closed.
Existing app recovered with two ready PDFs and five jobs. No reset/deletion or
credential change. Migration/PDF/jobs 33 PASS; whole worktree 2,378 PASS /
2 live SKIP in 254.39 s; clean Git app source 108 PASS in 12.94 s. Receipt:
docs/ui/evidence/pdf-ingestion-tests.xml.

## 2026-10-23 - manual local OCR on the web

Commit 6ce75659 adds the document-detail OCR action without a second upload.
Explicit retry preserves job history; no automatic resend. Server-owned caps
are at most 50 scan pages/120 seconds. Source hash, trusted scope, active/ready
state and queue admission are checked; client limit overrides are rejected.
Admission errors remain visible and allow manual recovery. Recognition is local.
Focused OCR/web/PDF/jobs 37 PASS; full worktree 2,384 PASS / 2 live SKIP in
258.03 s; clean Git app source 114 PASS in 11.95 s. Browser E2E 41/41 PASS,
including axe OCR dialog and real local OCR after simulated admission failure.
The new browser flow needed scoped selectors and a wait for dialog loading.

Full-app goal remains active: full upload/OCR/index load and RSS, partially
text-bearing scan pages, OCR/table fidelity and current-source native model
quality remain open. Grounding thresholds and release status are unchanged.
