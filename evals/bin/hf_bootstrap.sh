#!/bin/sh
set -eu
export PYTHONUNBUFFERED=1

mkdir -p /work /results/live
cp -R /source/. /work/
cd /work
apt-get update -qq
apt-get install -y --no-install-recommends git opam build-essential pkg-config rsync
rm -rf /var/lib/apt/lists/*
uv sync --project evals --python 3.12 --locked --inexact
# Install the Dune/findlib kernel and compiler-derived bindings before starting Python.
sh evals/bin/kernel_setup.sh
exec opam exec --switch="${KERNEL_SWITCH:-genius-kernel-414}" -- \
    uv run --project evals --no-sync python -m "${EVAL_RUNNER_MODULE:-evals.python.integrations.hugging_face.job}"
