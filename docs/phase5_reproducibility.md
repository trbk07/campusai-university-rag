# Phase 5 reproducibility

Phase 5 requires Python 3.11–3.14 and the committed `uv.lock`. From a clean
checkout on Windows, run:

```powershell
uv sync --all-extras --frozen
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.tmp\pytest-full
.\.venv\Scripts\python.exe scripts\secret_scan.py
.\.venv\Scripts\python.exe scripts\validate_benchmark_data.py data\benchmark\grounding_reviewed.jsonl --release
```

The benchmark is generated with `scripts/build_benchmark.py`, independently
reviewed through an external overlay merged by `scripts/merge_review.py`, and
attested with `scripts/annotation_signoff.py`. Calibration is fitted only on
the `dev` split by `evaluation/calibrate_confidence.py`. Test and holdout are
evaluation-only.

Release evidence is written under the ignored `.release/phase5` directory so
generation cannot dirty the source commit. Copy the frozen grounding and
calibration reports into that directory, collect the live, performance,
security, deployment and rollback reports, then run:

```powershell
.\.venv\Scripts\python.exe scripts\phase5_release.py build-manifest `
  --package-dir .release\phase5 --adversarial-cases 52 --adversarial-passed 52
.\.venv\Scripts\python.exe scripts\phase5_release.py validate .release\phase5
```

Manifest creation refuses a dirty tree. Every artifact is SHA-256 bound to the
release commit, benchmark, calibration artifact, schema, policy and frozen
threshold configuration. Any missing external evidence fails closed.
