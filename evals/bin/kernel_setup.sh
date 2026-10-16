#!/bin/sh
set -eu

evals_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
kernel_switch=${KERNEL_SWITCH:-genius-kernel-414}
bridge_commit=4bd7956a69f1ee91201f440f3a87fa976dedfc3a

cd "$evals_root"
command -v opam >/dev/null || { echo "Install opam before setting up the OCaml kernel." >&2; exit 1; }
test -x .venv/bin/python || { echo "Run uv sync --python 3.12 --locked --inexact first." >&2; exit 1; }

if ! opam var --global root >/dev/null 2>&1; then
    opam init --bare --no-setup --disable-sandboxing --yes
fi
if ! opam switch list --short | grep -Fx "$kernel_switch" >/dev/null; then
    opam switch create "$kernel_switch" ocaml-base-compiler.4.14.2 --no-switch --yes
fi

# The bridge discovers Python while building; use the same interpreter as the harness.
export PATH="$evals_root/.venv/bin:$PATH"
# Keep the pinned bridge's generated compiler files out of callers' working directories.
bridge_patch=$(.venv/bin/python -c 'import hashlib, pathlib; print(hashlib.sha256(pathlib.Path("kernel/bridge.patch").read_bytes()).hexdigest()[:16])')
bridge_source="$(opam var --global root)/genius-kernel-bridge-$bridge_commit-$bridge_patch"
if ! test -d "$bridge_source/.git"; then
    git clone --no-checkout https://github.com/ocamllibs/ocaml-in-python.git "$bridge_source"
    git -C "$bridge_source" checkout --detach "$bridge_commit"
fi
if ! git -C "$bridge_source" apply --reverse --check "$evals_root/kernel/bridge.patch" 2>/dev/null; then
    git -C "$bridge_source" apply --check "$evals_root/kernel/bridge.patch"
    git -C "$bridge_source" apply "$evals_root/kernel/bridge.patch"
fi
opam pin add --switch="$kernel_switch" --kind=path ocaml-in-python "$bridge_source" --yes --no-action
opam install --switch="$kernel_switch" ocaml-in-python ppxlib.0.26.0 dune.3.24.2 --yes --assume-depexts --jobs=4
bridge_library=$(opam var --switch="$kernel_switch" ocaml-in-python:lib)
# A real search path also avoids the source ocaml/ directory shadowing an editable finder.
.venv/bin/python -c 'import pathlib, sys, sysconfig; pathlib.Path(sysconfig.get_paths()["purelib"], "genius-ocaml.pth").write_text(sys.argv[1] + "\n")' "$bridge_library"
# Build and install the normal findlib package before any Python import.
opam exec --switch="$kernel_switch" -- dune build @install tools/bindings.exe
opam exec --switch="$kernel_switch" -- .venv/bin/python kernel/generate.py
opam exec --switch="$kernel_switch" -- dune install
opam exec --switch="$kernel_switch" -- .venv/bin/python -c 'from kernel import Case, Task, Rubric'
