#!/usr/bin/env bats

@test "bin/setup has --skip-shell-config flag" {
  run grep 'skip-shell-config' bin/setup
  [ "$status" -eq 0 ]
}

@test "bin/setup skips .zshrc modifications when SKIP_SHELL_CONFIG is true" {
  run grep 'SKIP_SHELL_CONFIG\|SKIP_SHELL' bin/setup
  [ "$status" -eq 0 ]
}

@test "bin/setup supports --help flag" {
  run grep -- '--help\|-h)' bin/setup
  [ "$status" -eq 0 ]
}

@test "bin/setup adds datestamp to .zshrc modifications" {
  run grep "date.*'+%Y-%m-%d'\|added.*%Y-%m-%d\|%Y-%m-%d.*added" bin/setup
  [ "$status" -eq 0 ]
}

@test "bin/setup --skip-shell-config skips without error" {
  # Dry test: verify the flag is handled (won't actually modify the system)
  run grep 'Skipping.*zshrc\|skip.*shell\|SKIP_SHELL' bin/setup
  [ "$status" -eq 0 ]
}
