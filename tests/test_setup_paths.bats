#!/usr/bin/env bats

@test "bin/setup references the correct docs/dev/STOP-TINKERING.md path" {
  run grep 'docs/dev/STOP-TINKERING' bin/setup
  [ "$status" -eq 0 ]
}

@test "bin/setup does not reference the wrong STOP-TINKERING location" {
  run grep -E 'docs/STOP-TINKERING|docs/dreams/STOP-TINKERING' bin/setup
  [ "$status" -ne 0 ]
}

@test "bin/dashboard and bin/setup agree on STOP-TINKERING path" {
  dashboard_path=$(grep 'STOP-TINKERING' bin/dashboard | grep -oE 'docs/[^ ]+' | head -1)
  setup_path=$(grep 'STOP-TINKERING' bin/setup | grep -oE 'docs/[^ ]+' | head -1)
  [ "$dashboard_path" = "$setup_path" ]
}
