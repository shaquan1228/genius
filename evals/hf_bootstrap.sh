#!/bin/sh
set -eu

mkdir -p /work /results/live
cp -R /source/. /work/
cd /work
apt-get update -qq
apt-get install -y --no-install-recommends ocaml-nox
rm -rf /var/lib/apt/lists/*
uv sync --project evals --locked
exec uv run --project evals python -c 'from evals.hf_job import run; raise SystemExit(run())'
