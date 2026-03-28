#!/usr/bin/env bats

@test "bin/setup detects platform with uname" {
  run grep 'uname' bin/setup
  [ "$status" -eq 0 ]
}

@test "bin/setup uses brew --prefix instead of hardcoded /opt/homebrew for p10k" {
  run grep 'brew --prefix' bin/setup
  [ "$status" -eq 0 ]
}

@test "bin/setup does not hardcode /opt/homebrew for powerlevel10k" {
  run grep -F '/opt/homebrew/share/powerlevel10k' bin/setup
  [ "$status" -ne 0 ]
}

@test "bin/setup guards iTerm2 section with Darwin platform check" {
  run grep 'Darwin' bin/setup
  [ "$status" -eq 0 ]
}
