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
