.PHONY: setup test coverage secret-scan baseline benchmark-draft benchmark-review benchmark-validate grounding-eval release-validate phase5-adversarial phase5-security phase5-performance phase5-package-validate test-windows coverage-windows secret-scan-windows
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
benchmark-draft:
	.venv\Scripts\python.exe scripts\build_benchmark.py --input-dir data\corpus\university --output data\benchmark\grounding_draft.jsonl --target 400
benchmark-review:
	.venv\Scripts\python.exe scripts\review_benchmark.py data\benchmark\grounding_draft.jsonl data\benchmark\grounding_reviewed.jsonl --annotator-id engineering-review-1
benchmark-validate:
	.venv\Scripts\python.exe scripts\validate_benchmark_data.py data\benchmark\grounding_reviewed.jsonl --release
