.PHONY: check

# With full statement/branch coverage, CRAP equals cyclomatic complexity.
# Xenon's A rank requires every function to have complexity <= 5.
check:
	uv sync --extra dev --locked
	uv run ruff check *.py heldout tests --exclude tests/solutions
	uv run mypy
	uv run pytest --cov --cov-branch --cov-report=term-missing --cov-report=json:results/coverage.json --cov-report=xml:results/coverage.xml --junitxml=results/tests.xml
	uv run xenon --max-absolute A --max-modules A --max-average A *.py heldout tests -e tests/solutions
	uv run radon cc --show-complexity --json *.py heldout tests -e tests/solutions > results/complexity.json
