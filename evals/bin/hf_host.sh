#!/bin/sh
set -eu

: "${HF_NAMESPACE:?Set HF_NAMESPACE to your Hugging Face username or organization}"
: "${EVAL_MODEL:?Set EVAL_MODEL to an exact Inspect provider/model ID}"
EVAL_EPOCHS="${EVAL_EPOCHS:-1}"
EVAL_MAX_SAMPLES="${EVAL_MAX_SAMPLES:-1}"
EVAL_RUN_ID="${EVAL_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)-$$}"
case "$EVAL_MAX_SAMPLES" in
  [1-9]|1[0-6]) ;;
  *) echo "EVAL_MAX_SAMPLES must be an integer from 1 to 16" >&2; exit 2 ;;
esac

case "$EVAL_MODEL" in
  hf-inference-providers/*)
    : "${EVAL_MODEL_COST:?Set EVAL_MODEL_COST to the exact routed provider token prices}"
    provider_key=; default_agent=codex ;;
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

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$repo_root"

hf() { uvx --from huggingface_hub==2.2.0 hf "$@"; }
source_repo="$HF_NAMESPACE/genius-evals-$(date -u +%Y%m%dT%H%M%SZ)-$$"
results_bucket="$HF_NAMESPACE/genius-eval-results"
snapshot_dir=$(mktemp -d)
trap 'rm -rf "$snapshot_dir"' EXIT HUP INT TERM
git -c safe.directory="$(pwd)" archive HEAD README.md docs skills evals | tar -x -C "$snapshot_dir"

hf repos create "$source_repo" --repo-type dataset --private
hf buckets create "$results_bucket" --private --exist-ok
hf upload "$source_repo" "$snapshot_dir" . --repo-type dataset \
  --commit-message 'Immutable Genius evaluation source'

set -- --secrets HF_TOKEN
if [ -n "$provider_key" ]; then
  set -- "$@" --secrets "$provider_key"
fi

hf jobs run --name genius-evals --namespace "$HF_NAMESPACE" --timeout "${EVAL_JOB_TIMEOUT:-4h}" \
  --volume "hf://datasets/$source_repo:/source:ro" \
  --volume "hf://buckets/$results_bucket:/results:rw" \
  "$@" \
  --env "EVAL_AGENT=$EVAL_AGENT" --env "EVAL_MODEL=$EVAL_MODEL" \
  --env "EVAL_VERSION=${EVAL_VERSION:-}" \
  --env "EVAL_VARIANT=${EVAL_VARIANT:-}" \
  --env "HF_NAMESPACE=$HF_NAMESPACE" \
  --env "EVAL_SANDBOX_IMAGE=${EVAL_SANDBOX_IMAGE:-}" \
  --env "EVAL_RUN_ID=${EVAL_RUN_ID:-}" \
  --env "EVAL_MAX_SAMPLES=$EVAL_MAX_SAMPLES" \
  --env "EVAL_EPOCHS=$EVAL_EPOCHS" \
  --env "EVAL_DATASET=${EVAL_DATASET:-smoke}" --env "EVAL_LIMIT=${EVAL_LIMIT:-}" \
  --env "EVAL_SAMPLE_IDS=${EVAL_SAMPLE_IDS:-}" --env "EVAL_COST_LIMIT=${EVAL_COST_LIMIT:-0.25}" \
  --env "EVAL_TIME_LIMIT=${EVAL_TIME_LIMIT:-}" \
  --env "EVAL_MESSAGE_LIMIT=${EVAL_MESSAGE_LIMIT:-}" \
  --env "EVAL_CACHE=${EVAL_CACHE:-}" \
  --env "EVAL_MODEL_COST=${EVAL_MODEL_COST:-}" \
  --env "EVAL_INSTRUCTION_DELIVERY=${EVAL_INSTRUCTION_DELIVERY:-files}" \
  --env "EVAL_DELIVERIES=${EVAL_DELIVERIES:-}" \
  ghcr.io/astral-sh/uv:python3.12-bookworm sh /source/evals/bin/hf_bootstrap.sh
