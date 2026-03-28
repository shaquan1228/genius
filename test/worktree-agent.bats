#!/usr/bin/env bats
# Tests for bin/worktree-agent — create temporal worktrees for agent tasks

BIN="$BATS_TEST_DIRNAME/../bin/worktree-agent"

setup() {
  TEST_REPO="$(mktemp -d)"
  git init "$TEST_REPO" --initial-branch=main >/dev/null 2>&1
  git -C "$TEST_REPO" -c user.name="test" -c user.email="test@test" -c commit.gpgsign=false commit --allow-empty -m "initial" >/dev/null 2>&1
  export HOME="$TEST_REPO"
  mkdir -p "$TEST_REPO/Desktop"
  cd "$TEST_REPO"
}

teardown() {
  cd /
  rm -rf "$TEST_REPO"
}

@test "has bash shebang and set -euo pipefail" {
  head -20 "$BIN" | grep -q '#!/usr/bin/env bash'
  head -20 "$BIN" | grep -q 'set -euo pipefail'
}

@test "is executable" {
  [ -x "$BIN" ]
}

@test "fails with no arguments" {
  run "$BIN"
  [ "$status" -ne 0 ]
}

@test "creates temporal worktree with agent- prefix" {
  run "$BIN" "fix login bug"

  [ "$status" -eq 0 ]
  [[ "$output" == *"Agent worktree ready"* ]]
  [[ "$output" == *"TEMPORAL"* ]]

  # Branch should exist with agent- prefix and sanitized name
  REPO_NAME="$(basename "$TEST_REPO")"
  WORKTREE_DIR="$TEST_REPO/Desktop/${REPO_NAME}-worktrees"
  ls "$WORKTREE_DIR" | grep -q "^agent-fix-login-bug-"
}

@test "sanitizes task description in branch name" {
  run "$BIN" "Fix UPPERCASE & special!chars"

  [ "$status" -eq 0 ]
  REPO_NAME="$(basename "$TEST_REPO")"
  WORKTREE_DIR="$TEST_REPO/Desktop/${REPO_NAME}-worktrees"
  # Should be lowercased, special chars replaced with dashes
  ls "$WORKTREE_DIR" | grep -q "^agent-fix-uppercase-special-chars-"
}

@test "logs creation to ~/.quanbot/worktree.log" {
  run "$BIN" "test logging"

  [ "$status" -eq 0 ]
  [ -f "$TEST_REPO/.quanbot/worktree.log" ]
  grep -q "CREATE: agent-test-logging-" "$TEST_REPO/.quanbot/worktree.log"
}

@test "respects QUANBOT_WORKTREE_DIR env var" {
  run grep 'QUANBOT_WORKTREE_DIR' "$BIN"
  [ "$status" -eq 0 ]
}
