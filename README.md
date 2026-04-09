# genius

LLMs are stateless. Every session starts cold — no memory of the habits you taught last time, no consistent instincts, no shared reasoning framework. Genius fixes that by injecting a structured engineering identity into Claude Code and Cursor on every session, without re-prompting.

## Why genius

Research on semi-formal structured reasoning ([arxiv 2603.01896](https://arxiv.org/html/2603.01896v1)) shows that structured templates outperform standard unstructured prompting by 8–11 percentage points on code tasks. The core mechanism: explicit premises, constraints, and observation requirements prevent unsupported claims and force thorough investigation. Genius's proof system is that structure, applied to how you work.

**Observed in practice:**

Same model, same repo, same one-line prompt, bypass permissions, both left to run unattended. Without identity: Claude read the repo plainly, picked up a `tutorial-commit` instruction from a CLAUDE.md file, and executed it without questioning whether that was the right move. With identity: Claude stayed in step 2 deliberating while no-identity was already on step 5, ran independent validation before moving forward, and didn't trust its own intermediate outputs. Result: 34 min / ~$13 / ~100 fewer lines of code vs 13 min / ~$8 / more code with things to address.

## How it works

`bin/setup` writes a single file — `~/.claude/CLAUDE.md` — that Claude Code loads globally on every session. That file references `docs/identity.md`: a set of operating principles derived from a proof system that defines how the model should observe, decide, and act. Cursor gets the same context via `.cursor/rules/`. No plugins. No API wrappers. Just ambient context that persists across sessions and tools.

## Quickstart

1. Clone: `git clone git@github.com:shaquan1228/genius.git`
2. Run `bin/setup` from within the cloned repo
3. Open a new shell after setup completes
4. For Cursor: paste the printed snippet into **Cursor > Settings > Rules for AI**

## Commands

| Command                    | Description                                                                |
| -------------------------- | -------------------------------------------------------------------------- |
| `setup`                    | Bootstrap machine: install deps, symlink dotfiles, configure Claude/Cursor |
| `worktree <branch> [base]` | Create or checkout git worktree (smart naming, composable flags)           |
| `worktree-cleanup`         | Remove old temporal worktrees                                              |
| `dashboard`                | Show over-tinkering monitor and system status                              |
| `teardown`                 | Safely remove genius configuration                                         |

## Dev toolkit

`bin/` includes a small toolkit that complements the identity injection: opinionated worktree management (`worktree`, `worktree-cleanup`) built on top of Graphite, a tmux workspace initializer, and `compress-memory` for summarizing Claude's memory files when context gets heavy. None of it is required — the core value is the identity injection via `bin/setup`.

## Dashboard (experimental)

`dashboard/` is a Go TUI that surfaces git state, worktrees, tmux sessions, and recent logs. It was the first thing built and may be overtinkering — the identity injection turned out to be the real leverage. Treat it as optional.

## Framework

The identity is grounded in a proof system — five lemmas that compose into a decision framework for how to reason and act under uncertainty. See [`docs/identity.md`](docs/identity.md) for the full structure, and [`docs/proofs/`](docs/proofs/) for the derivations.
