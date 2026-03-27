#!/usr/bin/env bats
# Tests for bin/teardown — safe removal of quanbot setup

TEARDOWN_CMD="$BATS_TEST_DIRNAME/../bin/teardown"

@test "dry-run is the default (no files removed)" {
  run "$TEARDOWN_CMD"

  [ "$status" -eq 0 ]
  [[ "$output" == *"DRY RUN"* ]]
}

@test "prints usage on unknown flag" {
  run "$TEARDOWN_CMD" --unknown-flag

  [ "$status" -eq 1 ]
  [[ "$output" == *"Usage"* ]]
}
