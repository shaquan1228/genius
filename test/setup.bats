#!/usr/bin/env bats
# Tests for bin/setup — bootstrap quanbot on a new machine

BIN="$BATS_TEST_DIRNAME/../bin/setup"

@test "has bash shebang and set -euo pipefail" {
  head -20 "$BIN" | grep -q '#!/usr/bin/env bash'
  head -20 "$BIN" | grep -q 'set -euo pipefail'
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
