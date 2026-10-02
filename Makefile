.PHONY: setup test coverage secret-scan baseline benchmark-draft benchmark-review benchmark-validate grounding-eval release-validate phase5-adversarial phase5-security phase5-performance phase5-package-validate phase6-benchmark phase6-index phase6-calibrate phase6-evaluate phase6-operations phase6-security phase6-validate test-windows coverage-windows secret-scan-windows reranker-validate reranker-baseline-check reranker-human-freeze reranker-candidate-coverage reranker-route-calibration reranker-quality
setup:
	python scripts/bootstrap.py
test:
	.venv/bin/python -m pytest -q --basetemp=.tmp/pytest-make
coverage:
	.venv/bin/python -m pytest -q --cov=campusai.llm --cov-fail-under=90
secret-scan:
	python scripts/secret_scan.py
test-windows:
	.venv\Scripts\python.exe -m pytest -q --basetemp=.tmp\pytest-make
coverage-windows:
	.venv\Scripts\python.exe -m pytest -q --cov=campusai.llm --cov-fail-under=90
secret-scan-windows:
	.venv\Scripts\python.exe scripts\secret_scan.py
baseline:
	.venv\Scripts\python.exe evaluation\create_baseline.py --benchmark data\benchmark\basic_rag.jsonl
grounding-eval:
	.venv\Scripts\python.exe evaluation\run_grounding_eval.py --benchmark data\benchmark\basic_rag.jsonl --mode fixture
release-validate:
	.venv\Scripts\python.exe evaluation\validate_release.py evaluation\results\grounding_release_report.json
phase5-adversarial:
	.venv\Scripts\python.exe -m pytest -q tests\test_phase5_adversarial.py --basetemp=.tmp\pytest-adversarial
phase5-security:
	.venv\Scripts\python.exe scripts\security_evidence.py
phase5-performance:
	.venv\Scripts\python.exe scripts\load_test.py --output .release\phase5\performance_report.json
phase5-package-validate:
	.venv\Scripts\python.exe scripts\phase5_release.py validate .release\phase5
phase6-benchmark:
	.venv\Scripts\python.exe scripts\build_phase6_benchmark.py
phase6-index:
	.venv\Scripts\python.exe scripts\build_phase6_index.py
phase6-calibrate:
	.venv\Scripts\python.exe evaluation\calibrate_phase6.py
phase6-evaluate:
	.venv\Scripts\python.exe evaluation\run_phase6_release.py
phase6-operations:
	set OMP_NUM_THREADS=1&& set MKL_NUM_THREADS=1&& .venv\Scripts\python.exe evaluation\run_phase6_operations.py
phase6-security:
	.venv\Scripts\python.exe evaluation\run_phase6_security.py
phase6-validate:
	.venv\Scripts\python.exe evaluation\validate_phase6_release.py
benchmark-draft:
	.venv\Scripts\python.exe scripts\build_benchmark.py --input-dir data\corpus\university --output data\benchmark\grounding_draft.jsonl --target 400
benchmark-review:
	.venv\Scripts\python.exe scripts\review_benchmark.py data\benchmark\grounding_draft.jsonl data\benchmark\grounding_reviewed.jsonl --annotator-id engineering-review-1
benchmark-validate:
	.venv\Scripts\python.exe scripts\validate_benchmark_data.py data\benchmark\grounding_reviewed.jsonl --release

ifeq ($(OS),Windows_NT)
PHASE7_PYTHON ?= .venv/Scripts/python.exe
else
PHASE7_PYTHON ?= .venv/bin/python
endif
PHASE7_ARGS ?=
PHASE7_STAGES := baseline human-freeze candidate model route calibration quality performance security faults rollback staging staging-collect validate release
.PHONY: $(addprefix phase7-,$(PHASE7_STAGES))
$(addprefix phase7-,$(PHASE7_STAGES)): phase7-%:
	$(PHASE7_PYTHON) -m evaluation.phase7_release $* $(PHASE7_ARGS)

# Existing command names remain compatible with the canonical Phase 7 workflow.
reranker-validate: phase7-validate
reranker-baseline-check: phase7-baseline
reranker-human-freeze: phase7-human-freeze
reranker-candidate-coverage: phase7-candidate
reranker-route-calibration: phase7-route
reranker-quality: phase7-quality

.PHONY: student-natural-benchmark
student-natural-benchmark:
	$(PHASE7_PYTHON) -m evaluation.build_student_natural_benchmark
