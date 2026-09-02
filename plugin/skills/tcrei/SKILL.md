---
name: tcrei
description: Compose a paste-ready TCREI prompt (Task / Context / Rules / Iterate) for dispatching to an agent.
argument-hint: "[task, or context to build the prompt from]"
---

## Task

Turn the supplied task/context and conversation into one dispatch-ready prompt for an agent working in an environment you cannot see.

## Context

- The reader starts cold — no shared history, no visible environment. A link or a "you know the one" will not survive.
- This skill is governed by GNS-001 (observe before acting) and GNS-004 (independent premise validation). If they are not loaded (no GNS references in context), read the packaged identity at `../../docs/identity.md` relative to this `SKILL.md` inline first.
- The prompt's section anatomy, the TCREI -> four-header mapping, the observation-first rewrite table, and a worked template all live in `references/prompt-anatomy.md` relative to this `SKILL.md`. Read it before drafting; do not restate it here.
- `references/examples.md` holds excerpts of what works and the portability traps to rewrite. Read it for calibration.

## Rules

- Emit exactly one fenced block — Task, Context, Rules, Iterate — with nothing else inside the fence.
- Context carries observed facts only. Tag anything unverified `[unverified]`; assert no host, container, or directory you did not observe.
- Never hardcode branch tooling, working directory, package manager, or test runner. State the intent plus a preferred tool with a fallback, and let the agent observe and choose (GNS-001).
- If Task or Context is too thin to survive a cold start, ask one round of clarifying questions before drafting.

## Evaluate

Before emitting, the prompt ships only if all hold:

- Every Rules and Iterate line names an outcome or an observe-and-fallback — never a tool you merely assume is present.
- It is self-contained: a stranger could run it with no other context.
- Iterate ends in a proof gate (specs, lint, review criteria) that defines done (GNS-004).

## Iterate

1. Load the identity if absent, then read `references/prompt-anatomy.md`.
2. Gather raw material from the supplied task/context and the conversation; ask one round if too thin.
3. Draft the four output sections per the anatomy.
4. Run the observation-precedence rewrite over every Rules and Iterate line, using the rewrite table in the reference.
5. Check the draft against Evaluate, then emit the fenced block.
