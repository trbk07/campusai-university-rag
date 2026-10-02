# Repository conventions

## File placement and naming

Keep runtime code in `src/campusai/`. Place operational commands in
`scripts/<domain>/` and measurement/calibration workflows in
`evaluation/<domain>/`. Keep output in `evaluation/results/`, rather than mixing
JSON or CSV reports with Python modules. Tests stay under `tests/` and
integration tests under `tests/integration/`.

Use lowercase `snake_case` filenames describing the task, for example
`build_corpus_index.py`, `calibrate_hybrid_confidence.py`, and
`measure_reranker_http.py`. Use domain folders and function-based Make targets
such as `hybrid-evaluate` and `reranker-quality`. Roadmap phases belong in
planning history, rather than file or command names.

Run tools from the project root with `python -m scripts.<domain>.<tool>` or
`python -m evaluation.<domain>.<tool>`. New tool folders include `__init__.py`.
Place documentation in the matching `docs/<domain>/` directory, and link
relative to that document's own directory. Historical implementation plans live
in `docs/planning/`. The main project roadmap stays at the repository root as
`plan.md` for the entire project. Keep it tracked, and never move, rename or
delete it during cleanup. Only the owner will delete it after project completion.

## Evaluation evidence

Benchmark labels, dataset IDs, reviewed splits, calibration metadata and
recorded metrics are versioned evidence. Preserve their bytes when moving or
renaming them: changing an old report's path fields changes its checksum.
Existing reports retain historical paths, release identifiers and schema
fields in their payloads. Runtime protocol names and serialized fields retain
compatibility with these datasets.

Baseline retrieval files use `baseline_`, hybrid datasets/reports use
`hybrid_`, and AI reranker questions use `reranker_`. PDF pipeline measurements
and manual table review live in `evaluation/results/pdf_pipeline_benchmark.*`
and `evaluation/results/pdf_table_review.json`.

The historical `hybrid_release_manifest.json` remains immutable. Its embedded
paths and source/config/documentation checksums describe the earlier layout.
Validators reject stale fingerprints; an offline test run does not renew
release approval. Regenerate required evidence and the fingerprint from a
clean, reviewed commit before a production release. Run
`python -m evaluation.retrieval.validate_hybrid_release --help` for fingerprint
options. Use `--require-clean --write-manifest` when renewing the hybrid
fingerprint: artifact gates are checked before writing, and normal validation
continues to verify the existing fingerprint. Reranker evidence also binds the
source tree and must be regenerated after source changes.

## Local artifacts

`.venv/` holds installed dependencies. `.tmp/` holds scratch runs and model
snapshots; `.release/` holds local deployment evidence. These directories are
ignored by Git. `data/store/` and generated ingestion/index directories hold
local user data and are preserved until an explicit data-deletion request.
Dependency caches, test temporary directories and coverage files can be
regenerated.

`data/corpus/university/` is the canonical evaluation fixture. Root-level PDFs
were removed only after their SHA-256 hashes matched files in that corpus.
