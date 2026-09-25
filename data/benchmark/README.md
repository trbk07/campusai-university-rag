# Benchmark annotations

`dev.jsonl` is a schema-valid 20-row university development benchmark. Its
evidence is manually anchored to the checked-in Phase 1/2 golden fixtures
(`golden-graduation` and `golden-prerequisites`); it is suitable for parser,
chunking, provenance, and citation regression, not for claiming retrieval
quality on a large external university corpus.

The application never reads this file at runtime; it is consumed only by
`evaluation/run_retrieval_eval.py`. A separate holdout corpus should be added
before tuning retrieval or reporting generalization metrics.
