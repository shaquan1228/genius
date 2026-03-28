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

@test "teardown uses mktemp for safe temporary file creation" {
  run grep 'mktemp' "$BIN"
  [ "$status" -eq 0 ]
}

@test "teardown creates timestamped backup before modifying files" {
  run grep '\.bak\.' "$BIN"
  [ "$status" -eq 0 ]
}

@test "teardown has size guard to prevent empty file overwrite" {
  run grep '\-s "\$' "$BIN"
  [ "$status" -eq 0 ]
}

@test "teardown remove_line_from_file does not use predictable .tmp extension" {
  run grep '${file}\.tmp\|"${file}\.tmp"' "$BIN"
  [ "$status" -ne 0 ]
}
