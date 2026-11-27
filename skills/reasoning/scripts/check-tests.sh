#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BEND_NO_TELEMETRY=1 exec "${BEND_BIN:-bend}" \
  "$script_dir/../../../docs/proofs/reasoning/check-tests.bend" "$@"
