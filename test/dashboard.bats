#!/usr/bin/env bats
# Tests for bin/dashboard — TUI status display

BIN="$BATS_TEST_DIRNAME/../bin/dashboard"

@test "has bash shebang" {
  head -5 "$BIN" | grep -q '#!/usr/bin/env bash'
}

@test "is executable" {
  [ -x "$BIN" ]
}

@test "tmux-init-session checks dashboard-go is executable before using it" {
  run grep '\-x.*dashboard-go\|dashboard-go.*-x' bin/tmux-init-session
  [ "$status" -eq 0 ]
}

@test "tmux-init-session falls back to bin/dashboard" {
  run grep 'bin/dashboard[^-]' bin/tmux-init-session
  [ "$status" -eq 0 ]
}
