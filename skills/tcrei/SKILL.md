---
name: tcrei
description: Compose a paste-ready TCREI prompt (Task / Context / Rules / Iterate) for dispatching to an agent. Use when handing work to a subagent or another session. Triggers on "write a prompt for", "dispatch this", "tcrei".
argument-hint: "[task, or context to build the prompt from]"
---

## Task

Turn the supplied task, context, and conversation into one prompt. The prompt must work for an agent in an environment you cannot see.

## Context

- The reader starts cold. It has no shared history and no visible environment. A link or abstract signpost will not survive.
- GNS-001 (observe before acting) and GNS-004 (independent premise validation) govern this skill.
- If GNS-001..006 are not in context, read `../../docs/identity.md` relative to this file. In Claude Code, this is `$CLAUDE_PLUGIN_ROOT/docs/identity.md`. Load it inline. Do not prompt the user.
- `references/prompt-anatomy.md` holds the section anatomy, the TCREI mapping, the rewrite table, and a template. Read it before you draft. Do not restate it here.
- `references/examples.md` holds excerpts that work and portability traps to rewrite. Read it for calibration.

## Rules

- Emit exactly one formatted block. It contains Task, Context, Rules, and Iterate. Put nothing else inside the fence.
- Put only observed facts in Context. Tag unverified facts `[unverified]`.
- Do not assert a host, container, or directory you did not observe.
- Do not hardcode branch tooling, working directory, package manager, or test runner. State the intent. Name a preferred tool with a fallback. Let the agent observe and choose (GNS-001).
- If Task or Context is too thin for a cold start, ask one round of clarifying questions before you draft.

## Evaluate

The prompt ships only if all of these hold:

- Every Rules and Iterate line names an outcome or an observe-and-fallback. None names a tool you only assume is present.
- The prompt is self-contained. A stranger can run it with no other context.
- Iterate ends in a proof gate that defines done. Examples: specs, lint, review criteria (GNS-004).

## Iterate

1. Load the identity if absent. Read `references/prompt-anatomy.md`.
2. Gather raw material from the supplied task, context, and conversation. Ask one round if too thin.
3. Draft the four output sections per the anatomy.
4. Apply the rewrite table to every Rules and Iterate line.
5. Check the draft against Evaluate. Emit the fenced block.
