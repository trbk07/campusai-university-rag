# Benchmark annotations

`dev.jsonl` is a schema-valid 20-row university development benchmark. Its
evidence is manually anchored to the checked-in Phase 1/2 golden fixtures
(`golden-graduation` and `golden-prerequisites`); it is suitable for parser,
chunking, provenance, and citation regression, not for claiming retrieval
quality on a large external university corpus.

The application never reads this file at runtime; it is consumed only by
`evaluation/run_retrieval_eval.py`. A separate holdout corpus should be added
before tuning retrieval or reporting generalization metrics.

`retrieval_test.jsonl` is the Phase 3 frozen 100-row test split. It includes
Vietnamese, English, and mixed queries across fact, table, calculation,
comparison, multi-hop, exact-code, and negative categories, with easy/medium/
hard labels and document/page evidence. It is intended for reproducible metric
and performance reports; the checked-in golden evidence is a contract fixture,
not a claim about external-corpus generalization.

`retrieval_calibration.jsonl` is a separate dev/calibration split. Thresholds
must be selected with `evaluation.calibrate_retrieval` on this split and then
held fixed while reporting metrics on `retrieval_test.jsonl`.
