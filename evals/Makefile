.PHONY: check

# With full statement/branch coverage, CRAP equals cyclomatic complexity.
# Xenon's A rank requires every function to have complexity <= 5.
check:
	uv sync --extra dev --locked
	uv run ruff check genius_evals tests
	uv run mypy
	uv run pytest --cov --cov-branch --cov-report=term-missing --cov-report=json:results/coverage.json --cov-report=xml:results/coverage.xml --junitxml=results/tests.xml
	uv run xenon --max-absolute A --max-modules A --max-average A genius_evals tests
	uv run radon cc --show-complexity --json genius_evals tests > results/complexity.json
