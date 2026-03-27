#!/usr/bin/env bats
# Tests for bin/tmux-init-session — initialize tmux workspace layout

BIN="$BATS_TEST_DIRNAME/../bin/tmux-init-session"

@test "has bash shebang" {
  head -5 "$BIN" | grep -q '#!/usr/bin/env bash'
}

@test "is executable" {
  [ -x "$BIN" ]
}
