#!/usr/bin/env bats
# Tests for bin/teardown — safe removal of quanbot setup

setup() {
  TEST_HOME="$(mktemp -d)"
  TEARDOWN_CMD="$BATS_TEST_DIRNAME/../bin/teardown"
}

teardown() {
  rm -rf "$TEST_HOME"
}

@test "dry-run is the default (no files removed)" {
  # Create fake symlinks that teardown would target
  mkdir -p "$TEST_HOME/.claude"
  touch "$TEST_HOME/fakefile"

  run "$TEARDOWN_CMD"

  [ "$status" -eq 0 ]
  [[ "$output" == *"DRY RUN"* ]]
}

@test "prints usage on unknown flag" {
  run "$TEARDOWN_CMD" --unknown-flag

  [ "$status" -eq 1 ]
  [[ "$output" == *"Usage"* ]]
}
