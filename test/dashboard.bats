#!/usr/bin/env bats
# Tests for bin/dashboard — TUI status display

BIN="$BATS_TEST_DIRNAME/../bin/dashboard"

@test "has bash shebang" {
  head -5 "$BIN" | grep -q '#!/usr/bin/env bash'
}

@test "is executable" {
  [ -x "$BIN" ]
}

@test "shows universal tmux Ctrl+b keybinding" {
  run grep 'Ctrl+b' "$BIN"
  [ "$status" -eq 0 ]
}
