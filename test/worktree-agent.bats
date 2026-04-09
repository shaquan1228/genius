#!/usr/bin/env bats
# Tests for bin/worktree — smart naming and --with-graphite flag
# (replaces old worktree-agent tests)

BIN="$BATS_TEST_DIRNAME/../bin/worktree"

setup() {
  TEST_REPO="$(mktemp -d)"
  git init "$TEST_REPO" --initial-branch=main >/dev/null 2>&1
  git -C "$TEST_REPO" -c user.name="test" -c user.email="test@test" -c commit.gpgsign=false commit --allow-empty -m "initial" >/dev/null 2>&1
  export HOME="$TEST_REPO"
  cd "$TEST_REPO"
}

teardown() {
  cd /
  rm -rf "$TEST_REPO"
  rm -rf "$(dirname "$TEST_REPO")/$(basename "$TEST_REPO")-worktrees" 2>/dev/null || true
}

@test "description with spaces gets sanitized and timestamped" {
  run "$BIN" "fix login bug"

  [ "$status" -eq 0 ]
  REPO_NAME="$(basename "$TEST_REPO")"
  WORKTREE_DIR="$(dirname "$TEST_REPO")/${REPO_NAME}-worktrees"
  ls "$WORKTREE_DIR" | grep -q "^fix-login-bug-"
}

@test "clean branch name is used as-is" {
  run "$BIN" my-feature

  [ "$status" -eq 0 ]
  REPO_NAME="$(basename "$TEST_REPO")"
  WORKTREE_DIR="$(dirname "$TEST_REPO")/${REPO_NAME}-worktrees"
  [ -d "$WORKTREE_DIR/my-feature" ]
}

@test "--temporal with description gets temp- prefix and sanitized name" {
  run "$BIN" --temporal "implement user auth"

  [ "$status" -eq 0 ]
  [[ "$output" == *"TEMPORAL"* ]]
  REPO_NAME="$(basename "$TEST_REPO")"
  WORKTREE_DIR="$(dirname "$TEST_REPO")/${REPO_NAME}-worktrees"
  ls "$WORKTREE_DIR" | grep -q "^temp-implement-user-auth-"
}

@test "sanitizes uppercase and special chars in description" {
  run "$BIN" "Fix UPPERCASE & special!chars"

  [ "$status" -eq 0 ]
  REPO_NAME="$(basename "$TEST_REPO")"
  WORKTREE_DIR="$(dirname "$TEST_REPO")/${REPO_NAME}-worktrees"
  ls "$WORKTREE_DIR" | grep -q "^fix-uppercase-special-chars-"
}

@test "logs creation to ~/.genius/worktree.log" {
  run "$BIN" --temporal "test logging"

  [ "$status" -eq 0 ]
  [ -f "$TEST_REPO/.genius/worktree.log" ]
  grep -q "CREATE: temp-test-logging-" "$TEST_REPO/.genius/worktree.log"
}

@test "--with-graphite flag is accepted" {
  # Just verify the flag doesn't cause an error (gt may not be installed in CI)
  run "$BIN" --temporal --with-graphite "graphite test"

  [ "$status" -eq 0 ]
}
