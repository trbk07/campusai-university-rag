# Benchmark annotations

`dev.jsonl` is the schema-valid 20-row development scaffold for T7. Before
reporting research results, replace the placeholder `fixture-*` document IDs,
answers, and pages with manually verified evidence from the selected PDF
corpus. The application never reads this file at runtime; it is consumed only
by `evaluation/run_retrieval_eval.py`.
