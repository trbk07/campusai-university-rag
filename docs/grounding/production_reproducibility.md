# Phase 5 reproducibility

Phase 5 requires Python 3.11–3.14 and the committed `uv.lock`. From a clean
checkout on Windows, run:

```powershell
uv sync --all-extras --frozen
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.tmp\pytest-full
.\.venv\Scripts\python.exe -m scripts.dev.secret_scan
.\.venv\Scripts\python.exe -m scripts.benchmarks.validate_benchmark_data data\benchmark\grounding_reviewed.jsonl --release
```

The benchmark is generated with `scripts/benchmarks/build_benchmark.py`, independently
reviewed through an external overlay merged by `scripts/benchmarks/merge_review.py`, and
attested with `scripts/release/annotation_signoff.py`. Calibration is fitted only on
the `dev` split by `evaluation/grounding/calibrate_confidence.py`. Test and holdout are
evaluation-only.

Release evidence is written under the ignored `.release/grounding` directory so
generation cannot dirty the source commit. Copy the frozen grounding and
calibration reports into that directory, collect the live, performance,
security, deployment and rollback reports, then run:

```powershell
.\.venv\Scripts\python.exe -m scripts.release.package_grounding_release build-manifest `
  --package-dir .release\grounding --adversarial-cases 52 --adversarial-passed 52
.\.venv\Scripts\python.exe -m scripts.release.package_grounding_release validate .release\grounding
```

Manifest creation refuses a dirty tree. Every artifact is SHA-256 bound to the
release commit, benchmark, calibration artifact, schema, policy and frozen
threshold configuration. Any missing external evidence fails closed.
