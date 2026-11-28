#!/bin/sh
# Preserve the unittest pilot's status names for either proof backend.
set -eu
scripts=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
status=0
bash "$scripts/prove.sh" gns-004 unittest "$@" >/dev/null || status=$?
case "$status" in
  0) echo confirmed ;;
  1) echo needs_evidence ;;
  *) echo unavailable ;;
esac
exit "$status"
