#!/usr/bin/env bats
# Tests for bin/teardown — safe removal of quanbot setup

BIN="$BATS_TEST_DIRNAME/../bin/teardown"

@test "has bash shebang and set -euo pipefail" {
  head -20 "$BIN" | grep -q '#!/usr/bin/env bash'
  head -20 "$BIN" | grep -q 'set -euo pipefail'
}

@test "is executable" {
  [ -x "$BIN" ]
}

@test "dry-run is the default (no files removed)" {
  run "$BIN"

  [ "$status" -eq 0 ]
  [[ "$output" == *"DRY RUN"* ]]
}

@test "prints usage on unknown flag" {
  run "$BIN" --unknown-flag

  [ "$status" -eq 1 ]
  [[ "$output" == *"Usage"* ]]
}
