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
