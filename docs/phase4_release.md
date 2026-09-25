# Phase 4 release evidence — Basic RAG

## Decision

**Pass — 10/10 offline acceptance contract.** The Phase 4 benchmark uses a
tracked university-only fixture corpus built at runtime. It does not use any
`.tmp` financial artifact or live provider quota.

## Implemented

- Stable evidence context blocks preserving `chunk_id`, `doc_id`, document name,
  page, page range, section and content.
- Character and conservative token budgets with provenance-preserving content
  truncation and `truncated=true` markers.
- Explicit Vietnamese and English grounding prompts requiring JSON-only output,
  short answers, evidence-only claims and abstention when evidence is lacking.
- Strict answer/citation validation, duplicate citation removal and human-facing
  `[document, page]` formatting.
- Versioned query-answer cache with normalized questions, corpus/index version,
  prompt/model version, filters, mode and budget in a SHA-256 key.
- Corpus manifest includes a BM25 artifact hash; rebuilding BM25 or dense
  indexes changes the corpus version and invalidates old answers.
- Cache isolation across corpus versions and process-local single-flight locking.
- Safe deterministic abstentions may be cached; provider errors, invalid model
  output and retryable failures are never cached.
- Negative/out-of-corpus abstention and low-relevance policy.
- Deterministic end-to-end benchmark with answerable, multi-evidence, ambiguous
  and out-of-corpus university questions.

## Acceptance evidence

Run:

```powershell
.venv\Scripts\python.exe evaluation\run_phase4_basic_rag.py
.venv\Scripts\python.exe -m pytest -q --basetemp D:\Project\.tmp\pytest-phase4 tests\test_phase4_basic_rag.py tests\test_grounding.py
```

The canonical outputs are:

- [`phase4_basic_rag.json`](../evaluation/results/phase4_basic_rag.json)
- [`phase4_summary.md`](../evaluation/results/phase4_summary.md)

The acceptance thresholds are met: answerable answer success, citation
resolution/page/document accuracy, negative abstention, zero fabrication and
zero context-budget violations. The cache repeat pass avoided 22 fake LLM
calls; cache keys contain only a SHA-256 digest and no provider credentials.

## Live provider evidence

Offline acceptance remains the deterministic release gate. An opt-in live
Gemini contract test is available when a key is supplied only through the
environment:

```powershell
$env:RUN_LLM_INTEGRATION = "1"
$env:GEMINI_API_KEY = "<key supplied only in the environment>"
$env:PHASE4_LLM_MODEL = "gemini-3.8-flash"
.venv\Scripts\python.exe -m pytest -q tests\integration\test_phase4_gemini.py
```

The live test validates a real provider JSON response, grounded answer and
fixture citation. It is intentionally opt-in and is not required for offline
CI because quota/network availability is external state.

## Known limitations

The benchmark uses deterministic fixture LLM responses for offline acceptance.
Live provider quality, latency and quota behavior remain provider-contract
tests rather than a release gate.
