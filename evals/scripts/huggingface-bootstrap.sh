#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
readonly SCRIPT_DIR
# shellcheck source=evals/lib/shell.sh
source "$SCRIPT_DIR/../lib/shell.sh"

usage() {
  cat <<'HELP'
Usage: evals/scripts/huggingface-bootstrap.sh [options]
Prepare a Hugging Face worker and replace this process with the evaluation runner.
Defaults match the Debian Job image and volume mounts used by huggingface-run.
Missing build tools are installed with apt-get, requiring root in that case.

Example:
  evals/scripts/huggingface-bootstrap.sh --source-dir /source --work-dir /work --results-dir /results

Options:
  --source-dir DIR   Committed source snapshot (default: /source).
  --work-dir DIR     Writable working copy (default: /work).
  --results-dir DIR  Writable results directory (default: /results).
  -h, --help         Show help without filesystem or network changes.

Environment: EVAL_RUNNER_MODULE and EVAL_* runner settings.
Help: https://github.com/shaquan1228/genius/tree/main/evals#run-on-hugging-face
HELP
}

build_tools() {
  local tool
  for tool in git cc; do
    if ! command -v "$tool" >/dev/null 2>&1; then
      cli_require apt-get
      ((EUID == 0)) || cli_die 'Installing missing build tools requires root; install the tools yourself and retry.'
      cli_info 'Installing worker build tools.'
      apt-get update -qq >&2
      apt-get install -y --no-install-recommends git build-essential >&2
      return
    fi
  done
}

main() {
  cli_help "$@"
  local source_dir=/source work_dir=/work results_dir=/results
  while (($#)); do
    case $1 in
      --source-dir | --work-dir | --results-dir)
        [[ $# -ge 2 && -n $2 && $2 != --* ]] || cli_usage_error "$1 requires a directory."
        case $1 in
          --source-dir) source_dir=$2 ;;
          --work-dir) work_dir=$2 ;;
          --results-dir) results_dir=$2 ;;
        esac
        shift
        ;;
      --)
        shift
        cli_no_arguments "$@"
        break
        ;;
      *) cli_usage_error "Unexpected argument: $1" ;;
    esac
    shift
  done
  [[ -f $source_dir/evals/pyproject.toml ]] || cli_die "Source snapshot not found: $source_dir"
  cli_require cp mkdir uv
  source_dir=$(CDPATH='' cd -- "$source_dir" && pwd -P)
  mkdir -p -- "$work_dir" "$results_dir/live"
  work_dir=$(CDPATH='' cd -- "$work_dir" && pwd -P)
  results_dir=$(CDPATH='' cd -- "$results_dir" && pwd -P)
  case $work_dir/ in "$source_dir/"*) cli_usage_error 'Working directory must be outside the source snapshot.' ;; esac
  build_tools
  export PYTHONUNBUFFERED=1
  export EVAL_LOG_DIR=${EVAL_LOG_DIR:-$results_dir/live}
  cli_info "Preparing evaluation in $work_dir"
  cp -R -- "$source_dir/." "$work_dir/"
  cd -- "$work_dir"
  uv sync --project evals --python 3.12 --locked --inexact >&2
  cli_info 'Starting evaluation runner.'
  exec uv run --project evals --no-sync python -m "${EVAL_RUNNER_MODULE:-evals.python.integrations.hugging_face.job}"
}

cli_init
main "$@"
