#!/usr/bin/env bash
set -euo pipefail

TASK_FILE="${1:-}"
if [[ -z "${TASK_FILE}" ]]; then
  echo "Usage: ai/scripts/preflight.sh <task_file>"
  exit 1
fi

if [[ ! -f "${TASK_FILE}" ]]; then
  echo "Task file not found: ${TASK_FILE}"
  exit 1
fi

WARNINGS=0

check_contains() {
  local pattern="$1"
  local message="$2"
  if ! grep -Eiq "${pattern}" "${TASK_FILE}"; then
    echo "Warning: ${message}"
    WARNINGS=$((WARNINGS + 1))
  fi
}

check_contains "acceptance|done|success|outcome" \
  "Task does not appear to define acceptance criteria."
check_contains "test|spec|verify|validation" \
  "Task does not explicitly call out tests or verification."
check_contains "error|failure|fallback|edge case|risk" \
  "Task may not mention failure handling or edge cases."

if [[ "${WARNINGS}" -eq 0 ]]; then
  echo "Preflight: no warnings."
else
  echo "Preflight: ${WARNINGS} warning(s)."
fi
