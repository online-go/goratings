help:
	@echo "make test: Run tests"
	@echo "make lint: Run linters"

.venv venv:
	virtualenv -ppython3 .venv
	.venv/bin/pip install -r requirements.txt

100k:
	python -m goratings

test: .venv
	.venv/bin/tox -e py3

cov coverage: .venv
	@set -e && .venv/bin/tox -e coverage 

lint: .venv
	@set -e && .venv/bin/tox -e linters

format black: .venv
	isort --multi-line=3 --trailing-comma --force-grid-wrap=0 --use-parentheses --line-width=88  unit_tests goratings analysis/util
	.venv/bin/tox -e linters --notest
	.tox/linters/bin/black --line-length 120 --target-version py38 goratings unit_tests analysis/util

shippable-test:
	tox -e py3

shippable-lint:
	tox -e linters

.PHONY: lint test format
