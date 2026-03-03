#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AI_DIR="${AI_DIR_OVERRIDE:-$(cd "${SCRIPT_DIR}/.." && pwd)}"

usage() {
  echo "Usage:"
  echo "  quanbot <planner|implementer|reviewer> <task_file>"
  echo "  quanbot <planner|implementer|reviewer> -"
  echo "  quanbot <planner|implementer|reviewer> --text \"task text\""
}

ROLE="${1:-implementer}"
shift || true

INLINE_TEXT=""
TASK_ARG=""
while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --text)
      shift
      INLINE_TEXT="${1:-}"
      if [[ -z "${INLINE_TEXT}" ]]; then
        echo "Missing value for --text"
        usage
        exit 1
      fi
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      if [[ -z "${TASK_ARG}" ]]; then
        TASK_ARG="$1"
      else
        echo "Unexpected argument: $1"
        usage
        exit 1
      fi
      shift
      ;;
  esac
done

ROLE_PROMPT="${AI_DIR}/prompts/${ROLE}.md"
if [[ ! -f "${ROLE_PROMPT}" ]]; then
  echo "Unknown role: ${ROLE}"
  usage
  exit 1
fi

INPUT_TASK_FILE=""
TASK_SOURCE=""
TMP_TASK=""
if [[ -n "${INLINE_TEXT}" ]]; then
  TMP_TASK="$(mktemp)"
  printf "%s\n" "${INLINE_TEXT}" > "${TMP_TASK}"
  INPUT_TASK_FILE="${TMP_TASK}"
  TASK_SOURCE="inline-text"
elif [[ -n "${TASK_ARG}" && "${TASK_ARG}" != "-" ]]; then
  if [[ ! -f "${TASK_ARG}" ]]; then
    echo "Task file not found: ${TASK_ARG}"
    exit 1
  fi
  INPUT_TASK_FILE="${TASK_ARG}"
  TASK_SOURCE="${TASK_ARG}"
elif [[ "${TASK_ARG:-}" == "-" || ! -t 0 ]]; then
  TMP_TASK="$(mktemp)"
  cat > "${TMP_TASK}"
  if [[ ! -s "${TMP_TASK}" ]]; then
    echo "No task content received from stdin."
    usage
    exit 1
  fi
  INPUT_TASK_FILE="${TMP_TASK}"
  TASK_SOURCE="stdin"
else
  usage
  exit 1
fi

TMP_PROMPT="$(mktemp)"
trap 'rm -f "${TMP_PROMPT}" "${TMP_TASK:-}"' EXIT
cat \
  "${AI_DIR}/identity.md" \
  "${AI_DIR}/rules.md" \
  "${AI_DIR}/workflow.md" \
  "${ROLE_PROMPT}" \
  "${INPUT_TASK_FILE}" > "${TMP_PROMPT}"

echo "Assembled prompt: ${TMP_PROMPT}"
echo "Role: ${ROLE}"
echo "Task source: ${TASK_SOURCE}"

if [[ "${LLM_MODE:-print}" == "print" ]]; then
  echo ""
  echo "LLM_MODE=print; outputting assembled prompt:"
  cat "${TMP_PROMPT}"
  exit 0
fi

if [[ -z "${LLM_CMD:-}" ]]; then
  echo "Set LLM_CMD to execute a provider CLI in run mode."
  echo "Example: export LLM_CMD='cat'"
  exit 1
fi

"${AI_DIR}/scripts/preflight.sh" "${INPUT_TASK_FILE}" || true
cat "${TMP_PROMPT}" | eval "${LLM_CMD}"
