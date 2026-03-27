#!/usr/bin/env bats
# Validate all shell scripts parse correctly and have proper headers

BIN_DIR="$BATS_TEST_DIRNAME/../bin"

@test "bin/setup has bash shebang and set -euo pipefail" {
  head -20 "$BIN_DIR/setup" | grep -q '#!/usr/bin/env bash'
  head -20 "$BIN_DIR/setup" | grep -q 'set -euo pipefail'
}

@test "bin/teardown has bash shebang and set -euo pipefail" {
  head -20 "$BIN_DIR/teardown" | grep -q '#!/usr/bin/env bash'
  head -20 "$BIN_DIR/teardown" | grep -q 'set -euo pipefail'
}

@test "bin/link has bash shebang and set -euo pipefail" {
  head -20 "$BIN_DIR/link" | grep -q '#!/usr/bin/env bash'
  head -20 "$BIN_DIR/link" | grep -q 'set -euo pipefail'
}

@test "bin/worktree has bash shebang and set -euo pipefail" {
  head -20 "$BIN_DIR/worktree" | grep -q '#!/usr/bin/env bash'
  head -20 "$BIN_DIR/worktree" | grep -q 'set -euo pipefail'
}

@test "bin/worktree-agent has bash shebang and set -euo pipefail" {
  head -20 "$BIN_DIR/worktree-agent" | grep -q '#!/usr/bin/env bash'
  head -20 "$BIN_DIR/worktree-agent" | grep -q 'set -euo pipefail'
}

@test "bin/worktree-cleanup has bash shebang and set -euo pipefail" {
  head -20 "$BIN_DIR/worktree-cleanup" | grep -q '#!/usr/bin/env bash'
  head -20 "$BIN_DIR/worktree-cleanup" | grep -q 'set -euo pipefail'
}

@test "bin/tmux-init-session has bash shebang" {
  head -5 "$BIN_DIR/tmux-init-session" | grep -q '#!/usr/bin/env bash'
}

@test "bin/dashboard has bash shebang" {
  head -5 "$BIN_DIR/dashboard" | grep -q '#!/usr/bin/env bash'
}

@test "all bin/ scripts are executable" {
  for script in setup teardown link worktree worktree-agent worktree-cleanup tmux-init-session dashboard; do
    [ -x "$BIN_DIR/$script" ]
  done
}
