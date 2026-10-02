# Phase 3 remediation

The frozen starting point is `evaluation/results/baseline_retrieval_audit.json`.
It records the 100-query, two-document benchmark and its negative FPR of 1.0.
The old report remains historical evidence, not the new release report.

The retriever now exposes `last_trace.abstention_reason` when it returns no
results. The legacy calibration command uses the confidence score for hybrid
retrieval, matching the runtime abstention decision. It also checks actual
answerable Recall@5 instead of treating any returned candidate as relevant.

Build a separate Phase 3 index and source manifest from the verified PDFs:

```powershell
.\.venv\Scripts\python.exe -m scripts.retrieval.build_corpus_index --store-dir .tmp\phase3-store --index-dir .tmp\baseline-index
.\.venv\Scripts\python.exe -m scripts.retrieval.isolate_corpus_index
.\.venv\Scripts\python.exe -m scripts.retrieval.create_corpus_manifest
```

The index builder is shared, but the Phase 3 index and manifests are separate.
The isolation step selects only verified PDFs from this build, since an index
directory may already contain unrelated development data.
`create_corpus_manifest.py` verifies every PDF checksum and records indexed
document and chunk counts. Scan-only PDFs do not count toward the eight-indexed-
document gate.

Provide independently reviewed Phase 3 benchmark files named
`baseline_retrieval_dev.jsonl`, `baseline_retrieval_test.jsonl`, and
`baseline_retrieval_holdout.jsonl` in `data/benchmark`. Their record format uses
`qid`, `split`, `question`, `answerable`, `gold_evidence`, `negative_class`,
`source_group`, and `template_group`. The validator rejects duplicate queries,
missing evidence, and source or template groups crossing splits. At least 400
records and 40 negatives are required. Existing Phase 6 benchmark queries and
reports cannot be relabeled as independent Phase 3 release evidence.

`scripts/benchmarks/build_baseline_draft.py` can generate 400 review candidates
from the existing source dataset. Every row is marked `draft_unreviewed` and
the release validator rejects it until its question, evidence, split and
negative label are independently reviewed. The script refuses to overwrite
existing annotations.

For exploration before review, both calibration and release commands support
`--allow-draft`. Keep their outputs under `.tmp`; the release status remains
conditional and the draft cannot be promoted by this flag.

On the current draft, Phase 3 dev has 140 queries (126 answerable, 14
negative). A fresh BAAI/bge-m3 Phase 3 index has 10 verified indexed PDFs and
942 chunks. A diagnostic hybrid RRF calibration measured unfiltered
answerable Recall@5 of `0.912698`. No threshold met both the plan's `0.95`
calibration recall and `0.01` FPR limits; the best recall with FPR at most 1%
was `0.119048`. These are diagnostic measurements from unreviewed labels, so
they do not establish final retrieval quality.

The diagnostic test/holdout run (without a feasible threshold) measured hybrid
RRF Recall@5 `0.965812`/`0.940171`, MRR `0.812821`/`0.831909`, and negative
FPR `0.461538` on both splits. Automatic routing measured Recall@5
`0.982906`/`0.957265` and FPR `0.307692` on both splits. Hybrid warm p95 was
`329.318`/`253.782` ms, but p50 was `194.910`/`203.936` ms, above the plan's
150 ms target. This is a diagnostic run with unreviewed labels and no calibrated
threshold, not release evidence.

Then run:

```powershell
.\.venv\Scripts\python.exe -m evaluation.retrieval.calibrate_baseline_threshold
.\.venv\Scripts\python.exe -m evaluation.retrieval.evaluate_baseline_release
```

Calibration reads the dev split only and binds the threshold to benchmark and
index hashes. The release evaluator runs dense, hybrid RRF, and automatic
routing on test and holdout. It remains conditional until quality, negative
FPR, clean-tree, performance, persistence, and statistical gates all pass.
The three supporting evidence files are
`evaluation/results/baseline_performance.json`,
`evaluation/results/baseline_persistence.json`, and
`evaluation/results/baseline_statistical_report.json`; each must have a passing
status and the current Phase 3 index hash.

The weighted target values printed in the supplied plan sum to **9.46**, not
9.5: `9.3 * 0.20 + 9.5 * 0.80 = 9.46`. This tooling reports measured gates
and leaves `score` unset; a reviewer must assign category scores under a
consistent rubric before asserting an overall score of at least 9.5.
