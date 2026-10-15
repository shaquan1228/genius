.PHONY: check check-scaffolding lint-ocaml

# Every OCaml warning is an error, except type-directed disambiguation and open shadowing.
OCAML_FLAGS = -strict-sequence -strict-formats -w +a-4-40-41-42-44-45-70 -warn-error +a

# With full statement/branch coverage, CRAP equals cyclomatic complexity.
# Xenon's A rank requires every function to have complexity <= 5.
check: check-scaffolding lint-ocaml
	sh -n check.sh
	@test -f tasks.py || { echo "Eval runtime is supplied by the stacked fixture PR." >&2; exit 1; }
	uv sync --extra dev --locked
	uv run ruff check *.py tests
	uv run mypy
	uv run pytest --cov --cov-branch --cov-report=term-missing --cov-report=json:results/coverage.json --cov-report=xml:results/coverage.xml --junitxml=results/tests.xml
	uv run xenon --max-absolute A --max-modules A --max-average A *.py tests
	uv run radon cc --show-complexity --json *.py tests > results/complexity.json

# Compile temporary copies in dependency order so no build files enter the checkout.
lint-ocaml:
	@command -v ocamlc >/dev/null || { echo "Install OCaml 4.13+ (ocamlc) for fixture checks." >&2; exit 1; }
	build_dir=$$(mktemp -d) && trap 'rm -rf "$$build_dir"' EXIT && \
	  cp *.mli *.ml "$$build_dir" && cd "$$build_dir" && \
	  ocamlc $(OCAML_FLAGS) -c $$(ocamldep -sort *.mli *.ml)

check-scaffolding:
	sh -n hf_host.sh
	sh -n hf_bootstrap.sh
	uv lock --check
