#!/usr/bin/env bats
# Tests for bin/tmux-init-session — dashboard window

@test "tmux-init-session uses dashboard-go for dashboard window" {
  run grep 'dashboard-go' bin/tmux-init-session
  [ "$status" -eq 0 ]
}
