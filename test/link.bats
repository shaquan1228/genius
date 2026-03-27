#!/usr/bin/env bats
# Tests for bin/link — safe symlink helper

setup() {
  TEST_DIR="$(mktemp -d)"
  LINK_CMD="$BATS_TEST_DIRNAME/../bin/link"
}

teardown() {
  rm -rf "$TEST_DIR"
}

@test "creates symlink from source to target" {
  echo "hello" > "$TEST_DIR/source.txt"

  run "$LINK_CMD" "$TEST_DIR/source.txt" "$TEST_DIR/target.txt"

  [ "$status" -eq 0 ]
  [ -L "$TEST_DIR/target.txt" ]
  [ "$(readlink "$TEST_DIR/target.txt")" = "$TEST_DIR/source.txt" ]
}

@test "is idempotent — skips if symlink already correct" {
  echo "hello" > "$TEST_DIR/source.txt"
  ln -s "$TEST_DIR/source.txt" "$TEST_DIR/target.txt"

  run "$LINK_CMD" "$TEST_DIR/source.txt" "$TEST_DIR/target.txt"

  [ "$status" -eq 0 ]
  [[ "$output" == *"already correct"* ]]
}

@test "backs up existing plain file before replacing" {
  echo "hello" > "$TEST_DIR/source.txt"
  echo "old content" > "$TEST_DIR/target.txt"

  run "$LINK_CMD" "$TEST_DIR/source.txt" "$TEST_DIR/target.txt"

  [ "$status" -eq 0 ]
  [ -L "$TEST_DIR/target.txt" ]
  [ -f "$TEST_DIR/target.txt.bak" ]
  [ "$(cat "$TEST_DIR/target.txt.bak")" = "old content" ]
}

@test "creates parent directories for target" {
  echo "hello" > "$TEST_DIR/source.txt"

  run "$LINK_CMD" "$TEST_DIR/source.txt" "$TEST_DIR/nested/dir/target.txt"

  [ "$status" -eq 0 ]
  [ -L "$TEST_DIR/nested/dir/target.txt" ]
}

@test "replaces symlink pointing to wrong source" {
  echo "new" > "$TEST_DIR/new-source.txt"
  echo "old" > "$TEST_DIR/old-source.txt"
  ln -s "$TEST_DIR/old-source.txt" "$TEST_DIR/target.txt"

  run "$LINK_CMD" "$TEST_DIR/new-source.txt" "$TEST_DIR/target.txt"

  [ "$status" -eq 0 ]
  [ "$(readlink "$TEST_DIR/target.txt")" = "$TEST_DIR/new-source.txt" ]
}

@test "fails when no arguments provided" {
  run "$LINK_CMD"

  [ "$status" -ne 0 ]
}

@test "fails when only one argument provided" {
  run "$LINK_CMD" "$TEST_DIR/source.txt"

  [ "$status" -ne 0 ]
}
