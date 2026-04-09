# genius

LLMs are stateless. Every session starts cold — no memory of the habits you taught last time, no consistent instincts, no shared reasoning framework. Genius fixes that by injecting a structured engineering identity into Claude Code and Cursor on every session, without re-prompting.

## Why genius

Research on semi-formal structured reasoning ([arxiv 2603.01896](https://arxiv.org/html/2603.01896v1)) shows that structured templates outperform standard unstructured prompting by 8–11 percentage points on code tasks. The core mechanism: explicit premises, constraints, and observation requirements prevent unsupported claims and force thorough investigation. Genius's proof system is that structure, applied to how you work.

**Observed in practice:**

<!-- INSERT: describe what raw Claude did on your vague prompt (no identity) -->
<!-- INSERT: describe what genius-injected Claude did on the same prompt -->
<!-- INSERT: screenshots if available -->

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

## Framework

The identity is grounded in a proof system — five lemmas that compose into a decision framework for how to reason and act under uncertainty. See [`docs/identity.md`](docs/identity.md) for the full structure, and [`docs/proofs/`](docs/proofs/) for the derivations.
