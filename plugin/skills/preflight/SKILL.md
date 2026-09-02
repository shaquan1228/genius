---
name: preflight
description: Bind a 5-field contract before non-trivial action. Use when a task has meaningful scope, output, or verification choices.
argument-hint: "[task description]"
---

Five fields, five proofs. The proof tree is the schema.

1. **Triviality check.** If the supplied task is trivial — a single-file edit with no branch or scope ambiguity, a question, or a read-only ask — say so and exit. Do not bind a contract. Uncommitted changes alone are not a trigger.

2. **Identity check.** If the Genius identity is not loaded (no GNS-001..005 references in current context), read the packaged identity at `../../docs/identity.md` relative to this `SKILL.md` and internalize the proofs before continuing. Do not refuse or prompt the user — load it inline and proceed.

3. **Bind fields.** Walk the five fields below one at a time using the active harness's user-question tool. Fill from the supplied task where unambiguous; never guess. For per-field operational language, read `references/proof-citations.md` relative to this `SKILL.md`.

   - **Target branch + stack position** — cite GNS-003. Echo `git branch --show-current`; for Graphite, the stack position.
   - **In-scope files** — cite GNS-001. Explicit list, observed not assumed.
   - **Off-limits** — cite GNS-005. Packwerk, lint, adjacent refactors, "while I'm here" cleanup.
   - **Output shape** — cite GNS-002. Diff / numbered list / file path + 5-bullet summary / score-first.
   - **Verification gate** — cite GNS-004. Specs, srb, packwerk, `git diff --stat` confirmation.

4. **Echo the contract.** Output a fenced `## Preflight Contract` block with all five fields filled, each line tagged with its proof citation. This block is the binding artifact.

5. **Commit.** Re-read the contract before each subsequent tool call this session. If a tool call would violate any field, stop and surface the conflict; do not silently expand scope. On scope-expansion temptation, return to step 3 for a fresh contract — do not edit fields in place.
