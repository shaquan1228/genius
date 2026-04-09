# genius

Injects a structured engineering identity into Claude Code and Cursor — same reasoning instincts, every session, without re-prompting.

## Why

Without identity: Claude reads what's in front of it and executes the path of least resistance. With identity: it observes before acting, validates assumptions, and flags irreversible moves first.

**Tested:** same model, same repo, same one-line prompt, bypass permissions, both unattended.

| | no identity | genius |
|---|---|---|
| Time | ~13 min | ~34 min |
| Cost | ~$8 | ~$13 |
| Lines of code | more | ~100 fewer |
| Behavior | read repo, executed a stale CLAUDE.md instruction | deliberated, stayed in step 2 while no-identity was on step 5, ran independent validation |

Backed by research: semi-formal structured reasoning outperforms standard prompting by 8–11pp on code tasks ([arxiv 2603.01896](https://arxiv.org/html/2603.01896v1)).

## Quickstart

```sh
git clone git@github.com:shaquan1228/genius.git
cd genius
bin/setup --no-profile  # wires Claude Code + Cursor, leaves shell config alone
```

For Cursor: paste the printed snippet into **Cursor > Settings > Rules for AI**.

## Commands

| Command | Description |
| ------- | ----------- |
| `setup [--no-profile]` | Bootstrap machine: install deps, configure Claude/Cursor |
| `worktree <branch> [base]` | Create or checkout git worktree (smart naming) |
| `worktree-cleanup` | Remove old temporal worktrees |
| `dashboard` | System status TUI |
| `teardown` | Safely remove genius configuration |

## How it works

`bin/setup` writes `~/.claude/CLAUDE.md` — loaded by Claude Code on every session — pointing to `docs/identity.md`: a proof system that defines how the model should observe, decide, and act. Cursor gets the same via `.cursor/rules/`. No plugins, no API wrappers.

## Framework

Five proofs compose into a decision framework. See [`docs/identity.md`](docs/identity.md) and [`docs/proofs/`](docs/proofs/).

## Extras

`bin/` includes worktree management built on Graphite, a tmux workspace initializer, and `compress-memory` for summarizing Claude's memory files. Optional — the core value is the identity injection.

`dashboard/` is a Go TUI that was the first thing built. Potentially overtinkered. Treat as experimental.
