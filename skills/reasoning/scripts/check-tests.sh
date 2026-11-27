#!/bin/sh
# Compatibility for callers of the original unittest pilot.
set -eu
scripts=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
status=0
result=$(bash "$scripts/prove.sh" gns-004 unittest "$@") || status=$?
case "$result" in
  supported) echo confirmed ;;
  contradicted) echo needs_evidence ;;
  *) echo unavailable ;;
esac
exit "$status"
