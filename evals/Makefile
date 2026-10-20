.PHONY: check-bin check check-scaffolding check-ocaml-format check-python format format-ocaml format-python lint-ocaml setup setup-kernel test-ocaml check-install

KERNEL_SWITCH ?= genius-kernel-414
KERNEL_RUN = opam exec --switch="$(KERNEL_SWITCH)" -- uv run --no-sync

# Every OCaml warning is an error, except type-directed disambiguation and open shadowing.
OCAML_FLAGS = -strict-sequence -strict-formats -w +a-4-40-41-42-44-45-70 -warn-error +a

# The full local gate. CI runs check-ocaml-format in its own job, because the hosted
# runtime image has no ocamlformat.
check: check-scaffolding check-ocaml-format lint-ocaml test-ocaml check-python

# With full statement/branch coverage, CRAP equals cyclomatic complexity.
# Xenon's A rank requires every function to have complexity <= 5.
# The binding renderer and pytest collection hook remain outside runtime complexity checks.
check-python:
	uv sync --python 3.12 --extra dev --locked --inexact
	$(MAKE) setup-kernel
	$(KERNEL_RUN) dune build @python-bindings
	$(KERNEL_RUN) ruff format --check python scripts/check_installation.py
	$(KERNEL_RUN) ruff check python scripts/check_installation.py
	$(KERNEL_RUN) mypy
	$(KERNEL_RUN) pytest --cov --cov-branch --cov-report=term-missing --cov-report=json:results/coverage.json --cov-report=xml:results/coverage.xml --junitxml=results/tests.xml
	$(KERNEL_RUN) xenon --max-absolute A --max-modules A --max-average A --exclude python/kernel/generate.py,python/tests/conftest.py python
	$(KERNEL_RUN) radon cc --show-complexity --json --exclude python/kernel/generate.py,python/tests/conftest.py python > results/complexity.json

setup:
	uv sync --python 3.12 --extra dev --locked --inexact
	$(MAKE) setup-kernel

# Sync Python dependencies first; the bridge is installed from the pinned opam package.
setup-kernel:
	KERNEL_SWITCH="$(KERNEL_SWITCH)" bash scripts/kernel-setup.sh

format: format-ocaml format-python

# pyproject.toml configures Ruff's style and lint rules.
format-python:
	uv run ruff format python scripts/check_installation.py
	uv run ruff check --fix python scripts/check_installation.py

# ocaml/.ocamlformat pins the formatter version and style; `make format-ocaml` applies it.
format-ocaml:
	ocamlformat --inplace $(shell find ocaml -name '*.ml' -o -name '*.mli')

check-ocaml-format:
	@command -v ocamlformat >/dev/null || { echo "Install ocamlformat 0.29.0 for OCaml style checks; see README.md." >&2; exit 1; }
	ocamlformat --check $(shell find ocaml -name '*.ml' -o -name '*.mli') || { echo "OCaml style differs; run make -C evals format-ocaml." >&2; exit 1; }

# Compile temporary copies in dependency order so no build files enter the checkout.
lint-ocaml:
	@command -v ocamlc >/dev/null || { echo "Install OCaml 4.13+ for kernel checks." >&2; exit 1; }
	@build_dir=$$(mktemp -d) && \
	  (trap 'rm -rf "$$build_dir"' EXIT; \
	    cp $(filter-out ocaml/genius_evals_kernel.ml ocaml/kernel.ml,$(wildcard ocaml/*.mli ocaml/*.ml)) "$$build_dir" && cd "$$build_dir" && \
	    ocamlc $(OCAML_FLAGS) -c $$(ocamldep -sort *.mli *.ml))

# Pure kernel modules in dependency order.
KERNEL = $(shell cd ocaml && ocamldep -sort $(notdir $(filter-out ocaml/genius_evals_kernel.ml ocaml/kernel.ml,$(wildcard ocaml/*.mli ocaml/*.ml))))

# Link a test with only the modules it may use, so a new dependency fails to compile.
ocaml_test = build_dir=$$(mktemp -d) && trap 'rm -rf "$$build_dir"' EXIT && \
  cp $(addprefix ocaml/,$(1)) "$$build_dir" && cd "$$build_dir" && \
  ocamlc $(OCAML_FLAGS) -o test $(notdir $(1)) && ./test

COMPARISON = comparison.mli comparison.ml
VALIDATION = $(COMPARISON) validation_code.mli validation_code.ml validation_issue.mli validation_issue.ml validation_failure.mli validation_failure.ml validation.mli validation.ml
FILES = $(VALIDATION) file.mli file.ml fixture_comparison.mli fixture_comparison.ml fixture.mli fixture.ml
RESPONSE = $(VALIDATION) text.mli text.ml value.mli value.ml predicate.mli predicate.ml verification.mli verification.ml response_value.mli response_value.ml response_field.mli response_field.ml response.mli response.ml text_rule.mli text_rule.ml rubric.mli rubric.ml
PREDICATE = $(VALIDATION) text.mli text.ml value.mli value.ml predicate.mli predicate.ml
VERIFIER = $(VALIDATION) file.mli file.ml content.mli content.ml resource_binding.mli resource_binding.ml artifact.mli artifact.ml verifier.mli verifier.ml

test-ocaml:
	$(call ocaml_test,$(VALIDATION) profile.mli profile.ml experiment.mli experiment.ml tests/test_experiment.ml)
	$(call ocaml_test,$(VERIFIER) tests/test_verifier.ml)
	$(call ocaml_test,$(FILES) tests/test_fixture.ml)
	$(call ocaml_test,$(RESPONSE) tests/test_criterion.ml)
	$(call ocaml_test,$(PREDICATE) tests/test_predicate.ml)
	$(call ocaml_test,$(KERNEL) tests/test_content.ml)
	$(call ocaml_test,$(KERNEL) tests/test_kernel.ml)

check-install:
	$(KERNEL_RUN) python scripts/check_installation.py

check-scaffolding:
	bash -n bin/huggingface-run
	bash -n scripts/huggingface-bootstrap.sh
	bash -n scripts/kernel-setup.sh
	uv lock --check

# CLI contracts use only the standard library; tools are pinned and isolated by uv.
check-bin:
	cd .. && for script in evals/bin/* evals/scripts/*.sh evals/lib/*.sh; do "$${BASH_BIN:-bash}" -n "$$script" || exit; done
	cd .. && uvx --from shellcheck-py==0.11.0.1 shellcheck --external-sources --shell=bash evals/bin/* evals/scripts/*.sh evals/lib/*.sh
	cd .. && uvx --from shfmt-py==4.2.0 shfmt -d -i 2 -ci -bn evals/bin/* evals/scripts/*.sh evals/lib/*.sh
	cd .. && uv run --no-project --python 3.12 python -m unittest discover -s tests -v
