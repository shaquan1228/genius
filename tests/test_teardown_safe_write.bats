#!/usr/bin/env bats

@test "teardown uses mktemp for safe temporary file creation" {
  run grep 'mktemp' bin/teardown
  [ "$status" -eq 0 ]
}

@test "teardown creates timestamped backup before modifying files" {
  run grep '\.bak\.' bin/teardown
  [ "$status" -eq 0 ]
}

@test "teardown has size guard to prevent empty file overwrite" {
  run grep '\-s "\$' bin/teardown
  [ "$status" -eq 0 ]
}

@test "teardown remove_line_from_file does not use predictable .tmp extension" {
  run grep '${file}\.tmp\|"${file}\.tmp"' bin/teardown
  [ "$status" -ne 0 ]
}
