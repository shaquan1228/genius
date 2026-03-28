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

@test "has platform-conditional next steps using uname" {
  run grep 'uname' "$BIN"
  [ "$status" -eq 0 ]
}

@test "Linux path includes source .zshrc instruction" {
  run grep -E 'source.*\.zshrc|source ~/.zshrc' "$BIN"
  [ "$status" -eq 0 ]
}

@test "macOS path still references iTerm2" {
  run grep -E 'iTerm2|iterm' "$BIN"
  [ "$status" -eq 0 ]
}
