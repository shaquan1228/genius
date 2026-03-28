#!/usr/bin/env bats
# Tests for bin/worktree — create git worktrees

BIN="$BATS_TEST_DIRNAME/../bin/worktree"

# Helper to create git commits without signing (CI/sandboxed environments)
test_commit() {
  git -C "$1" -c user.name="test" -c user.email="test@test" -c commit.gpgsign=false commit "$@" >/dev/null 2>&1
}

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

@test "creates worktree with new branch from HEAD" {
  run "$BIN" test-feature

  [ "$status" -eq 0 ]
  [[ "$output" == *"Worktree ready"* ]]
  EXPECTED="$(dirname "$TEST_REPO")/$(basename "$TEST_REPO")-worktrees/test-feature"
  [ -d "$EXPECTED" ]
}

@test "--temporal flag prefixes branch with temp-" {
  run "$BIN" --temporal my-task

  [ "$status" -eq 0 ]
  [[ "$output" == *"TEMPORAL"* ]]
  EXPECTED="$(dirname "$TEST_REPO")/$(basename "$TEST_REPO")-worktrees/temp-my-task"
  [ -d "$EXPECTED" ]
}

@test "--permanent flag prefixes branch with keep-" {
  run "$BIN" --permanent my-task

  [ "$status" -eq 0 ]
  [[ "$output" == *"PERMANENT"* ]]
  EXPECTED="$(dirname "$TEST_REPO")/$(basename "$TEST_REPO")-worktrees/keep-my-task"
  [ -d "$EXPECTED" ]
}

@test "is idempotent — skips if worktree already exists" {
  run "$BIN" dupe-branch
  [ "$status" -eq 0 ]

  run "$BIN" dupe-branch
  [ "$status" -eq 0 ]
  [[ "$output" == *"already exists"* ]]
}

@test "logs operations to ~/.quanbot/worktree.log" {
  run "$BIN" logged-branch

  [ "$status" -eq 0 ]
  [ -f "$TEST_REPO/.quanbot/worktree.log" ]
  grep -q "CREATE: logged-branch" "$TEST_REPO/.quanbot/worktree.log"
}

@test "creates worktree from a specific base branch" {
  git -C "$TEST_REPO" checkout -b develop >/dev/null 2>&1
  git -C "$TEST_REPO" -c user.name="test" -c user.email="test@test" -c commit.gpgsign=false commit --allow-empty -m "develop commit" >/dev/null 2>&1
  git -C "$TEST_REPO" checkout main >/dev/null 2>&1

  run "$BIN" from-develop develop

  [ "$status" -eq 0 ]
  [[ "$output" == *"Worktree ready"* ]]
}

@test "respects QUANBOT_WORKTREE_DIR env var" {
  run grep 'QUANBOT_WORKTREE_DIR' "$BIN"
  [ "$status" -eq 0 ]
}

@test "uses sibling directory of repo as default worktree base" {
  run grep 'dirname.*REPO_ROOT' "$BIN"
  [ "$status" -eq 0 ]
}

@test "worktrees go to sibling of repo, not ~/Desktop" {
  CUSTOM_BASE="$(mktemp -d)"
  QUANBOT_WORKTREE_DIR="$CUSTOM_BASE" run "$BIN" override-branch

  [ "$status" -eq 0 ]
  [ -d "$CUSTOM_BASE/$(basename "$TEST_REPO")-worktrees/override-branch" ]
  rm -rf "$CUSTOM_BASE"
}
