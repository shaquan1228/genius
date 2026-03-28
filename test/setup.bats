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

@test "bin/setup validates ROOT_DIR before interpolating into files" {
  run grep 'ROOT_DIR.*=~\|=~.*ROOT_DIR' bin/setup
  [ "$status" -eq 0 ]
}

@test "ROOT_DIR validation rejects paths with shell metacharacters" {
  result=$(bash -c '
    ROOT_DIR="/tmp/evil\$(id)/repo"
    if [[ ! "$ROOT_DIR" =~ ^[a-zA-Z0-9/_.-]+$ ]]; then
      echo "rejected"; exit 1
    fi
    echo "accepted"
  ' 2>&1) || true
  [ "$result" = "rejected" ]
}

@test "ROOT_DIR validation accepts normal repository paths" {
  result=$(bash -c '
    ROOT_DIR="/Users/me/Repositories/quanbot"
    if [[ ! "$ROOT_DIR" =~ ^[a-zA-Z0-9/_.-]+$ ]]; then
      echo "rejected"; exit 1
    fi
    echo "accepted"
  ')
  [ "$result" = "accepted" ]
}

@test "bin/setup exits before writing CLAUDE.md on invalid ROOT_DIR" {
  run grep 'exit 1' bin/setup
  [ "$status" -eq 0 ]
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
