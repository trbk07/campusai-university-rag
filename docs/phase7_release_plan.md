# Phase 7: release 10/10

The authority is `python -m evaluation.validate_reranker_release --through M12`.
Only `status=pass`, `score=10.0`, and all M0–M12 `PASS` permit release.
The source baseline is preserved. A passing unit test is code evidence;
model benchmarks are evaluation evidence; staging observations are deployment
evidence. They are not interchangeable.

Canonical documents are this plan, [the runbook](reranker_release_runbook.md),
[human benchmark guidance](human_benchmark_sources.md), and
[current evidence status](reranker_progress.md). Existing names remain stable.

## Workflow

Run commands from the repository root. `python` below means the project
virtualenv interpreter (`.venv/Scripts/python.exe` on Windows).

| Command | Required external input | Gate |
|---|---|---|
| `python -m evaluation.phase7_release baseline` | Existing frozen Phase 6 artifacts/index | M0 |
| `python -m evaluation.phase7_release human-freeze` | Reviewed `data/benchmark/human_retrieval.jsonl` | M1 |
| `python -m evaluation.phase7_release candidate` | Frozen human splits | M2 |
| `python -m evaluation.phase7_release model --model-dir SNAPSHOT` | Offline model directory named by immutable commit | M3 |
| `python -m evaluation.phase7_release route` | Human dev with difficulty review and grouped route calibration | M4 |
| `python -m evaluation.phase7_release calibration --model-dir SNAPSHOT` | Dev-only cap sweep | M5 |
| `python -m evaluation.phase7_release quality --model-dir SNAPSHOT` | Held-out paired observations | M6 |
| `python -m evaluation.phase7_release performance --model-dir SNAPSHOT --deployment-ram-bytes LIMIT --llm-config CONFIG` | Real RAM limit and configured live LLM | M7 |
| `python -m evaluation.phase7_release security --model-dir SNAPSHOT --cases CASES` | >=50 adversarial cases covering all 12 categories | M8 |
| `python -m evaluation.phase7_release faults` | Controlled runtime injection | M9 |
| `python -m evaluation.phase7_release rollback --model-dir SNAPSHOT` | Live model and shared cache probes | M10 |
| `python -m evaluation.phase7_release staging --observations WINDOWS --fault-observations FAULTS` | Actual staging telemetry | M11 |
| `python -m evaluation.phase7_release staging-collect --model-dir SNAPSHOT` | Frozen M0-M10 evidence; local measured deployment | Collect and audit M11 |
| `python -m evaluation.phase7_release validate` | All artifacts; clean source tree | M12 |
| `python -m evaluation.phase7_release release --model-dir SNAPSHOT` | Recomputed physical model snapshot | Final manifest |

Each command has an equivalent `make phase7-STAGE PHASE7_ARGS="..."`.
The workflow configures experimental measurement activation from the M3
identity; provide `--device` and `--model-name` if they differ from the CPU/BGE
defaults. It never enables production automatically.

Use `--results-dir`, `--index-dir`, and `--benchmark-dir` for isolated studies.
The standard evidence directory is `evaluation/results`; official artifacts,
cap trials, and grounding XML reports stay there. Readiness output goes to
`.release/reranker/readiness.json` so validation does not dirty the tree.
The generated final manifest at `evaluation/results/reranker_release_manifest.json`
is ignored; archive it with the committed evidence. Never use it to substitute
for measured reports.

## Freeze and rerun rules

M4 writes `reranker_route_freeze.json` **before** opening held-out route data.
M6 writes `reranker_policy_freeze.json` **before** opening held-out quality data.
A failed run also consumes the study. Fitting tools reject another fit after
the applicable lock; identical quality reruns may reuse the lock, but changed
model, route, calibration, benchmark or cap evidence is rejected. Never remove
locks to tune on held-out results. A failed study requires a new research cycle
with fresh reviewed data and its own results directory.

Reports M3 onward bind source/runtime/index/Phase 6 calibration/model identity.
Reports after calibration also bind route calibration, training split, and
human benchmark. The source digest includes tests and build/dependency files.
Any source change requires affected measurements to be rerun on the release
source. Finish code review and commit source before collecting final evidence.

## External evidence still required

The repository currently has no independently approved 150-record human
benchmark and no real staging window/fault telemetry. These cannot be authored
or approved by the evaluation scripts. Use the pending-review schema example,
two distinct human author/reviewer identities, frozen PDF coordinates, and
explicit scope. Review checks include paraphrase leakage and expected behavior.

Staging needs 0/1/5/10/25% in order, three healthy windows at **each** step,
100 requests per window, complete metrics, and all eight rollback exercises.
Every window must meet the budgets; the final step is checked too. Both p95
and p99 violations count toward the three-window latency rollback trigger.

`staging-collect` starts an isolated local service process, runs the real model,
collects three windows at all five steps, executes all eight controlled rollback
exercises, and audits the resulting telemetry. It requires M0-M10 first. The
default outputs are `.release/reranker/staging_observations.json` and
`.release/reranker/staging_fault_observations.json`; use new paths for a new run.
`--staging-requests` defaults to 100 and `--staging-concurrency` to 1. Every
workload cycle retains reviewed easy, hard and negative cohorts. Scope exercises
also need restricted-scope rows from all three cohorts.

The collector retains request IDs, evaluator labels, scope, outputs, measured
latency, and process RSS/queue gauges sampled every 10 ms. The auditor recomputes
window summaries and checks output provenance against the frozen index; scalar
summaries cannot substitute for raw observations. Faults resume the measured
25% configuration, inject at named service/model boundaries, and verify provider
closure plus unchanged Phase 6 outputs and zero new inference in follow-up
requests. The memory exercise lowers the configured alert budget while retaining
the actual measured RSS. The latency exercise executes three slow windows and
therefore takes at least five minutes at the default sequential load.

`python -m evaluation.diagnose_reranker_cpu --model-dir SNAPSHOT --device cpu`
probes real chunks from three hard dev questions at caps 8/10/20. Use
`--device cuda:0` for a separately installed GPU runtime. This is exploratory
diagnostic data, always `release_eligible=false`; it never satisfies M7 or reads
test/holdout. Measurement activation runs Hugging Face/Transformers offline.

For a Windows host with an NVIDIA GPU, `powershell -File scripts/setup_phase7_gpu.ps1`
creates a separate `.tmp/phase7-gpu-runtime`. It installs the pinned PyTorch CUDA
wheel from [the official PyTorch repository](https://download.pytorch.org/whl/cu126/torch/)
and shares existing project dependencies without replacing the CPU `.venv`.
Run GPU commands with `.tmp/phase7-gpu-runtime/Scripts/python.exe` and
`--device cuda:0`; model smoke/calibration and later measurements must use that
same runtime. Device/runtime changes invalidate their earlier evidence bindings.

The future public website must have zero GPU rental cost. Its selected target
and quota/lease constraints are recorded in [the free GPU deployment decision](phase7_free_gpu_hosting.md).

Commit the actual dataset and evaluation evidence after measurement. Only
after that clean checkout passes M12 should the manifest be generated and
`RERANKER_DEPLOYMENT=production` be configured.
