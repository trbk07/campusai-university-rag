.PHONY: setup test coverage secret-scan test-windows coverage-windows secret-scan-windows
setup:
	python scripts/bootstrap.py
test:
	.venv/bin/python -m pytest -q
coverage:
	.venv/bin/python -m pytest -q --cov=campusai.llm --cov-fail-under=90
secret-scan:
	python scripts/secret_scan.py
test-windows:
	.venv\Scripts\python.exe -m pytest -q
coverage-windows:
	.venv\Scripts\python.exe -m pytest -q --cov=campusai.llm --cov-fail-under=90
secret-scan-windows:
	.venv\Scripts\python.exe scripts\secret_scan.py
