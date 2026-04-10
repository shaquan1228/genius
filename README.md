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
bin/setup
```

For Cursor: paste the printed snippet into **Cursor > Settings > Rules for AI**.

## How it works

`bin/setup` writes `~/.claude/CLAUDE.md` — loaded by Claude Code on every session — pointing to `docs/identity.md`: operating principles that define how the model should observe, decide, and act. Cursor gets the same via `.cursor/rules/`. No plugins, no API wrappers.

`docs/identity.md` is the only file you need to understand or customize.

## Commands

| Command | Description |
| ------- | ----------- |
| `setup` | Inject genius identity into Claude Code and Cursor |
| `teardown [--confirm]` | Remove the injection (dry-run by default) |
