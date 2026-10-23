# App performance evidence

Cycle: 2026-10-23. No new speed claim is made for the source-packaging repair.

| Workload | Before | After / observation | Limits |
|---|---|---|---|
| Two real PDFs, 34 + 13 pages, local hash-model profile | Sequential 4,980 ms | Parallel 4,515 ms (~9.3% lower wall time) | Earlier same-profile baseline before worker count increase; not the BGE workload. |
| Five generated one-page PDFs, total 4,749 bytes, BGE-M3 offline | No comparable old five-file BGE baseline recorded | All accepted in 0.113 s; ready in 9.619 s including cold model load | Prior cycle, tiny fixtures; does not predict five large/scanned PDFs. |
| 100 EN/VI local API questions, four query workers | No matched before baseline | 100/100 HTTP success, 4.853 s wall time, p95 0.324 s | Deterministic test provider: 72 checked citations, 28 fail-closed abstentions. Not live model accuracy or latency. |
| Clean-source app correctness | Import fails on published source | Exact staged Git export: 98/98 tests PASS in 11.49 s | Test duration is not user-request latency. Earlier minimal candidate: 10.62 s. |

## Real-PDF parser cycle

Same five public university PDFs, 104 pages, 28,184,916 bytes; three workers,
three fresh-process runs per version. Baseline source: commit `3a04b7f1`.
The parser unnecessarily requested embedded image bytes although it uses only
text/font metadata. Excluding those bytes reduced median parser wall time from
**0.8493 to 0.1194 seconds** and median sampled peak process RSS from
**93,302,784 to 76,345,344 bytes** (~18.2% lower). RSS is sampled every 10 ms;
it is not a guaranteed absolute peak or the memory of the whole app/model.
Exact native text, physical-page and layout hashes match for all five PDFs;
scan-only pages remain unread until OCR, rather than being claimed as text.

Reproduce with project `.venv` Python and `PYTHONPATH=src`:
`python -m scripts.operations.benchmark_pdf_parser --workers 3` followed by
`data/corpus/university/` files `uet_admission_2024.pdf`, `uet_admission_2025.pdf`,
`uet_computer_engineering_program.pdf`, `uet_electronics_program_2023.pdf`, and
`uet_masters_admission_2022.pdf`. Raw runs, input hashes and content-equivalence
checks: [parser evidence](docs/ui/evidence/pdf-parser-batch.json).

A separate real RapidOCR run on a synthetic mixed PDF succeeded in 2.339 s,
OCRing only physical page 2 (average engine confidence 0.989326), retaining native
page 1 and skipping blank page 3. The recognized advisor text was checked against
the known fixture. Engine confidence alone is not proof of general OCR accuracy.

Outstanding: full upload/OCR/index peak RSS and latency for realistic batches,
table/scan extraction quality, slow/disconnected client behavior under load,
and live provider latency/quality.
Provider quota remains independent of local query-worker capacity: four local
query slots do not imply four Gemini requests in flight or unlimited API usage.

Existing detailed runtime/profile notes: [Phase 12 handoff](docs/ui/phase12-ui.md).
