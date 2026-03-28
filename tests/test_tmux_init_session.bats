#!/usr/bin/env bats

@test "tmux-init-session checks dashboard-go is executable before using it" {
  run grep '\-x.*dashboard-go\|dashboard-go.*-x' bin/tmux-init-session
  [ "$status" -eq 0 ]
}

@test "tmux-init-session falls back to bin/dashboard" {
  run grep 'bin/dashboard[^-]' bin/tmux-init-session
  [ "$status" -eq 0 ]
}
