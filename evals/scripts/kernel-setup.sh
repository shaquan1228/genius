#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
readonly SCRIPT_DIR
# shellcheck source=evals/lib/shell.sh
source "$SCRIPT_DIR/../lib/shell.sh"

usage() {
  cat <<'HELP'
Usage: evals/scripts/kernel-setup.sh
Build the pinned OCaml kernel for an existing CPython 3.12 environment.
Run `make -C evals setup` to create the Python environment as well.

Examples:
  evals/scripts/kernel-setup.sh
  KERNEL_PYTHON=/path/to/env/bin/python evals/scripts/kernel-setup.sh

Options:
  -h, --help  Show help without requiring Python, opam, or network access.

Environment:
  KERNEL_SWITCH           OCaml 4.14.2 switch (default: genius-kernel-414).
  KERNEL_PYTHON           Explicit environment interpreter.
  UV_PROJECT_ENVIRONMENT Environment directory; relative paths use evals/.
  KERNEL_JOBS             Positive build job count (default: 2).

Concurrent setup using the same bridge cache fails without changing that cache.
Help: https://github.com/shaquan1228/genius/tree/main/evals
HELP
}

kernel_environment() {
  local environment=${UV_PROJECT_ENVIRONMENT:-.venv}
  case $environment in /*) ;; *) environment="$evals_root/$environment" ;; esac
  kernel_python=${KERNEL_PYTHON:-$environment/bin/python}
  [[ -x $kernel_python ]] || cli_die 'Python environment not found. Run make -C evals setup or set KERNEL_PYTHON.'
  kernel_python=$("$kernel_python" -c 'import sys; print(sys.executable)')
  "$kernel_python" -c 'import sys; sys.exit(0 if sys.implementation.name == "cpython" and sys.version_info[:2] == (3, 12) else "The native bridge requires CPython 3.12")'
  export PATH="${kernel_python%/*}:$PATH"
}

kernel_switch_setup() {
  local root switches
  root=$(opam var --global root 2>/dev/null) || root=
  if [[ -z $root || ! -f $root/config ]]; then
    opam init --bare --no-setup --disable-sandboxing --yes >&2
  fi
  switches=$(opam switch list --short)
  if ! grep -Fx -- "$kernel_switch" <<<"$switches" >/dev/null; then
    opam switch create "$kernel_switch" ocaml-base-compiler.4.14.2 --no-switch --yes --jobs="$kernel_jobs" >&2
  fi
  [[ $(opam var --switch="$kernel_switch" ocaml:version) == 4.14.2 ]] \
    || cli_die 'KERNEL_SWITCH must use OCaml 4.14.2. Choose a separate switch.'
}

kernel_bridge_source() {
  local patch_hash root lock temporary
  patch_hash=$("$kernel_python" -c 'import hashlib, pathlib; print(hashlib.sha256(pathlib.Path("python/kernel/bridge.patch").read_bytes()).hexdigest()[:16])')
  root=$(opam var --global root)
  bridge_source="$root/genius-kernel-bridge-$bridge_commit-$patch_hash"
  lock=$bridge_source.lock
  mkdir -- "$lock" 2>/dev/null || cli_die "Bridge cache is busy: $lock. Retry when the other setup finishes; remove stale locks only when no setup is running."
  CLI_TEMP_PATHS+=("$lock")
  if [[ ! -d $bridge_source ]]; then
    cli_temp_dir "$root"
    temporary=$REPLY/source
    git clone --no-checkout https://github.com/ocamllibs/ocaml-in-python.git "$temporary" >&2
    git -C "$temporary" checkout --detach "$bridge_commit" >&2
    mv -- "$temporary" "$bridge_source"
  fi
  [[ $(git -C "$bridge_source" rev-parse HEAD) == "$bridge_commit" ]] \
    || cli_die "Bridge cache revision differs from its pin: $bridge_source"
  if ! git -C "$bridge_source" apply --reverse --check "$evals_root/python/kernel/bridge.patch" 2>/dev/null; then
    git -C "$bridge_source" apply --check "$evals_root/python/kernel/bridge.patch"
    git -C "$bridge_source" apply "$evals_root/python/kernel/bridge.patch"
  fi
}

kernel_install() {
  opam pin add --switch="$kernel_switch" --kind=path ocaml-in-python "$bridge_source" --yes --no-action >&2
  opam install --switch="$kernel_switch" ocaml-in-python ppxlib.0.26.0 dune.3.24.2 --yes --jobs="$kernel_jobs" >&2
  local bridge_library purelib
  bridge_library=$(opam var --switch="$kernel_switch" ocaml-in-python:lib)
  purelib=$("$kernel_python" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
  file_update "$purelib/genius-ocaml.pth" printf '%s\n' "$bridge_library"
  opam exec --switch="$kernel_switch" -- dune build @install @python-bindings >&2
  opam exec --switch="$kernel_switch" -- dune install >&2
  opam exec --switch="$kernel_switch" -- "$kernel_python" -c 'from kernel import Case, Task, Rubric'
}

main() {
  cli_help "$@"
  cli_no_arguments "$@"
  local evals_root=$SCRIPT_DIR/.. kernel_python bridge_source
  local kernel_switch=${KERNEL_SWITCH:-genius-kernel-414} kernel_jobs=${KERNEL_JOBS:-2}
  local bridge_commit=4bd7956a69f1ee91201f440f3a87fa976dedfc3a
  [[ $kernel_jobs =~ ^[1-9][0-9]*$ ]] || cli_usage_error 'KERNEL_JOBS must be a positive integer.'
  cli_require opam git grep mkdir mktemp mv cp cmp
  kernel_environment
  cd -- "$evals_root"
  evals_root=$PWD
  cli_info "Preparing native kernel in switch $kernel_switch"
  kernel_switch_setup
  kernel_bridge_source
  kernel_install
  cli_info 'Native kernel is ready.'
}

cli_init
main "$@"
