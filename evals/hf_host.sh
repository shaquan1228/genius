#!/bin/sh
set -eu

: "${HF_NAMESPACE:?Set HF_NAMESPACE to your Hugging Face username or organization}"
: "${EVAL_MODEL:?Set EVAL_MODEL to an exact Inspect provider/model ID}"
EVAL_EPOCHS="${EVAL_EPOCHS:-1}"

case "$EVAL_MODEL" in
  openai/*) provider_key=OPENAI_API_KEY; default_agent=codex ;;
  anthropic/*) provider_key=ANTHROPIC_API_KEY; default_agent=claude ;;
  *) echo "EVAL_MODEL must start with openai/ or anthropic/" >&2; exit 2 ;;
esac
EVAL_AGENT="${EVAL_AGENT:-$default_agent}"

if ! printenv "$provider_key" >/dev/null; then
  echo "Set $provider_key in this shell before launching the Job" >&2
  exit 2
fi

hf() { uvx --from huggingface_hub==2.2.0 hf "$@"; }
source_repo="$HF_NAMESPACE/genius-evals"
results_bucket="$HF_NAMESPACE/genius-eval-results"

hf repos create "$source_repo" --repo-type dataset --private --exist-ok
hf buckets create "$results_bucket" --private --exist-ok
hf upload "$source_repo" . . --repo-type dataset \
  --include README.md --include 'docs/**' --include 'skills/**' --include 'evals/**' \
  --exclude 'evals/.venv/**' --exclude 'evals/results/**' \
  --exclude '**/__pycache__/**' --exclude '**/.mypy_cache/**' \
  --commit-message 'Update Genius evaluation source'

hf jobs run --detach --name genius-evals --namespace "$HF_NAMESPACE" --timeout 4h \
  --volume "hf://datasets/$source_repo:/source:ro" \
  --volume "hf://buckets/$results_bucket:/results:rw" \
  --secrets HF_TOKEN --secrets "$provider_key" \
  --env "EVAL_AGENT=$EVAL_AGENT" --env "EVAL_MODEL=$EVAL_MODEL" \
  --env "EVAL_EPOCHS=$EVAL_EPOCHS" \
  ghcr.io/astral-sh/uv:python3.12-bookworm sh /source/evals/hf_bootstrap.sh
