# App performance evidence

## 2026-10-27 - native100/10MB gate PASS

QA-03c/QA-08d DONE in the fixed local CUDA lab:20/20 fresh uploads of the same
100-page,10,243,313-byte native fixture become ready. Nearest-rank p95 is
12.246s (gate15s),maximum14.158s,minimum11.010s. Decimal MB=1,000,000 bytes;
the fixture contains actual selected academic pages, no filler/padding. Every
run preserves all100 exact parsed pages, source hash and372 chunk contents/IDs
in BM25 and real1024-dimensional BGE-M3 dense indexes. Each owned upload/index
is deleted before the next run; original user stores are never modified.

Physical PDFMiner table decoding now uses up to4 spawned processes per large
PDF (maximum12 with the default3 ingestion jobs). Table semantics are assembled
in original page/table order, retaining continuation headers and semester scope.
Small files remain sequential; a broken pool discards partial results and uses
the sequential path. All tables in35 PDFs/368 pages match the old extractor
exactly.625 related tests PASS across two disjoint suites.

The serial pre-fix pilot took25.301s and the first parallel pilot14.768s. These
single observations are not before/after p95 estimates; cold-decoder/OS-cache
effects limit a causal speedup claim. The profiled serial pipeline spends24.773
of27.515s in table extraction; profiling adds overhead. A later matched warm
table-only observation is3.309s serial/1.556s parallel, with identical64 tables.
The final20-run gate is separate from those diagnostics.

Environment:Windows11,Python3.14.6,20 logical CPUs,25,480,257,536 bytes RAM,
RTX4060 Laptop8GB,torch2.14.0+cu126,BGE-M3 float32/default batch8,3 ingestion
workers,loopback HTTP and100ms polling. Model startup42.513s is measured outside
the warm upload-to-ready gate. Both model and OS cache are warm; PDF parsing,
table extraction,chunking and both indexes are rebuilt on every run. No answer
provider is configured. This is not scan/OCR speed,first-launch latency,remote
upload bandwidth or concurrent-five-large-PDF qualification.
[Raw runs, source/runtime bindings and reproduction](docs/ui/evidence/native100-performance-20261027.json).

The following performance results are historical baselines.

2026-10-27 visibility repair: isolated ingestion of the actual18-page CS2019
scan completes in33.610s, including27.369s local Tesseract OCR on all18 pages.
No provider/index calls or source changes. This single scan observation is not
a p95, before/after speedup or native100-page/10MB qualification. Coverage-v3
reuses unaffected v2 chunks after checking visible source glyphs.
[Bound observation](docs/ui/evidence/pdf-visibility-20261027.json).

Latest cycle:2026-10-25. [Current hybrid/read-path evidence](docs/ui/evidence/hybrid-coverage-20261025.json).

Same7-document library after reindexing,17 retained job records:20 users,400
ordinary read requests,400/400 HTTP200,p95 0.478s versus0.751s before the final
metadata optimization. Endpoint p95:library0.429s,local PDF facts0.497s. Request
snapshots eliminate repeated selected-source checks;job-path validation is
reused only within one listing. File reads,delete/retry and row authorization
still validate normally. No provider calls were made.

Existing-library OCR/reindex observation:5/5 documents,268 pages,40.65s total;
this excludes initial upload/startup and is not a p95 or a speedup comparison.
All native lines and original source hashes were checked. Current Chrome lab:
9/9 sessions PASS,max LCP308ms/INP104ms/CLS0.0109. Real AI streaming and the full
100-page/10MB workload remain unqualified. The earlier100-page/6.17MB result
must be requalified under coverage-v2;its historical ready flag did not audit
same-page raster regions.

Earlier read-path cycle: [raw measurements and bindings](docs/ui/evidence/web-read-performance-20261025.json).

| Current workload | Before | After | Scope |
|---|---|---|---|
|20 users,400 alternating library/local page-count requests|234 HTTP200,166 HTTP429;p95 2.737s|400 HTTP200,0 HTTP429;p95 0.189s|93.1% lower p95 for these ordinary read operations;0 provider calls,all7 original documents retained.|
|Initial layout,200ms document-response delay on both versions|Desktop CLS0.1022|Desktop CLS0.0109;9/9 viewport sessions PASS|Actual app,Chrome lab;not field/physical-mobile data.|
|100 native pages,6,171,517 bytes;20 fresh uploads|No matched older end-to-end measurement|20/20 ready;p95 11.506s,max11.700s|Warm CUDA BGE app,100ms polling;source SHA/page count checked,only owned uploads deleted. Does not close100-page/10MB gate.|

Registry reads reuse a compact projection with live file identity checks under
the existing writer locks. Cheap page counts no longer reserve model slots;
content/composite queries still do. Real AI streaming latency,larger PDF workload
qualification and remaining quality/recovery gates stay open.

Historical source-packaging cycle:2026-10-23. No speed claim was made for that repair.

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

Manual web OCR now schedules local work without a second upload and retains
server caps of at most 50 scan pages / 120 seconds. Its browser flow was verified
with actual OCR and error recovery (41/41 E2E checks). No matched throughput
measurement was performed for this UI change, and test-suite duration is not
reported as OCR latency. Full upload/OCR/index load remains outstanding.


## Full five-PDF BGE/OCR measurement

Same public inputs (104 pages, 28,184,916 bytes), three workers, offline BGE-M3 and real local OCR; one fresh-process run per version. Upload acceptance: 0.154 to 0.165 s. Overall terminal time: 212.73 to 226.62 s; **no overall speedup and only 3/5 ready in either run**. The fixed run has zero failed jobs, but the 32/35-page scans remain in review after exhausting the OCR attempt budget. Peak sampled RSS: 3.51 to 3.48 GB, not a meaningful memory improvement from one run. Library probe p95: 0.360 to 0.136 s. Six-page OCR phase: 102.14 to 39.03 s, with matching recognized text/chunk count. A separate three-page OCR comparison went from 28.47 s / 167 process threads to 10.83 s / 50 threads; all three text hashes/confidence values match exactly. These are bounded observations, not general OCR accuracy or p95 SLO claims.

Raw before/after reports, hardware, input hashes, original registry-race reproduction and instrumentation caveats: [runtime evidence](docs/ui/evidence/pdf-runtime-load.json). A probe-relative stage timestamp bug in the historical report is explicitly excluded from timing conclusions; the reusable benchmark script is corrected. Large-scan completion and OCR/table fidelity remain open.
