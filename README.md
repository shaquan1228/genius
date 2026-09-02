# genius

Injects a structured engineering identity into Claude Code, Codex, and Cursor — same reasoning instincts across coding agents.

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

Then start a new Claude Code session and invoke `/genius:reasoning` to load the identity.

**From Codex:**

```sh
codex plugin marketplace add shaquan1228/genius
codex plugin add genius@genius
```

Start a new Codex thread, then invoke `$reasoning` or describe the Genius reasoning framework in your prompt. Codex uses the shared skill package and does not automatically inject the identity into every session.

**Manually:**

```sh
git clone git@github.com:shaquan1228/genius.git
cd genius
bin/setup
```

For Cursor: paste the printed snippet into **Cursor > Settings > Rules for AI**.

## How it works

Claude Code and Codex use the same packaged reasoning skill and the identity at `plugin/docs/identity.md`. The identity defines how the model should observe, decide, and act. Cursor gets the same context via `.cursor/rules/`. Codex activates the skill when it matches a request or when you invoke `$reasoning`; `bin/setup` references the same packaged identity for persistent Claude Code and Cursor injection.

`plugin/docs/identity.md` is the identity file consumed by the packaged skill and setup script.

Run `/genius:reasoning` in Claude Code or `$reasoning` in Codex to load and summarize the reasoning framework. Use the corresponding `off` argument to stop applying it for the current session.

## Commands

| Command | Description |
| ------- | ----------- |
| `/genius:reasoning` | Load the genius reasoning framework in Claude Code |
| `$reasoning` | Load the genius reasoning framework in Codex |
| `... on` | Load Genius for the current session |
| `... off` | Stop applying Genius for the current session |
| `bin/setup` | Manually inject identity into Claude Code and Cursor |
| `bin/teardown [--confirm]` | Remove the injection (dry-run by default) |
