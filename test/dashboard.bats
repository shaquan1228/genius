#!/usr/bin/env bats
# Tests for bin/dashboard — TUI status display

BIN="$BATS_TEST_DIRNAME/../bin/dashboard"

@test "has bash shebang" {
  head -5 "$BIN" | grep -q '#!/usr/bin/env bash'
}

@test "is executable" {
  [ -x "$BIN" ]
}

@test "references docs/dreams/STOP-TINKERING.md (not docs/dev/)" {
  grep -q 'docs/dreams/STOP-TINKERING\.md' "$BIN"
}

@test "does not reference docs/dev/STOP-TINKERING.md" {
  run grep 'docs/dev/STOP-TINKERING' "$BIN"
  [ "$status" -ne 0 ]
}
