.PHONY: check check-scaffolding check-ocaml-format check-python format format-ocaml format-python lint-ocaml setup-kernel test-ocaml

KERNEL_SWITCH ?= genius-kernel-414
KERNEL_RUN = opam exec --switch=$(KERNEL_SWITCH) -- uv run --no-sync

# Every OCaml warning is an error, except type-directed disambiguation and open shadowing.
OCAML_FLAGS = -strict-sequence -strict-formats -w +a-4-40-41-42-44-45-70 -warn-error +a

# The full local gate. CI runs check-ocaml-format in its own job, because the hosted
# runtime image has no ocamlformat.
check: check-scaffolding check-ocaml-format lint-ocaml test-ocaml check-python

# With full statement/branch coverage, CRAP equals cyclomatic complexity.
# Xenon's A rank requires every function to have complexity <= 5.
check-python:
	uv sync --python 3.12 --extra dev --locked --inexact
	$(MAKE) setup-kernel
	$(KERNEL_RUN) dune build @python-bindings
	$(KERNEL_RUN) ruff format --check python kernel
	$(KERNEL_RUN) ruff check python kernel
	$(KERNEL_RUN) mypy
	$(KERNEL_RUN) pytest --cov --cov-branch --cov-report=term-missing --cov-report=json:results/coverage.json --cov-report=xml:results/coverage.xml --junitxml=results/tests.xml
	$(KERNEL_RUN) xenon --max-absolute A --max-modules A --max-average A python kernel/__init__.py
	$(KERNEL_RUN) radon cc --show-complexity --json python kernel/__init__.py > results/complexity.json

# Sync Python dependencies first; the bridge is installed from the pinned opam package.
setup-kernel:
	KERNEL_SWITCH=$(KERNEL_SWITCH) sh bin/kernel_setup.sh

format: format-ocaml format-python

# pyproject.toml configures Ruff's style and lint rules.
format-python:
	uv run ruff format python kernel
	uv run ruff check --fix python kernel

# .ocamlformat pins the formatter version and style; `make format-ocaml` applies it.
format-ocaml:
	ocamlformat --inplace $(shell find ocaml tools -name '*.ml' -o -name '*.mli')

check-ocaml-format:
	@command -v ocamlformat >/dev/null || { echo "Install ocamlformat 0.29.0 for OCaml style checks; see README.md." >&2; exit 1; }
	ocamlformat --check $(shell find ocaml tools -name '*.ml' -o -name '*.mli') || { echo "OCaml style differs; run make -C evals format-ocaml." >&2; exit 1; }

# Compile temporary copies in dependency order so no build files enter the checkout.
lint-ocaml:
	@command -v ocamlc >/dev/null || { echo "Install OCaml 4.13+ for kernel checks." >&2; exit 1; }
	@build_dir=$$(mktemp -d) && \
	  (trap 'rm -rf "$$build_dir"' EXIT; \
	    cp $(filter-out ocaml/genius_evals_kernel.ml,$(wildcard ocaml/*.mli ocaml/*.ml)) "$$build_dir" && cd "$$build_dir" && \
	    ocamlc $(OCAML_FLAGS) -c $$(ocamldep -sort *.mli *.ml))

# Pure kernel modules in dependency order.
KERNEL = $(shell cd ocaml && ocamldep -sort $(notdir $(filter-out ocaml/genius_evals_kernel.ml,$(wildcard ocaml/*.mli ocaml/*.ml))))

# Link a test with only the modules it may use, so a new dependency fails to compile.
ocaml_test = build_dir=$$(mktemp -d) && trap 'rm -rf "$$build_dir"' EXIT && \
  cp $(addprefix ocaml/,$(1)) "$$build_dir" && cd "$$build_dir" && \
  ocamlc $(OCAML_FLAGS) -o test $(notdir $(1)) && ./test

test-ocaml:
	$(call ocaml_test,fixture_store.mli fixture_store.ml ast.ml experiment.mli experiment.ml tests/test_experiment.ml)
	$(call ocaml_test,fixture_store.mli fixture_store.ml ast.ml verifier.mli verifier.ml tests/test_verifier.ml)
	$(call ocaml_test,fixture_store.mli fixture_store.ml ast.ml fixture.mli fixture.ml tests/test_fixture.ml)
	$(call ocaml_test,fixture_store.mli fixture_store.ml ast.ml response.mli response.ml fixture.mli fixture.ml verifier.mli verifier.ml criterion.mli criterion.ml tests/test_criterion.ml)
	$(call ocaml_test,$(KERNEL) tests/test_kernel.ml)

check-scaffolding:
	sh -n bin/hf_host.sh
	sh -n bin/hf_bootstrap.sh
	sh -n bin/kernel_setup.sh
	uv lock --check
