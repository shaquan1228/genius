#!/usr/bin/env bats

@test "worktree-cleanup accepts --yes flag in argument parser" {
  run grep -- '--yes' bin/worktree-cleanup
  [ "$status" -eq 0 ]
}

@test "worktree-cleanup accepts -y short flag" {
  run grep -- '-y)' bin/worktree-cleanup
  [ "$status" -eq 0 ]
}

@test "worktree-cleanup accepts --force flag" {
  run grep -- '--force' bin/worktree-cleanup
  [ "$status" -eq 0 ]
}

@test "worktree-cleanup --yes flag skips main confirmation" {
  run grep 'YES' bin/worktree-cleanup
  [ "$status" -eq 0 ]
}

@test "worktree-cleanup --force implies --yes" {
  run grep 'FORCE_YES\|FORCE.*YES\|force.*yes' bin/worktree-cleanup
  [ "$status" -eq 0 ]
}
