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

@test "curl has --connect-timeout flag" {
  grep -q 'connect-timeout' "$BIN"
}

@test "curl has --max-time flag" {
  grep -q 'max-time' "$BIN"
}

@test "prints progress message before brew bundle" {
  local brew_line
  local progress_line
  brew_line=$(grep -n 'brew bundle' "$BIN" | head -1 | cut -d: -f1)
  progress_line=$(grep -n 'minutes\|Brewfile' "$BIN" | grep -i 'install\|installing\|running\|progress' | head -1 | cut -d: -f1)
  [ -n "$progress_line" ]
  [ "$progress_line" -lt "$brew_line" ]
}

@test "prints progress message before npm install" {
  local npm_line
  local progress_line
  npm_line=$(grep -n 'npm install' "$BIN" | head -1 | cut -d: -f1)
  progress_line=$(grep -n 'Graphite\|graphite' "$BIN" | grep -i 'install\|Installing' | head -1 | cut -d: -f1)
  [ -n "$progress_line" ]
  [ "$progress_line" -lt "$npm_line" ]
}
