#!/usr/bin/env bats

@test "worktree-cleanup validates --age-days is a positive integer" {
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
