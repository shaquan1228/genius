# quanbot

Portable dev toolkit. Bootstraps a new machine and injects engineering context into Claude Code and Cursor.

## Quickstart

```bash
git clone git@github.com:your-handle/quanbot.git ~/Desktop/quanbot
~/Desktop/quanbot/bin/setup
```

That's it. Open a new shell after setup completes.

## What bin/setup does

1. Installs Homebrew (if missing)
2. Installs dependencies from `Brewfile` (gh, gt, asdf, neovim, etc.)
3. Symlinks `dotfiles/` into `~` (gitconfig, zshrc.local, claude permissions)
4. Writes `~/.claude/CLAUDE.md` — auto-loaded by Claude Code every session
5. Symlinks `commands/` into `~/.claude/commands/` — slash commands for Claude Code
6. Writes `.cursor/rules/quanbot.mdc` — auto-loaded by Cursor when workspace is open

## After setup

Set your git email (not tracked — work-specific):
```bash
git config --global user.email "you@example.com"
```

For Cursor to load context in all projects (not just this workspace), paste the printed snippet into **Cursor > Settings > Rules for AI**.

## Worktree helper

```bash
# from any git repo:
quanbot/bin/worktree <branch>              # new branch from HEAD
quanbot/bin/worktree <branch> <base>       # new branch from <base>
quanbot/bin/worktree --checkout <branch>   # check out existing branch
```

Worktrees are created at `~/Desktop/<repo-name>-worktrees/<branch>`.

## Files

- `identity.md` — engineering identity and principles
- `rules.md` — language-agnostic coding, design, and testing rules
- `workflow.md` — OODA-based task execution process
- `prompts/` — role overlays: planner, implementer, reviewer, stack
- `commands/` — Claude Code slash commands
- `dotfiles/` — portable config: gitconfig, zshrc.local, claude permissions
- `Brewfile` — dependency declarations
- `bin/setup` — full bootstrapper
- `bin/link` — symlink helper used by setup
- `bin/worktree` — git worktree creation utility
