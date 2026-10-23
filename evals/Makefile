.PHONY: check-bin check check-scaffolding check-python format format-python setup check-install

RUN = uv run --no-sync

check: check-scaffolding check-python

# With full statement/branch coverage, CRAP equals cyclomatic complexity.
# Xenon's A rank requires every function to have complexity <= 5.
# The pytest collection hook remains outside runtime complexity checks.
check-python:
	uv sync --python 3.12 --extra dev --locked --inexact
	$(RUN) ruff format --check python scripts/check_installation.py
	$(RUN) ruff check python scripts/check_installation.py
	$(RUN) mypy
	$(RUN) pytest --cov --cov-branch --cov-report=term-missing --cov-report=json:results/coverage.json --cov-report=xml:results/coverage.xml --junitxml=results/tests.xml
	$(RUN) xenon --max-absolute A --max-modules A --max-average A --exclude python/tests/conftest.py python
	$(RUN) radon cc --show-complexity --json --exclude python/tests/conftest.py python > results/complexity.json

setup:
	uv sync --python 3.12 --extra dev --locked --inexact

format: format-python

# pyproject.toml configures Ruff's style and lint rules.
format-python:
	uv run ruff format python scripts/check_installation.py
	uv run ruff check --fix python scripts/check_installation.py

check-install:
	$(RUN) python scripts/check_installation.py

check-scaffolding:
	bash -n bin/huggingface-run
	bash -n scripts/huggingface-bootstrap.sh
	uv lock --check

# CLI contracts use only the standard library; tools are pinned and isolated by uv.
check-bin:
	cd .. && for script in evals/bin/* evals/scripts/*.sh evals/lib/*.sh; do "$${BASH_BIN:-bash}" -n "$$script" || exit; done
	cd .. && uvx --from shellcheck-py==0.11.0.1 shellcheck --external-sources --shell=bash evals/bin/* evals/scripts/*.sh evals/lib/*.sh
	cd .. && uvx --from shfmt-py==4.2.0 shfmt -d -i 2 -ci -bn evals/bin/* evals/scripts/*.sh evals/lib/*.sh
	cd .. && uv run --no-project --python 3.12 python -m unittest discover -s tests -v
