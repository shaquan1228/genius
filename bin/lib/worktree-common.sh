#!/usr/bin/env bash
# bin/lib/worktree-common.sh — shared worktree infrastructure
#
# Source this file from worktree scripts:
#   source "$(dirname "${BASH_SOURCE[0]}")/lib/worktree-common.sh"

REPO_ROOT="$(git rev-parse --show-toplevel)"
REPO_NAME="$(basename "$REPO_ROOT")"

# Default: sibling directory of the repo (e.g. /Repositories/quanbot → /Repositories/quanbot-worktrees)
# Override: set QUANBOT_WORKTREE_DIR to use a different base
WORKTREE_BASE="${QUANBOT_WORKTREE_DIR:-$(dirname "$REPO_ROOT")}/${REPO_NAME}-worktrees"
LOG_FILE="$HOME/.quanbot/worktree.log"

wt_log() {
  mkdir -p "$(dirname "$LOG_FILE")"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}
