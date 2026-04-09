# genius

Portable dev toolkit. Bootstraps a new machine and injects engineering context into Claude Code and Cursor.

## Quickstart

1. Clone: `git clone git@github.com:your-handle/genius.git`
2. Run `bin/setup` within your cloned repo.
3. Set your git email (not tracked) `git config --global user.email "you@example.com"`
4. For global Cursor context, paste the printed snippet into **Cursor > Settings > Rules for AI** from within your cloned repo: `echo "@$(pwd)/docs/identity.md" | pbcopy`
5. Open a new shell after setup completes.

## Commands

| Command                    | Description                                                                |
| -------------------------- | -------------------------------------------------------------------------- |
| `setup`                | Bootstrap machine: install deps, symlink dotfiles, configure Claude/Cursor |
| `worktree <branch> [base]` | Create or checkout git worktree (smart naming, composable flags)           |
| `worktree-cleanup`         | Remove old temporal worktrees                                              |
| `dashboard`                | Show over-tinkering monitor and system status                              |
| `teardown`             | Safely remove genius configuration                                        |
