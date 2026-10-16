#!/bin/sh
set -eu
export PYTHONUNBUFFERED=1

mkdir -p /work /results/live
cp -R /source/. /work/
cd /work
apt-get update -qq
apt-get install -y --no-install-recommends git ocaml-nox ocaml-findlib libjsonm-ocaml-dev
rm -rf /var/lib/apt/lists/*
uv sync --project evals --locked
exec uv run --project evals python -m "${EVAL_RUNNER_MODULE:-evals.python.integrations.hugging_face.job}"
