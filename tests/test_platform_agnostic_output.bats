#!/usr/bin/env bats

@test "bin/dashboard shows universal tmux Ctrl+b keybinding" {
  run grep 'Ctrl+b' bin/dashboard
  [ "$status" -eq 0 ]
}

@test "bin/setup has platform-conditional next steps using uname" {
  run grep 'uname' bin/setup
  [ "$status" -eq 0 ]
}

@test "bin/setup Linux path includes source .zshrc instruction" {
  run grep 'source.*\.zshrc\|source ~/.zshrc' bin/setup
  [ "$status" -eq 0 ]
}

@test "bin/setup macOS path still references iTerm2" {
  run grep 'iTerm2\|iterm' bin/setup
  [ "$status" -eq 0 ]
}
