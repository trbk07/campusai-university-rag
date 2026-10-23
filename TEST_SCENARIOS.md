# App test scenarios

Cycle: 2026-10-23. See [QA_AUDIT.md](QA_AUDIT.md) for open findings.

| Flow | Expected behavior | Evidence |
|---|---|---|
| Clean startup | Source archive imports app and local launcher without local-only modules. | Initial archive fails; repaired candidate covered by 98-test clean-source run. |
| Upload lifecycle | Real PDF upload, worker/index readiness, duplicate validation, retry, source/feedback/delete/re-upload and five concurrent uploads remain consistent. | `tests/test_web_documents.py`, `tests/test_ingestion_jobs.py`; clean candidate PASS. |
| Parallel queries | Four independent EN/VI requests retain their own response content and request ID. | `tests/test_web.py`; clean candidate PASS. |
| Natural phrasing | Accents/no accents, page-count variants, real follow-up versus topic change, ambiguous multi-document scope and injection checks. | `tests/test_natural_conversation.py`; clean candidate PASS. Its 100-turn check is structural PDF metadata, not 100 verified live model answers. |
| Page/multiple intents | Exact physical page/range, invalid pages and page-count plus content question preserve scope and both intents. | `tests/test_document_question_plans.py`; clean candidate PASS with deterministic local provider. |
| UI end to end | Six-file rejection, five uploads until ready, chat/citations/source/delete, mobile/desktop and accessibility. | Prior 39/39 browser smoke documented in `docs/ui/phase12-ui.md`; not rerun in this packaging cycle. |
| Live AI quality | Verify correctness, completeness, groundedness, naturalness and hallucination against reviewed source/gold. | OPEN: P5 native qualification; no new provider calls. |
| Large/scan PDF load | Verify extraction/table/OCR and latency/RSS under five realistic PDFs plus query load. | OPEN for current app performance cycle; unit PDF regressions alone do not prove this workload. |

All current-cycle API/worker scenarios use isolated local test stores and no
external provider. Existing production/user documents must not be deleted.
