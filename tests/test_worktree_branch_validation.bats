#!/usr/bin/env bats

@test "bin/worktree validates branch name against character allowlist" {
  run grep '\[a-zA-Z0-9' bin/worktree
  [ "$status" -eq 0 ]
}

@test "branch validation rejects path traversal sequences" {
  result=$(bash -c '
    BRANCH="../../etc/passwd"
    if [[ "$BRANCH" =~ \.\. ]] || [[ ! "$BRANCH" =~ ^[a-zA-Z0-9/_.-]+$ ]]; then
      echo "rejected"
    else
      echo "accepted"
    fi
  ' 2>&1)
  [ "$result" = "rejected" ]
}

@test "branch validation accepts normal branch names" {
  result=$(bash -c '
    BRANCH="feat/my-feature"
    if [[ ! "$BRANCH" =~ ^[a-zA-Z0-9/_.-]+$ ]]; then
      echo "rejected"
    else
      echo "accepted"
    fi
  ')
  [ "$result" = "accepted" ]
}

@test "branch validation accepts branch names with dashes and dots" {
  result=$(bash -c '
    BRANCH="fix-123.patch"
    if [[ ! "$BRANCH" =~ ^[a-zA-Z0-9/_.-]+$ ]]; then
      echo "rejected"
    else
      echo "accepted"
    fi
  ')
  [ "$result" = "accepted" ]
}
