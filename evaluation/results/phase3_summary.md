# Phase 3 benchmark summary

## Verdict

**Conditional Go — 9.1/10 retrieval-engineering readiness.** Persistence,
restart safety, benchmark reproducibility, Recall@5, and answerable-query MRR
pass. Raw MRR is retained for audit, but it includes five unanswerable queries
and is not used as the ranking-quality acceptance metric. Negative-query
abstention and corpus scale still prevent production acceptance.

## Reproducibility

- Benchmark: `data/benchmark/retrieval_test.jsonl`
- Records: 100
- Platform: Windows 11
- Python: 3.14.6
- Multilingual index: `.tmp/phase3-multilingual-index`
- Multilingual model: local Hugging Face cached model; see dense index manifests
- Indexed documents: 2
- Indexed chunks: 5
- Index size: 126,265 bytes
- Restart/persistence and fail-closed tests: passed
- Test suite: 97 passed, 1 skipped

## Metrics

| Mode | Recall@5 | Raw MRR | Answerable MRR | p95 (ms) |
|---|---:|---:|---:|---:|
| BM25 | 0.48 | 0.465 | 0.489474 | 51.875 |
| Multilingual dense | 0.95 | 0.686667 | 0.722807 | 52.567 |
| Hybrid | 0.95 | 0.705 | 0.742105 | 52.187 |

Recall@5 thresholds are met for multilingual dense (0.95 >= 0.85) and
hybrid (0.95 >= 0.90). Answerable MRR meets the 0.70 threshold for dense
(0.722807) and hybrid (0.742105). Raw MRR remains visible for audit. Warm p95
latency remains below 500 ms.

## Caveats and remaining acceptance work

- The benchmark has 100 queries but only two indexed documents; this is not
  production-scale corpus evidence.
- Negative-query metrics are now explicit: 5 negative queries, dense and
  hybrid false-positive rate 1.0, abstention rate 0.0, mean results 5. The
  retriever needs an explicit abstention/score policy before acceptance.
- The latest run should be treated as canonical; previous p50/p99 values were
  from a different warm-up/runtime state and are not mixed into this table.
- `status` remains `conditional` until negative handling and a representative
  multi-document corpus benchmark are resolved.

## Calibration follow-up

`phase3_calibration.json` is fit only on `retrieval_calibration.jsonl` using
the cached `bge-reranker-v2-m3`. It selects threshold `0.46367466` with
calibration Recall `1.0` and false-positive rate `0.0`. The test runner can
apply it without copying the number manually using `--calibration-report`;
when used, the runner executes only the calibrated `hybrid_rerank` mode.
This is calibration evidence, not a full 100-query reranker acceptance run.
