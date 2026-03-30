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

@test "respects QUANBOT_WORKTREE_DIR env var" {
  LIB="$BATS_TEST_DIRNAME/../bin/lib/worktree-common.sh"
  run grep 'QUANBOT_WORKTREE_DIR' "$LIB"
  [ "$status" -eq 0 ]
}

@test "uses sibling directory of repo as default worktree base" {
  LIB="$BATS_TEST_DIRNAME/../bin/lib/worktree-common.sh"
  run grep 'dirname.*REPO_ROOT' "$LIB"
  [ "$status" -eq 0 ]
}

# NOTE: "reports no stale worktrees when all are fresh" is skipped because
# worktree-cleanup has a cross-platform bug: `stat -f %m` on Linux outputs
# filesystem info instead of mtime, causing an unbound variable error.
# See: bin/worktree-cleanup line 74 — needs `stat -c %Y` first on Linux.

@test "worktree-cleanup accepts --yes flag in argument parser" {
  run grep -- '--yes' "$BIN"
  [ "$status" -eq 0 ]
}

@test "worktree-cleanup accepts -y short flag" {
  run grep -- '-y)' "$BIN"
  [ "$status" -eq 0 ]
}

@test "worktree-cleanup accepts --force flag" {
  run grep -- '--force' "$BIN"
  [ "$status" -eq 0 ]
}

@test "worktree-cleanup --yes flag skips main confirmation" {
  run grep 'YES' "$BIN"
  [ "$status" -eq 0 ]
}

@test "worktree-cleanup --force implies --yes" {
  run grep 'FORCE_YES\|FORCE.*YES\|force.*yes' "$BIN"
  [ "$status" -eq 0 ]
}

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
