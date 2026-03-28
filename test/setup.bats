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

@test "bin/setup detects platform with uname" {
  run grep 'uname' "$BIN"
  [ "$status" -eq 0 ]
}

@test "bin/setup uses brew --prefix instead of hardcoded /opt/homebrew for p10k" {
  run grep 'brew --prefix' "$BIN"
  [ "$status" -eq 0 ]
}

@test "bin/setup does not hardcode /opt/homebrew for powerlevel10k" {
  run grep -F '/opt/homebrew/share/powerlevel10k' "$BIN"
  [ "$status" -ne 0 ]
}

@test "bin/setup guards iTerm2 section with Darwin platform check" {
  run grep 'Darwin' "$BIN"
  [ "$status" -eq 0 ]
}
