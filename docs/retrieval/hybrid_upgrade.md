# Phase 6 upgrade candidate

The released RC3 evidence remains frozen. The P6-A through P6-E upgrade runs
write candidate artifacts separately until every final gate passes on a clean
commit.

## Current measured candidate

The deterministic 400-query generated dataset remains the regression set.
After removing the calendar constant, internal-ID query boost, and short-query
BM25 route, a logistic confidence model fitted on its dev split selected
threshold `0.54888`. Dev FPR was `0` with answerable Recall@5 drop `0.015873`
relative to unthresholded retrieval. Test/holdout automatic retrieval achieved
answerable Recall@5 `0.982906`/`0.931624`, FPR `0`/`0`, and test exact-code
Recall@5 `1.0`. These results were recomputed with the new code; the RC3
report was not reused as evidence for the candidate.

The current performance candidate on Windows CPU measured warm p95 `103.277`
ms, concurrency-20 p99 `749.328` ms, zero observed errors/timeouts, and peak
RSS `2,203,578,368` bytes. RAM headroom needs the actual deployment memory
limit. At a minimum, 25% headroom against this process RSS alone requires
about 2.94 GB available to the process; OS and web-server memory require
additional allowance.
The full regression benchmark's auto-route p95 was `423.847` ms; this includes
its query mix and does not meet the preferred 300 ms warm-service target.
The separate warm-service performance profile is the resource-gate measurement,
so the two latency figures must not be presented as interchangeable.

## Human-natural challenge set

`data/benchmark/hybrid_human_natural.jsonl` must contain 100–150 questions
written by people without copying gold-chunk wording. The file is intentionally
absent until it is independently annotated. Each JSONL record needs:

```json
{
  "qid": "human-001",
  "split": "human_natural",
  "question": "Môn Machine Learning cần học môn gì trước?",
  "answerable": true,
  "gold_evidence": [{"doc_id": "<verified document id>", "chunk_id": "<verified chunk id>"}],
  "language": "vi",
  "difficulty": "hard",
  "category": "prerequisite",
  "query_type": "hybrid_rrf",
  "challenge_tags": ["prerequisite"],
  "expected_route": "hybrid_rrf",
  "author_type": "human",
  "author": "<person or team>",
  "reviewer": "<independent person or team>",
  "annotation_status": "reviewed",
  "source_annotation": "<document/page and review note>"
}
```

Negative questions use `answerable: false`, `gold_evidence: []`, and the
`negative` tag. `evaluation/benchmarks/human_challenge_schema.py` rejects missing review
fields, duplicate queries, invalid evidence IDs, and incomplete language or
negative coverage. Required tags include code-switch and OCR-degraded cases;
those must reflect actual reviewed source material, not synthetic labels.
Author/reviewer metadata is an attestation; software alone
cannot prove that a question was written by a human.

Run the two benchmark families separately:

```powershell
$env:HF_HUB_OFFLINE='1'
.\.venv\Scripts\python.exe -m evaluation.retrieval.calibrate_hybrid_confidence --output .tmp\hybrid_calibration_candidate.json
.\.venv\Scripts\python.exe -m evaluation.retrieval.evaluate_hybrid_release --calibration .tmp\hybrid_calibration_candidate.json --output-dir .tmp\hybrid-candidate
.\.venv\Scripts\python.exe -m evaluation.retrieval.run_human_challenge --calibration .tmp\hybrid_calibration_candidate.json
```

The generated report uses `regression_generated` evidence and the human report
uses `human_natural` evidence. Failure-case exports retain query IDs, gold and
returned chunk IDs, route, BM25/dense/fusion ranks, acceptance score,
threshold, and a root-cause category.

## Grounding regression with explicit document scope

The reviewed grounding questions often name a PDF filename. After removing
the retriever's implicit source-ID boost, an unscoped run exposed a real
ambiguity: only 52/213 answerable gold claims appeared in context. The scoped
benchmark adds `selected_doc_ids` only when a filename stem occurs in the
question itself. Selection never reads the gold claim or evidence; the runner
verifies that every other annotation field matches the original reviewed row.
Of 400 rows, 213 have an explicit title and 187 remain unscoped. The scoped
candidate restored 213/213 answerable gold claims in context, with citation
precision/recall 1.0 and zero unsupported/contradicted leakage. This measures
the explicit-document workflow, not unscoped open-corpus grounding quality.

```powershell
.\.venv\Scripts\python.exe -m scripts.benchmarks.build_scoped_grounding --output data\benchmark\hybrid_grounding_scoped.jsonl
.\.venv\Scripts\python.exe -m evaluation.grounding.run_grounding_eval --mode runtime --benchmark data\benchmark\hybrid_grounding_scoped.jsonl --annotation-benchmark data\benchmark\grounding_reviewed.jsonl --calibration-artifact data\benchmark\grounding_calibration.json --index-dir .tmp\hybrid-index --retrieval-calibration .tmp\hybrid_calibration_candidate.json --retrieval-mode auto --output .tmp\hybrid-candidate\grounding_scoped.json
```

The release gate checks the scoped benchmark and calibration hashes. The
unscoped regression remains a documented limitation; applications should pass
explicit document selection when the user names a source.

## Deployment profiles and release gate

- Quality/offline: BAAI/bge-m3 on CPU with the calibrated logistic model and
  enough RAM for the measured 2.20 GB peak plus 25% headroom and web/OS usage.
- Light/free-web: a separate smaller model or BM25 fallback is a design option.
  It needs its own calibration and human-natural quality gate before release;
  the BGE-M3 results cannot be carried over to it.

`evaluation/retrieval/validate_retrieval_upgrade.py` requires both benchmark families,
positive paired bootstrap evidence, grounding regression, resource limits,
failure-case exports, and a declared deployment RAM budget. Use
`--require-clean` for final release validation. A final manifest should be
generated only after that gate passes on the committed code and reviewed data.
