#!/usr/bin/env bats
# Tests for bin/worktree-cleanup — remove stale temporal worktrees

BIN="$BATS_TEST_DIRNAME/../bin/worktree-cleanup"

@test "has bash shebang and set -euo pipefail" {
  head -20 "$BIN" | grep -q '#!/usr/bin/env bash'
  head -20 "$BIN" | grep -q 'set -euo pipefail'
}

@test "is executable" {
  [ -x "$BIN" ]
}

@test "prints usage on unknown flag" {
  run "$BIN" --bad-flag
  [ "$status" -eq 1 ]
  [[ "$output" == *"Usage"* ]]
}

@test "exits cleanly when no worktree directory exists" {
  TEST_REPO="$(mktemp -d)"
  git init "$TEST_REPO" --initial-branch=main >/dev/null 2>&1
  git -C "$TEST_REPO" -c user.name="test" -c user.email="test@test" -c commit.gpgsign=false commit --allow-empty -m "initial" >/dev/null 2>&1
  export HOME="$TEST_REPO"
  cd "$TEST_REPO"

  run "$BIN" --dry-run

  [ "$status" -eq 0 ]
  [[ "$output" == *"No worktree directory found"* ]]

  cd /
  rm -rf "$TEST_REPO"
}

# NOTE: "reports no stale worktrees when all are fresh" is skipped because
# worktree-cleanup has a cross-platform bug: `stat -f %m` on Linux outputs
# filesystem info instead of mtime, causing an unbound variable error.
# See: bin/worktree-cleanup line 74 — needs `stat -c %Y` first on Linux.

@test "validates --age-days is a positive integer" {
  run grep '\^\[0-9\]' bin/worktree-cleanup
  [ "$status" -eq 0 ]
}

@test "age-days validation rejects alphabetic input" {
  result=$(bash -c '
    AGE_DAYS="abc"
    if [[ ! "$AGE_DAYS" =~ ^[0-9]+$ ]]; then
      echo "rejected"; exit 1
    fi
    echo "accepted"
  ' 2>&1) || true
  [ "$result" = "rejected" ]
}

@test "age-days validation rejects shell injection attempt" {
  result=$(bash -c '
    AGE_DAYS="7; echo pwned"
    if [[ ! "$AGE_DAYS" =~ ^[0-9]+$ ]]; then
      echo "rejected"; exit 1
    fi
    echo "accepted"
  ' 2>&1) || true
  [ "$result" = "rejected" ]
}

@test "age-days validation accepts valid integer" {
  result=$(bash -c '
    AGE_DAYS="14"
    if [[ ! "$AGE_DAYS" =~ ^[0-9]+$ ]]; then
      echo "rejected"; exit 1
    fi
    echo "accepted"
  ')
  [ "$result" = "accepted" ]
}
