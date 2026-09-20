.PHONY: setup test
setup:
	python scripts/bootstrap.py
test:
	.venv/bin/python -m pytest -q
