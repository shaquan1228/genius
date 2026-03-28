#!/usr/bin/env bats

@test "bin/setup curl has --connect-timeout flag" {
  run grep 'connect-timeout' bin/setup
  [ "$status" -eq 0 ]
}

@test "bin/setup curl has --max-time flag" {
  run grep 'max-time' bin/setup
  [ "$status" -eq 0 ]
}

@test "bin/setup prints progress message before brew bundle" {
  local brew_line
  local progress_line
  brew_line=$(grep -n 'brew bundle' bin/setup | head -1 | cut -d: -f1)
  progress_line=$(grep -n 'minutes\|Brewfile' bin/setup | grep -i 'install\|installing\|running\|progress' | head -1 | cut -d: -f1)
  [ -n "$progress_line" ]
  [ "$progress_line" -lt "$brew_line" ]
}

@test "bin/setup prints progress message before npm install" {
  local npm_line
  local progress_line
  npm_line=$(grep -n 'npm install' bin/setup | head -1 | cut -d: -f1)
  progress_line=$(grep -n 'Graphite\|graphite' bin/setup | grep -i 'install\|Installing' | head -1 | cut -d: -f1)
  [ -n "$progress_line" ]
  [ "$progress_line" -lt "$npm_line" ]
}
