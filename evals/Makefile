.PHONY: check check-scaffolding check-ocaml-format check-python format-ocaml lint-ocaml

# Every OCaml warning is an error, except type-directed disambiguation and open shadowing.
OCAML_FLAGS = -strict-sequence -strict-formats -w +a-4-40-41-42-44-45-70 -warn-error +a

# The full local gate. CI runs check-ocaml-format in its own job, because the hosted
# runtime image has OCaml 4.13 but no ocamlformat.
check: check-scaffolding check-ocaml-format lint-ocaml check-python

# With full statement/branch coverage, CRAP equals cyclomatic complexity.
# Xenon's A rank requires every function to have complexity <= 5.
check-python:
	uv sync --extra dev --locked
	uv run ruff check python
	uv run mypy
	uv run pytest --cov --cov-branch --cov-report=term-missing --cov-report=json:results/coverage.json --cov-report=xml:results/coverage.xml --junitxml=results/tests.xml
	uv run xenon --max-absolute A --max-modules A --max-average A python
	uv run radon cc --show-complexity --json python > results/complexity.json

# ocaml/.ocamlformat pins the formatter version and style; `make format-ocaml` applies it.
format-ocaml:
	ocamlformat --inplace ocaml/*.ml ocaml/*.mli

check-ocaml-format:
	@command -v ocamlformat >/dev/null || { echo "Install ocamlformat 0.29.0 for OCaml style checks; see README.md." >&2; exit 1; }
	ocamlformat --check ocaml/*.ml ocaml/*.mli || { echo "OCaml style differs; run make -C evals format-ocaml." >&2; exit 1; }

# Compile temporary copies in dependency order so no build files enter the checkout.
lint-ocaml:
	@command -v ocamlc >/dev/null || { echo "Install OCaml 4.13+ (ocamlc) for fixture checks." >&2; exit 1; }
	sh -n ocaml/check.sh
	build_dir=$$(mktemp -d) && trap 'rm -rf "$$build_dir"' EXIT && \
	  cp ocaml/*.mli ocaml/*.ml "$$build_dir" && cd "$$build_dir" && \
	  ocamlc $(OCAML_FLAGS) -c $$(ocamldep -sort *.mli *.ml)

check-scaffolding:
	sh -n hf_host.sh
	sh -n hf_bootstrap.sh
	uv lock --check
