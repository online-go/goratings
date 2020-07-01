help:
	@echo "make test: Run tests"
	@echo "make lint: Run linters"

.venv venv:
	virtualenv -ppython3 .venv
	.venv/bin/pip install tox
	.venv/bin/pip install python-dateutil

100k:
	python -m goratings

test: .venv
	.venv/bin/tox -e py3

cov coverage: .venv
	@set -e && .venv/bin/tox -e coverage 

lint: .venv
	@set -e && .venv/bin/tox -e linters

format black: .venv
	isort -y --multi-line=3 --trailing-comma --force-grid-wrap=0 --use-parentheses --line-width=88 
	.venv/bin/tox -e linters --notest
	.tox/linters/bin/black --target-version py38 goratings unit_tests 

.PHONY: lint test format
