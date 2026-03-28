#!/usr/bin/env bats

@test "bin/worktree respects QUANBOT_WORKTREE_DIR env var" {
  run grep 'QUANBOT_WORKTREE_DIR' bin/worktree
  [ "$status" -eq 0 ]
}

@test "bin/worktree-agent respects QUANBOT_WORKTREE_DIR env var" {
  run grep 'QUANBOT_WORKTREE_DIR' bin/worktree-agent
  [ "$status" -eq 0 ]
}

@test "bin/worktree-cleanup respects QUANBOT_WORKTREE_DIR env var" {
  run grep 'QUANBOT_WORKTREE_DIR' bin/worktree-cleanup
  [ "$status" -eq 0 ]
}

@test "worktree falls back to ~/Desktop when it exists" {
  run grep 'Desktop' bin/worktree
  [ "$status" -eq 0 ]
}

@test "worktree falls back to HOME when no Desktop" {
  run grep 'HOME\b' bin/worktree
  [ "$status" -eq 0 ]
}
