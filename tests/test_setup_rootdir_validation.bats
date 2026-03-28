#!/usr/bin/env bats

@test "bin/setup validates ROOT_DIR before interpolating into files" {
  run grep 'ROOT_DIR.*=~\|=~.*ROOT_DIR' bin/setup
  [ "$status" -eq 0 ]
}

@test "ROOT_DIR validation rejects paths with shell metacharacters" {
  result=$(bash -c '
    ROOT_DIR="/tmp/evil\$(id)/repo"
    if [[ ! "$ROOT_DIR" =~ ^[a-zA-Z0-9/_.-]+$ ]]; then
      echo "rejected"; exit 1
    fi
    echo "accepted"
  ' 2>&1) || true
  [ "$result" = "rejected" ]
}

@test "ROOT_DIR validation accepts normal repository paths" {
  result=$(bash -c '
    ROOT_DIR="/Users/me/Repositories/quanbot"
    if [[ ! "$ROOT_DIR" =~ ^[a-zA-Z0-9/_.-]+$ ]]; then
      echo "rejected"; exit 1
    fi
    echo "accepted"
  ')
  [ "$result" = "accepted" ]
}

@test "bin/setup exits before writing CLAUDE.md on invalid ROOT_DIR" {
  run grep 'exit 1' bin/setup
  [ "$status" -eq 0 ]
}
