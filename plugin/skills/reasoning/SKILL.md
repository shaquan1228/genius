---
name: reasoning
description: Load the Genius engineering identity and work on a task in Claude Code or Codex. Pass a task description to apply structured reasoning immediately.
argument-hint: "[task description]"
---

If the invocation asks to turn Genius "off":
  1. For the remainder of this session, stop applying the genius engineering identity. Do not observe-before-act, do not reference the proofs, and do not structure responses with TL;DR / Observed / Decided / Next / Blockers. Operate as the default coding agent.
  2. Confirm genius is off for this session.

Otherwise:
  1. Read the packaged identity at `../../docs/identity.md` relative to this `SKILL.md`. In Claude Code, this is `$CLAUDE_PLUGIN_ROOT/docs/identity.md`.
  2. Internalize the operating principles without a setup announcement.
  3. Immediately proceed to work on the task described in the invocation, applying the Genius identity from the start.
