#!/usr/bin/env bats
# Tests for bin/setup — bootstrap genius on a new machine

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

@test "bin/setup has --no-profile flag" {
  run grep 'no-profile' "$BIN"
  [ "$status" -eq 0 ]
}

@test "bin/setup uses brew --prefix instead of hardcoded /opt/homebrew for p10k" {
  run grep 'brew --prefix' "$BIN"
  [ "$status" -eq 0 ]
}

@test "bin/setup skips .zshrc modifications when --no-profile is passed" {
  run grep 'SKIP_SHELL_CONFIG\|SKIP_SHELL' "$BIN"
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

@test "bin/setup --no-profile skips without error" {
  # Dry test: verify the flag is handled (won't actually modify the system)
  run grep 'Skipping.*zshrc\|skip.*shell\|SKIP_SHELL' "$BIN"
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

@test "bin/setup supports --help flag" {
  run grep -- '--help\|-h)' "$BIN"
  [ "$status" -eq 0 ]
}

@test "bin/setup adds datestamp to .zshrc modifications" {
  run grep "date.*'+%Y-%m-%d'\|added.*%Y-%m-%d\|%Y-%m-%d.*added" "$BIN"
  [ "$status" -eq 0 ]
}
