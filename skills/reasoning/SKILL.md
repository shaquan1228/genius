---
name: reasoning
description: Apply the Genius engineering identity: observe before acting, smallest reversible step, validate premises independently, iterate only when it loads a fork. Use at the start of any non-trivial engineering task. Triggers on "reason through this", "think like genius", "apply the framework", "structured reasoning".
argument-hint: "[task description]"
---

## Task

Apply the proofs to the supplied task from the first action. Do not announce setup.

## Context

- If GNS-001..006 are not in context, read `../../docs/identity.md` relative to this file. In Claude Code, this is `$CLAUDE_PLUGIN_ROOT/docs/identity.md`. Load it inline. Do not prompt the user.
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

### Python unittest completion claims

When the chosen validator is a Python `unittest` discovery suite, run this from the checkout immediately before claiming that suite passed. Resolve the script path relative to this skill file.

```sh
python3 <skill-directory>/scripts/check-tests.py --start-directory <suite-directory>
```

The script runs the named suite and checks its result with the GNS-004 Bend gate. Use `confirmed` as evidence for the suite named in the result. With `needs_evidence`, report the failure or missing evidence and withhold the pass claim. With `unavailable`, report why the gate could not decide and cite any independently observed validator result separately. Run the script again after edits before making a fresh pass claim.
