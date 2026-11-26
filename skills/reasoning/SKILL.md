---
name: reasoning
description: Apply the Genius engineering identity: observe before acting, smallest reversible step, validate premises independently, iterate only when it loads a fork. Use at the start of any non-trivial engineering task. Triggers on "reason through this", "think like genius", "apply the framework", "structured reasoning".
argument-hint: "[task description] [backend:markdown|bend]"
---

## Task

Apply the proofs to the supplied task from the first action. Do not announce setup.

## Context

- If GNS-001..006 are not in context, read `../../docs/identity.md` relative to this file. In Claude Code, this is `$CLAUDE_PLUGIN_ROOT/docs/identity.md`. Load it inline. Do not prompt the user.
- Choose the proof backend explicitly. Default to `backend:markdown`; an explicit `backend:bend` selects the `.bend` counterparts. If a different backend is already loaded, replace the proof-source context with the selected treatment rather than treating an earlier load as satisfying this selection.
- For Markdown, read the postulate and proof `.md` sources linked from the identity. The standalone equivalent is `python3 bin/genius-proof --backend markdown`, run from the plugin root. This is prose reasoning, not a compiler proof receipt.
- For Bend, run `python3 bin/genius-proof --backend bend` from the plugin root and load its checked source output, plus `docs/proofs/logic.bend`. The command requires Bend 2 and the Lean-backed kernel. Respect an explicit `BEND_BIN` compiler path. If the toolchain or any check fails, report the failure; do not silently use Markdown or claim the proof was checked. Use `--ordinary` only when the user explicitly asks for the weaker ordinary checker and label it as such.
- The postulate remains an open hypothesis in either backend. The Bend files check the conclusions under their named premises; they do not prove those premises true or establish facts about the current task. The behavioral rules below apply in both modes.
- `references/trigger-map.md` states when each proof fires and the question it asks. Read it before the first step.
- `references/worked-example.md` traces one task through all five proofs. It then shows the same task done without them. Read it for calibration.

## Rules

- Do not announce that the identity was loaded. Start on the task.
- Make the first action on the task an observation. Do not edit first (GNS-001).
- Take the smallest reversible step available. If a step is irreversible, flag it before you take it (GNS-003).
- Cite a check for every "done" claim. The check must not derive from your own reasoning chain (GNS-004).
- Complete clear, authorized tasks directly. Before extra investigation, name the decision it could change. If none exists, stop investigating (GNS-005).
- Report in the identity's Communicating shape: TL;DR, then Observed, Decided, Next steps, Blockers.

## Evaluate

The work ships only if all of these hold:

- The first tool call was a read, grep, or command that observed state.
- Each edit is reversible, or its irreversibility was surfaced first.
- The done claim names a validator that ran and returned the expected signal.
- Each extra investigation named the decision it could change. A clear task was completed without inventing a fork.
- The final report is in Communicating shape.

## Iterate

1. Load the identity if absent. Read `references/trigger-map.md`.
2. Observe the task surface: files, tests, current branch, existing patterns (GNS-001).
3. Complete the clear task. For extra investigation, name the decision it could change. If none exists, stop investigating (GNS-005).
4. Take one step. Check it against GNS-003 and GNS-004 before you commit it. Repeat until the goal is reached (GNS-002).
5. Run the validator. Report in Communicating shape. Check the report against Evaluate.
