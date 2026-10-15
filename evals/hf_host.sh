#!/bin/sh
set -eu

: "${HF_NAMESPACE:?Set HF_NAMESPACE to your Hugging Face username or organization}"
: "${EVAL_MODEL:?Set EVAL_MODEL to an exact Inspect provider/model ID}"
EVAL_EPOCHS="${EVAL_EPOCHS:-1}"

case "$EVAL_MODEL" in
  hf-inference-providers/*) provider_key=; default_agent=codex ;;
  openai/*) provider_key=OPENAI_API_KEY; default_agent=codex ;;
  anthropic/*) provider_key=ANTHROPIC_API_KEY; default_agent=claude ;;
  *) echo "Use an hf-inference-providers/, openai/, or anthropic/ model" >&2; exit 2 ;;
esac
EVAL_AGENT="${EVAL_AGENT:-$default_agent}"

# CI passes unset secrets as empty strings, so require a non-empty key.
if [ -n "$provider_key" ] && [ -z "$(printenv "$provider_key")" ]; then
  echo "Set $provider_key in this shell before launching the Job" >&2
  exit 2
fi

hf() { uvx --from huggingface_hub==2.2.0 hf "$@"; }
source_repo="$HF_NAMESPACE/genius-evals"
results_bucket="$HF_NAMESPACE/genius-eval-results"
snapshot_dir=$(mktemp -d)
trap 'rm -rf "$snapshot_dir"' EXIT HUP INT TERM
git archive HEAD README.md docs skills evals | tar -x -C "$snapshot_dir"

hf repos create "$source_repo" --repo-type dataset --private --exist-ok
hf buckets create "$results_bucket" --private --exist-ok
hf upload "$source_repo" "$snapshot_dir" . --repo-type dataset \
  --delete 'evals/.coverage' --delete 'evals/.pytest_cache/**' \
  --delete 'evals/.ruff_cache/**' --delete 'evals/genius_evals.egg-info/**' \
  --commit-message 'Update Genius evaluation source'

set -- --secrets HF_TOKEN
if [ -n "$provider_key" ]; then
  set -- "$@" --secrets "$provider_key"
fi

hf jobs run --detach --name genius-evals --namespace "$HF_NAMESPACE" --timeout 4h \
  --volume "hf://datasets/$source_repo:/source:ro" \
  --volume "hf://buckets/$results_bucket:/results:rw" \
  "$@" \
  --env "EVAL_AGENT=$EVAL_AGENT" --env "EVAL_MODEL=$EVAL_MODEL" \
  --env "EVAL_VERSION=${EVAL_VERSION:-}" \
  --env "EVAL_EPOCHS=$EVAL_EPOCHS" \
  ghcr.io/astral-sh/uv:python3.12-bookworm sh /source/evals/hf_bootstrap.sh
