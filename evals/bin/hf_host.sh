#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
readonly SCRIPT_DIR
# shellcheck source=evals/bin/lib/common.bash
source "$SCRIPT_DIR/lib/common.bash"

usage() {
  cat <<'HELP'
Usage: evals/bin/hf_host.sh [--dry-run]
Upload committed sources and run a Hugging Face evaluation Job (charges apply).

Examples:
  HF_NAMESPACE=my-team EVAL_MODEL=openai/pinned-model evals/bin/hf_host.sh --dry-run
  HF_NAMESPACE=my-team EVAL_MODEL=openai/pinned-model evals/bin/hf_host.sh

Options:
  -n, --dry-run  Validate configuration and show the plan without network access.
  -h, --help     Show this help without credentials or optional tools.

Required environment:
  HF_NAMESPACE  Your Hugging Face user or organization.
  EVAL_MODEL    openai/..., anthropic/..., or hf-inference-providers/...

Direct providers require OPENAI_API_KEY or ANTHROPIC_API_KEY; HF routes require
EVAL_MODEL_COST. EVAL_EPOCHS defaults to 1; EVAL_MAX_SAMPLES is 1-16 (default 1).
Configure other EVAL_* settings as documented below; secrets are passed by name.
Help: https://github.com/shaquan1228/genius/tree/main/evals#run-on-hugging-face
HELP
}

hf() { uvx --from huggingface_hub==2.2.0 hf "$@"; }

validate_settings() {
  [[ -n ${HF_NAMESPACE:-} ]] || cli_usage_error 'Set HF_NAMESPACE to your Hugging Face username or organization.'
  [[ -n ${EVAL_MODEL:-} ]] || cli_usage_error 'Set EVAL_MODEL to an exact Inspect provider/model ID.'
  [[ $epochs =~ ^[1-9][0-9]*$ ]] || cli_usage_error 'EVAL_EPOCHS must be a positive integer.'
  case $max_samples in [1-9] | 1[0-6]) ;; *) cli_usage_error 'EVAL_MAX_SAMPLES must be an integer from 1 to 16.' ;; esac
  case $EVAL_MODEL in
    hf-inference-providers/?*)
      [[ -n ${EVAL_MODEL_COST:-} ]] || cli_usage_error 'Set EVAL_MODEL_COST to the exact routed provider token prices.'
      provider_key=
      default_agent=codex
      ;;
    openai/?*)
      provider_key=OPENAI_API_KEY
      default_agent=codex
      ;;
    anthropic/?*)
      provider_key=ANTHROPIC_API_KEY
      default_agent=claude
      ;;
    *) cli_usage_error 'Use an hf-inference-providers/, openai/, or anthropic/ model.' ;;
  esac
}

upload_snapshot() {
  local snapshot_dir
  cli_temp_dir
  snapshot_dir=$REPLY
  # Materialize the archive before extraction: either failure stops before any upload.
  git -c safe.directory="$PWD" archive --output="$snapshot_dir/source.tar" HEAD README.md docs skills evals
  mkdir -- "$snapshot_dir/tree"
  tar -xf "$snapshot_dir/source.tar" -C "$snapshot_dir/tree"
  hf repos create "$source_repo" --repo-type dataset --private >&2
  hf buckets create "$results_bucket" --private --exist-ok >&2
  hf upload "$source_repo" "$snapshot_dir/tree" . --repo-type dataset \
    --commit-message 'Immutable Genius evaluation source' >&2
}

launch_job() {
  local name
  local -a arguments=(jobs run --name genius-evals --namespace "$HF_NAMESPACE"
    --timeout "${EVAL_JOB_TIMEOUT:-4h}"
    --volume "hf://datasets/$source_repo:/source:ro"
    --volume "hf://buckets/$results_bucket:/results:rw" --secrets HF_TOKEN)
  if [[ -n $provider_key ]]; then arguments+=(--secrets "$provider_key"); fi
  export EVAL_AGENT=${EVAL_AGENT:-$default_agent} EVAL_EPOCHS=$epochs EVAL_MAX_SAMPLES=$max_samples
  export EVAL_RUN_ID=${EVAL_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)-$$}
  export EVAL_DATASET=${EVAL_DATASET:-smoke} EVAL_COST_LIMIT=${EVAL_COST_LIMIT:-0.25}
  export EVAL_INSTRUCTION_DELIVERY=${EVAL_INSTRUCTION_DELIVERY:-files}
  # An explicit allowlist prevents unrelated environment values or secrets being sent.
  for name in EVAL_AGENT EVAL_MODEL EVAL_VERSION EVAL_VARIANT HF_NAMESPACE \
    EVAL_SANDBOX_IMAGE EVAL_RUN_ID EVAL_MAX_SAMPLES EVAL_EPOCHS EVAL_DATASET \
    EVAL_LIMIT EVAL_SAMPLE_IDS EVAL_COST_LIMIT EVAL_TIME_LIMIT EVAL_MESSAGE_LIMIT \
    EVAL_CACHE EVAL_MODEL_COST EVAL_INSTRUCTION_DELIVERY EVAL_DELIVERIES; do
    arguments+=(--env "$name=${!name:-}")
  done
  hf "${arguments[@]}" ghcr.io/astral-sh/uv:python3.12-bookworm bash /source/evals/bin/hf_bootstrap.sh
}

main() {
  cli_help "$@"
  local dry_run=0
  while (($#)); do
    case $1 in
      -n | --dry-run) dry_run=1 ;;
      --)
        shift
        cli_no_arguments "$@"
        break
        ;;
      *) cli_usage_error "Unexpected argument: $1" ;;
    esac
    shift
  done
  local epochs=${EVAL_EPOCHS:-1} max_samples=${EVAL_MAX_SAMPLES:-1} provider_key default_agent
  validate_settings
  cd -- "$SCRIPT_DIR/../.."
  if ((dry_run)); then
    printf 'Would upload committed sources from %s\nWould launch %s with %s (epochs=%s, concurrency=%s)\n' \
      "$PWD" "$EVAL_MODEL" "${EVAL_AGENT:-$default_agent}" "$epochs" "$max_samples"
    return
  fi
  if [[ -n $provider_key && -z ${!provider_key:-} ]]; then
    cli_usage_error "Set $provider_key in this shell before launching the Job."
  fi
  cli_require uvx git tar mkdir mktemp date
  local source_repo
  source_repo=$HF_NAMESPACE/genius-evals-$(date -u +%Y%m%dT%H%M%SZ)-$$
  local results_bucket=$HF_NAMESPACE/genius-eval-results
  cli_info 'Uploading committed evaluation sources.'
  upload_snapshot
  cli_info "Launching $EVAL_MODEL; results: hf://buckets/$results_bucket"
  launch_job
}

cli_init
main "$@"
