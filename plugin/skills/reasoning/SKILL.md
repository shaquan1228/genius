---
description: Toggle the genius engineering identity, or apply it inline to a task. Use "on"/"off" to enable/disable globally, or pass a task description to load the framework and immediately work on the task.
argument-hint: "[on|off|task description]"
---

If $ARGUMENTS is "off":
  1. Run `claude plugin disable genius` to disable for future sessions.
  2. For the remainder of this session, stop applying the genius engineering identity. Do not observe-before-act, do not reference the proofs, and do not structure responses with TL;DR / Observed / Decided / Next / Blockers. Operate as default Claude.
  3. Confirm genius is off.

If $ARGUMENTS is "on", or no argument is provided:
  1. Run `claude plugin enable genius` to enable for future sessions.
  2. Read `$CLAUDE_PLUGIN_ROOT/docs/identity.md`, internalize the operating principles, and briefly summarize the five proofs (GNS-001 through GNS-005).
  3. Confirm you are now reasoning within the genius framework.

If $ARGUMENTS is anything else (a task description):
  1. Read `$CLAUDE_PLUGIN_ROOT/docs/identity.md` and internalize the operating principles. Do not summarize or announce this step.
  2. Immediately proceed to work on the task described in $ARGUMENTS, applying the genius identity from the start.
