# Phase 3 release evidence

## Implemented

- `EmbeddingProvider` abstraction with deterministic `HashEmbeddingProvider`
  and lazy `SentenceTransformerEmbeddingProvider`.
- Dense index schema v2 with corpus hash, model revision, provider,
  dimension, item count, build time, and checksum manifest.
- Atomic index writes and typed fail-closed errors for missing, corrupt,
  version-mismatch, and corpus-mismatch indexes.
- Corpus-level manifest plus per-document dense/BM25 indexes.
- Subprocess restart test and deterministic hash-provider tests.
- Frozen `retrieval_test.jsonl` with 100 validated records and a benchmark
  runner reporting Recall@1/3/5, MRR, and p50/p95/p99 latency.
- Leakage-safe calibration split and threshold selector. The cached
  `bge-reranker-v2-m3` calibration run selected threshold `0.46367466` with
  Recall `1.0` and false-positive rate `0.0` on the 20-row calibration split.
- Benchmark runner can consume that locked artifact with
  `--calibration-report`; threshold provenance is persisted in the report and
  the benchmark is restricted to the artifact's calibrated retrieval mode.

## Current evidence

```text
Phase 3 persistence/benchmark tests: pass
Full repository: 97 passed, 1 skipped
Benchmark test split: 100 valid records
Compileall: pass
Multilingual benchmark: passed using the locally cached BAAI/bge-m3 model
```

Canonical artifacts:

- `evaluation/results/phase3_hash.json`
- `evaluation/results/phase3_multilingual.json`
- `evaluation/results/phase3_summary.md`

The multilingual dense and hybrid modes reached Recall@5 0.95 on the
100-query benchmark. Latest warm p95 latency was 52.567 ms for dense and
52.187 ms for hybrid. Dense MRR was 0.686667 and hybrid MRR was 0.705; the
dense MRR threshold is therefore not met. Negative-query false-positive rate
was 1.0 for both modes. The corpus contains only two indexed golden
documents, so this is smoke/regression evidence, not production-scale proof.
The release remains conditional.

The hash provider remains accepted for deterministic development fallback use.
Negative-query false-positive/abstention metrics and a BM25 p99 outlier should
be addressed before final production acceptance.

## Acceptance thresholds

- Hash Recall@5: >= 0.70
- Multilingual dense Recall@5: >= 0.85
- Hybrid Recall@5: >= 0.90
- Multilingual MRR: >= 0.70
- Warm p50/p95 query latency: <= 150/500 ms on the benchmark host
- Restart load: <= 2 seconds on the benchmark host

The benchmark command is:

```powershell
.\.venv\Scripts\python.exe -m evaluation.run_retrieval_benchmark `
  --benchmark data\benchmark\retrieval_test.jsonl `
  --index-dir .tmp\phase3-index `
  --output evaluation\results\phase3_hash.json
```
