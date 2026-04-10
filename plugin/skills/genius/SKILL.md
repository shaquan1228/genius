---
description: Toggle or load the genius engineering identity. Use when you want to turn structured reasoning on or off, or explicitly load the framework.
argument-hint: "[on|off]"
---

If $ARGUMENTS is "off":
  1. Run `claude plugin disable genius` to disable for future sessions.
  2. For the remainder of this session, stop applying the genius engineering identity. Do not observe-before-act, do not reference the proofs, and do not structure responses with TL;DR / Observed / Decided / Next / Blockers. Operate as default Claude.
  3. Confirm genius is off.

If $ARGUMENTS is "on", or no argument is provided:
  1. Run `claude plugin enable genius` to enable for future sessions.
  2. Read `$CLAUDE_PLUGIN_ROOT/docs/identity.md`, internalize the operating principles, and briefly summarize the five proofs (GNS-001 through GNS-005).
  3. Confirm you are now reasoning within the genius framework.
