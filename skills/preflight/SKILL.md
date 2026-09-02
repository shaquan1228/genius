---
name: preflight
description: Bind a 5-field contract (branch, in-scope files, off-limits, output shape, verification gate) before non-trivial action. Use when a task spans files or branches, or has an unclear done signal. Triggers on "preflight", "bind a contract", "scope this before you start".
argument-hint: "[task description]"
---

## Task

Bind a five-field contract for the supplied task, one field per proof, and hold to it for the rest of the session.

## Context

- Five fields, five proofs. The proof tree is the schema.
- If GNS-001..005 are not in context, read `../../docs/identity.md` relative to this file (`$CLAUDE_PLUGIN_ROOT/docs/identity.md` in Claude Code). Load it inline; do not prompt the user.
- Per-field operational language and proof derivations live in `references/proof-citations.md` relative to this file. Read it before binding.
- `references/examples.md` holds filled-field excerpts and the traps to rewrite. Read it for calibration.
- `references/contract-enforcement.md` describes the optional hook that hard-enforces the contract. The skill itself can only re-read.

## Rules

- Every field is observed or user-answered. Never guessed. If a field needs speculation, observe first.
- Name no tool you did not observe. Say "the branch tool / test runner / type checker this repo uses" until you have seen it.
- Trivial tasks get no contract. A single-file edit with no scope ambiguity, a question, or a read-only ask exits at step 1. Uncommitted changes alone are not a trigger.
- The contract block is the binding artifact. Fields are never edited in place; a scope change means a fresh contract.

## Evaluate

The contract ships only if all hold:

- All five fields are filled, each tagged with its proof citation.
- No field names a tool, path, or branch that was not observed or confirmed by the user.
- The verification gate names a runnable command and what its passing output means.
- Off-limits names at least one concrete "while I'm here" temptation for this task.

## Iterate

1. **Triviality check.** If the task is trivial, say so and exit.
2. **Identity check.** Load the identity if absent. Then read `references/proof-citations.md`.
3. **Bind fields.** Walk the five fields one at a time. In Claude Code use `AskUserQuestion` (load via `ToolSearch` with `select:AskUserQuestion` if absent); otherwise ask in plain text, one field per message. Fill from the supplied task where unambiguous.
   - **Target branch + stack position** — GNS-003. Echo the current branch using whatever branch tooling exists here. If a stacking tool is authenticated, echo the stack position too.
   - **In-scope files** — GNS-001. Explicit list. Named, read, or grep-confirmed. Not assumed.
   - **Off-limits** — GNS-005. Boundary-tool fixes, lint sweeps, adjacent refactors, "while I'm here" cleanup.
   - **Output shape** — GNS-002. Diff / numbered list / file path + 5-bullet summary / score-first.
   - **Verification gate** — GNS-004. The repo's test runner, type checker, and boundary checker as observed, plus `git diff --stat` against the in-scope list.
4. **Echo the contract.** Output a fenced `## Preflight Contract` block with all five fields filled, each line tagged with its proof citation. Check it against Evaluate before emitting.
5. **Commit.** Re-read the contract before each edit. If an edit would violate a field, stop and surface the conflict; do not silently expand scope. On scope-expansion temptation, return to step 3 for a fresh contract. For hard enforcement, wire the hook in `references/contract-enforcement.md`.
