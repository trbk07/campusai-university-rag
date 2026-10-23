# CampusAI — Phase 12 UI

**UI IMPLEMENTATION STATUS: DONE — local single-user MVP, offline acceptance and usable local startup.**
Reviewed 15/10/2026 (Asia/Bangkok), by **Codex — Automated AI Review**.
This is not public deployment approval or live provider qualification.
Phase 13's local operational follow-up adds provider error codes, cooldown/manual
retry UX and bounded local HTTP/query admission. See [the review and recovery
evidence](../deployment/phase13/repository-review.md). Phase 12 acceptance remains
a historical source-bound snapshot; recovery evidence binds the subsequent code.
Roadmap: [plan.md](../../plan.md). Reference: the CampusAI screenshot supplied
in the owner's chat; no source data or fabricated documents were copied from it.

## Architecture and folder boundaries

The existing Python WSGI server serves a small frontend with native ES modules.
No React, Tailwind, frontend production dependency or build service is added.
Static files ship with the Python package through setuptools package-data.

```text
src/campusai/
  ui/                         interface only
    pages/index.html          semantic shell, four views, native dialogs
    styles/tokens.css         shared colors, typography, spacing
    styles/layout.css         header, sidebar, workspace, source panel
    styles/components.css     controls, cards, chat, upload, dialogs
    styles/responsive.css     desktop, tablet, mobile and drawer rules
    scripts/app.js            routing, drawers, keyboard/focus behavior
    scripts/api.js            HTTP client, upload progress, timeout/microcopy
    scripts/shared.js         state/events, escaped text, SVG icons
    features/documents.js     library, filters, collections, upload/jobs, PDF
    features/chat.js          conversation, citations, feedback, safe renderer
  web.py                      HTTP routing and existing telemetry contract
  web_documents.py            controlled storage and document transport adapter
tests/ui/                     isolated browser fixtures and acceptance tooling
```

Each UI folder contains at most four source files. Runtime data belongs to the
configured store/index, never the UI source folder. Retrieval, grounding,
temporal, multihop and KG algorithms remain unchanged. Small lifecycle fixes
release completed job bindings on deletion, purge local response caches, and
validate malformed PDF bytes without leaving Windows native file handles open.

## Four tabs

| Tab | Implemented requirement | Verified |
|---|---|---|
| Trợ lý AI | Source selection, scope-specific bounded history, suggestions, one-submit composer, safe text/list/table rendering, evidence/overload/error/timeout states, source cards, original PDF page, feedback | Real HTTP/worker/index E2E with deterministic test provider; browser single-submit, stale-source, XSS, timeout and retry checks |
| Tài liệu của tôi | Drag/drop or file chooser, file validation, measured upload progress, actual worker progress, ready/review/error states, search, metadata/status filters, detail, scope selection, deletion confirmation | Real PDF upload/ready, duplicate, encrypted/corrupt/oversized/scan review, job cancel/retry and delete/reupload tests |
| Bộ sưu tập | Counts and groups from actual `document_type`; unrecognized metadata goes to Chưa phân loại; opening a collection filters the library and allows selection | Browser opens a real uploaded document's collection and selects it for chat |
| Hướng dẫn | Five onboarding steps, expandable FAQ, PDF scan/version explanations, actual local/AI limits | Browser navigation and FAQ; axe audit |

Source selection never silently expands. Search/year/program/status filters
change the library; the actual question scope is the explicitly checked IDs
shown beside the composer. Conversation history includes at most six turns,
2,000 characters per turn, and only from the same document scope.
The welcome screen contracts completely once a question is submitted.

## API mapping

| Route | Status | Contract / reuse |
|---|---|---|
| `POST /api/query` | Existing, preserved | `CampusAIApplication.query`; unchanged `grounding-public-v2` answer. Request ID returned in header for feedback. Managed uploads require existing, ready, authorized selected IDs. Legacy query-only adapters retain their scope contract. |
| `GET /health`, `/live`, `/ready`, `/metrics` | Existing, preserved | Existing application probes/telemetry |
| `GET /api/documents` | Added | Registry summaries, scoped jobs, real upload limits/capability; no private paths or chunk bodies |
| `POST /api/documents/upload` | Added | Raw `application/pdf`, percent-encoded filename in `X-Filename`; content-addressed controlled storage → existing job manager |
| `GET /api/documents/{id}` | Added | Safe metadata and actual ready state (ingestion succeeded **and** both indexes exist) |
| `GET /api/documents/{id}/file` | Added | Authorized managed upload only; source bytes must hash to the document ID; native PDF viewer uses `#page=N` |
| `POST /api/documents/{id}/locate` | Added | Resolve the physical quote page inside an authorized multi-page chunk; inspect at most 16 pages, never invent a match or PDF highlight |
| `DELETE /api/documents/{id}` | Added | Existing full deletion + uploaded file removal, retriever eviction, corpus manifest refresh, response cache purge and terminal job cleanup |
| `GET /api/jobs/{id}` | Added | Redacted existing job fields; original state/stage/progress/ready semantics |
| `POST /api/jobs/{id}/cancel` | Added | Existing cooperative cancellation; no promise of immediate interruption |
| `POST /api/jobs/{id}/retry` | Added | Existing worker retry only for retryable failed jobs |
| `POST /api/feedback` | Added | Known response ID + `helpful`/`incorrect`, local JSONL; no question/document text or secrets |

No browser-supplied filesystem path, authorization flag or execution mode is
trusted. Trusted `campusai.authorized_doc_ids` middleware limits list, metadata,
source, delete, jobs, query and feedback. New upload ownership assignment under
a restricted session is deliberately unavailable until real ownership
middleware exists. The default loopback host is explicitly single-user.

Original source previews have separate verbatim excerpts. No artificial PDF
highlight or thumbnail is drawn; the available contract has no coordinates.
Missing PDFs and modified source bytes fail closed. Feedback references expire
after a process restart or 24 hours and the in-memory map is bounded to 1,000.

## Design system

`tokens.css` centralizes the requested palette: primary `#2563EB`, hover
`#1D4ED8`, soft `#EFF6FF`, dark `#1E40AF`; background `#F7F9FC`, white surfaces,
muted `#F1F5F9`; text `#0F172A`/`#475569`/`#64748B`; border `#E2E8F0`;
success `#15803D`, warning `#B45309`, danger `#DC2626`. Status backgrounds and
the restrained violet feature accent are also tokenized.

Spacing uses 4/8/12/16/24/32/48px tokens. Cards use 12–16px corners; controls
are generally 44px with visible focus rings. Font stack: Inter, Be Vietnam Pro,
system UI, Segoe UI; no external font request is needed. Body answers are 14px
with 1.75 line height. Icons are consistent local SVGs with functional labels.
Reduced-motion preference disables transitions and spinner motion.

## Validation and screenshots

| Check | Result | Evidence |
|---|---|---|
| Initial backend/UI contracts | **26 passed, 0 failed** | [Initial JUnit](focused-tests.xml) |
| Full offline suite | **1,604 passed, 2 skipped, 0 failed** | [Current JUnit](local-offline-tests.xml); [initial suite](offline-tests.xml) retained; skips are opt-in live-provider tests |
| Local launch / focused integration | **38 passed, 0 failed** | [Current JUnit](local-launch-tests.xml) |
| Chromium browser interactions | **29 checks passed**, no browser script errors | [Browser results](evidence/browser-results.json) |
| Responsive | Six requested viewports, zero horizontal overflow, composer visible | Screenshots and browser results |
| Automated accessibility | Zero axe WCAG A/AA findings in six welcome viewports, library, guide, collections, upload/scope dialogs and grounded answer/source panel | Browser results |
| Security/lifecycle | Scope denials, traversal/static allowlist, unmanaged source protection, actual Windows junction rejection, modified-PDF hash rejection, escaped unsafe HTML, cross-origin writes, feedback validation, no stale access after deletion | Backend tests and browser results |
| Python packaging | Offline wheel build succeeded; all 10 UI assets match source bytes | [Package check](evidence/packaging.json) |

Desktop [1440×900](evidence/welcome-1440x900.png),
[1280×800](evidence/welcome-1280x800.png),
tablet [1024×768](evidence/welcome-1024x768.png),
[768×1024](evidence/welcome-768x1024.png),
mobile [390×844](evidence/welcome-390x844.png),
[360×800](evidence/welcome-360x800.png).
Grounded answers: [desktop](evidence/answer-1440x900.png),
[mobile](evidence/answer-390x844.png).

The E2E creates and uploads a real PDF through the UI, polls the real worker,
uses actual BM25/index/grounding code with a test-only local provider, compares
the citation quote with the PDF's text, opens physical page 1, persists feedback,
deletes the document and verifies HTTP 404 for the source. Timeout, overload,
503 and malicious response cases use network mocks **only in browser tests**.
The 45-second timeout is tested with a virtual browser clock, not claimed as
live provider latency. Initial UI acceptance made no LLM calls; subsequent local
startup verification used real Gemini requests as described below.

The suite initially needed one archived historical preflight restored with the
repository's verified artifact tool. No historical source, benchmark, report,
release flag, R-01 or R-02 result was rewritten. See
[acceptance receipt](evidence/acceptance.json) for source/artifact SHA-256 bindings.

## Clean setup and reproduction

From the repository root, with Python 3.11–3.14 and `uv`:

```powershell
uv sync --extra dev --extra feasibility
uv run python -m scripts.operations.local --open-browser
# Open http://127.0.0.1:8000
```

Or double-click `start-campusai.cmd`. The launcher loads `.env`, preserves
explicit environment settings and uses the existing ignored key with
`configs/product_llm.yaml`. It performs no inference probe at startup, never
rotates keys/models and never changes billing. A repeated launch reuses the
running app; an older unconfigured server gets a restart hint. Missing keys
are reported before model loading. The normal embedding model remains configurable
through `CAMPUSAI_DENSE_MODEL`; model dependencies/weights must be available.
Explicit corpus-bound calibration still requires a matching index fingerprint;
the local upload host does not implicitly reuse the frozen evaluation corpus.

Offline API and browser reproduction (no model download or paid provider):

```powershell
.venv\Scripts\python.exe -m scripts.dev.manage_artifacts restore evaluation/results/phase8-post-fix-preflight-20261012.json
.venv\Scripts\python.exe -m pytest -q --junitxml=docs/ui/local-offline-tests.xml
.venv\Scripts\python.exe -m pytest -q tests/test_local_launcher.py tests/test_cross_language_grounding.py tests/test_web.py tests/test_web_documents.py tests/test_api_adapter.py tests/test_ingestion_jobs.py --junitxml=docs/ui/local-launch-tests.xml
npm.cmd ci --prefix tests/ui
# Terminal 1: isolated test host, never the production server
.venv\Scripts\python.exe -m tests.ui.serve_fixture --root .tmp/ui-browser --port 8012
# Terminal 2, from repository root (installed Chrome required):
node tests/ui/browser_smoke.cjs
.venv\Scripts\python.exe -m tests.ui.capture_evidence
```

`UI_CHROME` overrides Chrome's executable path. Browser dependencies are test
tools only. The test host uses a separate `.tmp/ui-browser` store, fallback
embeddings and deterministic test provider; it never reads API credentials.
The browser test only cleans the five named `Enrollment*.pdf` fixtures in its
isolated test store. Set `UI_BASE_URL` when the default port is already in use.
Stop the test host before removing its temporary directory. Screenshots,
JUnit reports and the acceptance receipt are retained as audit evidence.

## Files and gates

Added: `src/campusai/ui/**`, `web_documents.py`, `start-campusai.cmd`,
`scripts/operations/local.py`, local/cross-language tests, `tests/test_web_documents.py`,
`tests/ui/**`, this document and evidence. Updated: `web.py`, `serve.py`,
ingestion `jobs.py`/`validate.py`, local cache clear APIs, existing web tests,
Python package-data, `.gitignore`, README and the Phase 12 entries in `plan.md`.

| Phase 12 UI item | Status / basis |
|---|---|
| P12-UI-01 Audit/contracts | DONE — existing adapters reused; mapping above |
| P12-UI-02 Design/layout | DONE — tokens, four views, six viewport screenshots |
| P12-UI-03 Documents | DONE — real uploads, worker states, details, deletion |
| P12-UI-04 Chat | DONE — actual request/answer contract, selection, history, error/timeout |
| P12-UI-05 Sources | DONE — real doc/page/quote, source hash and access checks |
| P12-UI-06 Collections/guide/feedback | DONE — metadata groups, onboarding, persisted feedback |
| P12-UI-07 Responsive/a11y/hardening | DONE within tested MVP scope — results above |
| P12-UI-08 Acceptance/handoff | DONE — offline/backend/browser evidence and source bindings |

Remaining product limits: real provider quality/latency/availability are not
qualified as a workload here; R-01/R-02 remain **DEFERRED — NOT PASSED**. Authentication,
multi-user ownership, durable job history, large-corpus storage/quotas and public
hosting remain Phase 13/14. Native PDF rendering and virtual-keyboard behavior
on physical iOS/Android devices were not tested. Automated axe/keyboard checks
are evidence of the exercised states, not a blanket WCAG certification.

## Local use verification — 15/10/2026

The owner's 59-page uploaded PDF finished indexing with the existing BGE-M3
model. The local app starts with the existing credential and approved Gemini
3.8 Flash profile; no billing setting was changed. That model has a Free Tier
entry in [Google's official pricing](https://ai.google.dev/gemini-api/docs/pricing).

Real queries succeeded in English and Vietnamese on the English PDF, with
grounded answers and verbatim citations. Deterministic thresholds are unchanged:
cross-language prompts retain claims in the source language while presenting
the answer in the requested language. Unsupported claims still fail closed.
The composer now exposes Vietnamese/English reply selection.

The source viewer resolves the quote's physical page inside its chunk range.
The verified Vietnamese example had a chunk beginning on page 4 and its exact
quote on physical page 5; preview opened page 5. The public answer schema is
preserved. [Live HTTP smoke](evidence/local-live-smoke.json),
[English smoke](evidence/local-live-smoke-en.json),
[actual UI check](evidence/local-live-browser.json),
[actual local UI screenshot](evidence/local-live-view.png).
The UI check reused the verified cached answer and did not delete or modify
the owner's PDF. Readiness reported a configured LLM and one loaded document.

All five application query attempts remain accounted for: two grounded answers,
one rejected cross-language claim before the prompt fix, and two provider
failure responses (including the sandbox connection restriction and HTTP 503).
Summaries are retained under `evidence/local-live-*.json`. Recovery respected
the existing cooldown and used the same model/key. No automatic retry loop or
credential failover was added. These few requests demonstrate local use and
do not qualify R-01/R-02 or guarantee provider availability.

## Batch upload and question-load verification — 23/10/2026

The upload dialog accepts at most five PDF files per batch, displays progress
per file, sends each file concurrently and keeps failed files available for a
manual retry. The local runtime uses three ingestion workers, up to eight queued
jobs and four concurrent queries. Upload body reading and per-file validation /
write no longer hold the shared documents lock; registry, job admission and
index publication retain their own synchronization. The UI cap is per batch;
the server's existing per-file size/page limits still apply.

The updated browser smoke passed **39/39 checks**, including rejecting a six-file
selection, uploading five PDFs through the UI until all were ready, chat/source/
deletion flows, six viewport sizes, axe A/AA checks and zero script errors. The
full offline regression passed **2,368 tests** with **2 opt-in live-provider
tests skipped**.

An additional local-only HTTP workload used five generated one-page PDFs totaling
4,749 bytes with BGE-M3 in offline mode. All five upload requests were accepted
in **0.113 seconds**; all indexes were ready in **9.619 seconds**, including the
cold model load. A separate 100-question EN/VI run on four query workers returned
100/100 successful HTTP/API responses in **4.853 seconds** (p95 **0.324 seconds**).
The deterministic test provider produced checked citations for 72 questions and
abstained on 28 unsupported/ambiguous probes. These figures measure local
pipeline capacity and grounded-path behavior; they do not measure a live model's
answer quality, provider latency or quota.

## Manual local OCR — 23/10/2026

Document details offer OCR for scan/mixed PDFs in review. `POST
/api/documents/{id}/ocr` with an empty JSON object starts a background job on
the existing source. The server checks trusted scope, source hash, active work
and readiness, owns limits (at most 50 scan pages / 120 seconds), and rejects
client option overrides. No PDF reupload or external model inference is needed.
Explicit retry after OCR review preserves history; it never retries automatically.

Focused regression: 37 PASS; full worktree 2,384 PASS / 2 live SKIP. Clean Git
source: 114 app tests PASS. Browser E2E: 41/41 PASS, including OCR dialog axe,
admission-error recovery and actual local OCR becoming ready. Receipts:
`evidence/ocr-ui-tests.xml` and `evidence/ocr-browser-results.json`. End-to-end
load, OCR-table fidelity and native answer quality remain in the full-app audit.

## Manual local OCR — 23/10/2026

Document details offer OCR for scan/mixed PDFs in review. `POST
/api/documents/{id}/ocr` with an empty JSON object starts a background job on
the existing source. The server checks trusted scope, source hash, active work
and readiness, owns limits (at most 50 scan pages / 120 seconds), and rejects
client option overrides. No PDF reupload or external model inference is needed.
Explicit retry after OCR review preserves history; it never retries automatically.

Focused regression: 37 PASS; full worktree 2,384 PASS / 2 live SKIP. Clean Git
source: 114 app tests PASS. Browser E2E: 41/41 PASS, including OCR dialog axe,
admission-error recovery and actual local OCR becoming ready. Receipts:
`evidence/ocr-ui-tests.xml` and `evidence/ocr-browser-results.json`. End-to-end
load, OCR-table fidelity and native answer quality remain in the full-app audit.
