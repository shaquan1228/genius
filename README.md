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

**From the marketplace (recommended):**

```sh
/plugin marketplace add shaquan1228/genius
/plugin install genius@genius
```

Start a new session — the `SessionStart` hook loads the identity automatically.

**Manually:**

```sh
git clone git@github.com:shaquan1228/genius.git
cd genius
bin/setup
```

For Cursor: paste the printed snippet into **Cursor > Settings > Rules for AI**.

## How it works

Once installed, a `SessionStart` hook automatically injects `docs/identity.md` into every Claude Code session — no commands needed. The identity defines how the model should observe, decide, and act. Cursor gets the same context via `.cursor/rules/`.

`docs/identity.md` is the only file you need to understand or customize.

Run `/genius:think` at any point to have Claude explicitly load and summarize the reasoning framework.

## Commands

| Command | Description |
| ------- | ----------- |
| `/genius:think` | Load and summarize the genius reasoning framework |
| `setup` | Manually inject identity into Claude Code and Cursor |
| `teardown [--confirm]` | Remove the injection (dry-run by default) |
