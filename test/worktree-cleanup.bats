#!/usr/bin/env bats
# Tests for bin/worktree-cleanup — remove stale temporal worktrees

BIN="$BATS_TEST_DIRNAME/../bin/worktree-cleanup"

@test "has bash shebang and set -euo pipefail" {
  head -20 "$BIN" | grep -q '#!/usr/bin/env bash'
  head -20 "$BIN" | grep -q 'set -euo pipefail'
}

@test "is executable" {
  [ -x "$BIN" ]
}
