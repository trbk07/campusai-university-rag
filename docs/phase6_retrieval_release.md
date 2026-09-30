# Phase 6 retrieval release — RC3

Phase 6 is approved around a generic, user-supplied document workflow. The
PDFs in `data/corpus/university` exist only to make release evaluation
reproducible; production does not assume their names, hashes, document types,
or content. At runtime, `IngestionJobManager` parses each uploaded file,
derives its SHA-256 `doc_id`, persists its chunks, and builds BM25 plus dense
indexes in the configured index directory. `CampusAIQueryService` searches
only the `doc_ids` selected for the current request.

## Locked contract

- Release candidate: `phase6-rc3`
- Public result schema: `retrieval-public-v1`
- Index schema: `hybrid-index-v2`
- Dense model: `BAAI/bge-m3`, revision `1`, 1024 dimensions, CPU
- Primary mode: deterministic `auto` routing with `hybrid_rrf` fusion
- RRF: `k=3`, BM25 weight `1.0`, dense weight `1.2`, candidate cap `40`
- Reranker: excluded (Phase 7)
- Threshold: fitted only on RC3 dev and bound to benchmark/index/model hashes

Exact code lookup uses a cheap exact-only path only when one code maps to one
document and a bounded candidate set. Multiple codes, documents, or excess
candidates are treated as ambiguous and fall back to contextual BM25+dense
RRF with an explicit trace reason. Filters are schema-validated and applied
before global per-retriever ranking and candidate truncation.

## Locked evidence

The benchmark contains 400 queries over 13 real documents: dev 140, test 130,
holdout 130, including 40 negative/adversarial queries. Source and template
leakage are zero. Three scan-only PDFs are accepted negative/review fixtures;
ten documents have persisted BGE-M3 indexes.

RC3 release results:

| Metric | Result |
|---|---:|
| Test auto-hybrid Recall@5 | 0.982906 |
| Holdout auto-hybrid Recall@5 | 0.957265 |
| Test BM25 Recall@5 | 0.880342 |
| Test dense Recall@5 | 0.863248 |
| Test auto-hybrid MRR | 0.808689 |
| Test auto-hybrid nDCG@5 | 0.851988 |
| Exact-code Recall@5 | 1.000000 |
| Routing accuracy | 1.000000 |
| Test/holdout negative FPR | 0.000000 / 0.000000 |
| Test p95 | 363.891 ms |

The paired bootstrap comparisons, per-category/language/difficulty segments,
cold/warm latency, and rejected RC1/RC2 remediation records are stored under
`evaluation/results`. Rejected candidates are retained rather than rewritten.

## Reproduction

From a clean checkout with the locked environment and cached model:

```powershell
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
.venv\Scripts\python.exe scripts\build_phase6_benchmark.py
.venv\Scripts\python.exe scripts\build_phase6_index.py
.venv\Scripts\python.exe evaluation\calibrate_phase6.py
.venv\Scripts\python.exe evaluation\run_phase6_release.py
.venv\Scripts\python.exe evaluation\run_phase6_security.py
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
.venv\Scripts\python.exe evaluation\run_phase6_operations.py
.venv\Scripts\python.exe evaluation\validate_phase6_release.py
```

No API secret is required. Hash embeddings are rejected for Phase 6 release
evidence. The generated index lives in the declared `.tmp/phase6-index`
workspace and is rebuilt from checksum-verified tracked PDFs.
