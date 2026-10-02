ifeq ($(OS),Windows_NT)
PYTHON ?= .venv/Scripts/python.exe
else
PYTHON ?= .venv/bin/python
endif
RERANKER_ARGS ?=
RERANKER_STAGES := baseline human-freeze candidate model route calibration quality performance security faults rollback staging staging-collect validate release

.PHONY: setup test coverage secret-scan baseline grounding-eval release-validate grounding-adversarial grounding-security grounding-performance grounding-package-validate hybrid-benchmark hybrid-index hybrid-calibrate hybrid-evaluate hybrid-operations hybrid-security hybrid-validate benchmark-draft benchmark-review benchmark-validate student-natural-benchmark
setup:
	python -m scripts.dev.bootstrap
test:
	$(PYTHON) -m pytest -q --basetemp=.tmp/pytest-make
coverage:
	$(PYTHON) -m pytest -q --cov=campusai.llm --cov-fail-under=90
secret-scan:
	$(PYTHON) -m scripts.dev.secret_scan
baseline:
	$(PYTHON) -m evaluation.grounding.create_grounding_baseline --benchmark data/benchmark/basic_rag.jsonl
grounding-eval:
	$(PYTHON) -m evaluation.grounding.run_grounding_eval --benchmark data/benchmark/basic_rag.jsonl --mode fixture
release-validate:
	$(PYTHON) -m evaluation.grounding.validate_grounding_release evaluation/results/grounding_release_report.json
grounding-adversarial:
	$(PYTHON) -m pytest -q tests/test_grounding_adversarial.py --basetemp=.tmp/pytest-adversarial
grounding-security:
	$(PYTHON) -m scripts.operations.security_evidence
grounding-performance:
	$(PYTHON) -m scripts.operations.load_test --output .release/grounding/performance_report.json
grounding-package-validate:
	$(PYTHON) -m scripts.release.package_grounding_release validate .release/grounding
hybrid-benchmark:
	$(PYTHON) -m scripts.benchmarks.build_hybrid_benchmark
hybrid-index:
	$(PYTHON) -m scripts.retrieval.build_corpus_index
hybrid-calibrate:
	$(PYTHON) -m evaluation.retrieval.calibrate_hybrid_confidence
hybrid-evaluate:
	$(PYTHON) -m evaluation.retrieval.evaluate_hybrid_release
hybrid-operations:
	$(PYTHON) -m evaluation.retrieval.measure_hybrid_operations
hybrid-security:
	$(PYTHON) -m evaluation.retrieval.evaluate_hybrid_security
hybrid-validate:
	$(PYTHON) -m evaluation.retrieval.validate_hybrid_release
benchmark-draft:
	$(PYTHON) -m scripts.benchmarks.build_benchmark --input-dir data/corpus/university --output data/benchmark/grounding_draft.jsonl --target 400
benchmark-review:
	$(PYTHON) -m scripts.benchmarks.review_benchmark data/benchmark/grounding_draft.jsonl data/benchmark/grounding_reviewed.jsonl --annotator-id engineering-review-1
benchmark-validate:
	$(PYTHON) -m scripts.benchmarks.validate_benchmark_data data/benchmark/grounding_reviewed.jsonl --release
student-natural-benchmark:
	$(PYTHON) -m evaluation.benchmarks.build_student_natural_benchmark

.PHONY: $(addprefix reranker-,$(RERANKER_STAGES))
$(addprefix reranker-,$(RERANKER_STAGES)): reranker-%:
	$(PYTHON) -m evaluation.reranker.release_workflow $* $(RERANKER_ARGS)

.PHONY: test-windows coverage-windows secret-scan-windows reranker-baseline-check reranker-candidate-coverage reranker-route-calibration
test-windows: test
coverage-windows: coverage
secret-scan-windows: secret-scan
reranker-baseline-check: reranker-baseline
reranker-candidate-coverage: reranker-candidate
reranker-route-calibration: reranker-route
