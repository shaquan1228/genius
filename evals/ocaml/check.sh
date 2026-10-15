#!/bin/sh
# Compile a fresh copy so checking never changes the agent's worktree.
set -eu
build_dir=$(mktemp -d)
trap 'rm -rf "$build_dir"' EXIT HUP INT TERM
if [ "$1" = --stdin ]; then
  shift
  cp -- "$@" "$build_dir/"
  cat > "$build_dir/heldout.ml"
  set -- "$@" heldout.ml
else
  cp -- "$@" "$build_dir/"
fi
cd "$build_dir"
ocamlc -o checks "$@" || exit 65
./checks
