---
name: preflight
description: Bind a 5-field contract (branch, in-scope files, off-limits, output shape, verification gate) before non-trivial action. Use when a task spans files or branches, or has an unclear done signal. Triggers on "preflight", "bind a contract", "scope this before you start".
argument-hint: "[task description]"
---

## Task

Bind a five-field contract for the supplied task. Each field maps to one proof. Hold to the contract for the rest of the session.

## Context

- Five fields, five proofs. The proof tree is the schema.
- If GNS-001..005 are not in context, read `../../docs/identity.md` relative to this file. In Claude Code, this is `$CLAUDE_PLUGIN_ROOT/docs/identity.md`. Load it inline. Do not prompt the user.
- `references/proof-citations.md` holds the operational language and derivation for each field. Read it before you bind.
- `references/examples.md` holds filled-field excerpts and traps to rewrite. Read it for calibration.
- `references/contract-enforcement.md` describes an optional hook that hard-enforces the contract. The skill itself can only re-read.

## Rules

- Fill each field from observation or a user answer. Do not guess. If a field needs speculation, observe first.
- Do not name a tool you did not observe. Say "the branch tool this repo uses" until you have seen it. The same applies to the test runner and type checker.
- Do not bind a contract for a trivial task. A trivial task is a single-file edit with no scope ambiguity, a question, or a read-only ask. Uncommitted changes alone are not a trigger.
- The contract block is the binding artifact. Do not edit fields in place. A scope change requires a fresh contract.

## Evaluate

The contract ships only if all of these hold:

- All five fields are filled. Each field carries its proof citation.
- No field names a tool, path, or branch that was not observed or confirmed by the user.
- The verification gate names a runnable command. It states what a passing result looks like.
- Off-limits names at least one concrete "while I'm here" temptation for this task.

## Iterate

1. **Triviality check.** If the task is trivial, say so and exit.
2. **Identity check.** Load the identity if absent. Read `references/proof-citations.md`.
3. **Bind fields.** Walk the five fields one at a time. In Claude Code, use `AskUserQuestion`. Load it with `ToolSearch` (`select:AskUserQuestion`) if absent. Otherwise ask in plain text, one field per message. Fill from the supplied task where unambiguous.
   - **Target branch + stack position** (GNS-003). Echo the current branch with the branch tool present here. If a stacking tool is authenticated, echo the stack position.
   - **In-scope files** (GNS-001). Give an explicit list. Each file is named, read, or grep-confirmed. Do not assume.
   - **Off-limits** (GNS-005). Name boundary-tool fixes, lint sweeps, adjacent refactors, and "while I'm here" cleanup.
   - **Output shape** (GNS-002). One of: diff, numbered list, file path + 5-bullet summary, score-first.
   - **Verification gate** (GNS-004). Name the repo's test runner, type checker, and boundary checker as observed. Add `git diff --stat` against the in-scope list.
4. **Echo the contract.** Output a fenced `## Preflight Contract` block. Fill all five fields. Tag each line with its proof citation. Check it against Evaluate before you emit.
5. **Commit.** Re-read the contract before each edit. If an edit would violate a field, stop and surface the conflict. Do not expand scope silently. On scope-expansion temptation, return to step 3 for a fresh contract. For hard enforcement, wire the hook in `references/contract-enforcement.md`.
