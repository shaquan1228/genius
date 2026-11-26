# Shared proof backend

Every Genius skill uses this selection before applying GNS-001..006. The identity, behavioral rules, and proof triggers apply in either mode.

## Select

1. An explicit `backend:markdown` or `backend:bend` on the current invocation wins.
2. Otherwise, inherit the most recent explicit selection in this conversation.
3. With no selection, use Markdown.

The selection applies across skills. Moving from reasoning to preflight, Bayesian analysis, improvement, or prompt composition does not reset it. Do not ask for a choice when these rules resolve it. Already having the identity or GNS citations in context does not bypass backend selection. When the user switches, use the newly selected proof treatment as authority rather than an earlier backend's receipt.

## Load

Resolve the plugin root as `../..` from this file. In Claude Code it is also `$CLAUDE_PLUGIN_ROOT`. Load `docs/identity.md` inline if needed; do not announce setup.

- **Markdown:** use the written postulate and proof sources linked from the identity. Read a full argument when needed. `python3 bin/genius-proof --backend markdown` is the standalone equivalent. Prose is not a machine-checking receipt.
- **Bend:** from the plugin root, run `python3 bin/genius-proof --backend bend`, then load its checked source output and `docs/proofs/logic.bend`. Respect an explicit `BEND_BIN`. This requires Bend 2 and the Lean-backed kernel. A missing toolchain, missing counterpart, or failed check stops the selected mode with a reported error; never silently use Markdown or claim an unperformed check. Use `--ordinary` only on an explicit user request and label the weaker check.

For a particular derivation, resolve its ID through the same backend, for example `python3 bin/genius-proof GNS-004 --backend bend`. Markdown links in skill references identify the written source or operational explanation; they do not override a Bend selection. `docs/proofs/PROOF-TREE.md` remains the trigger/composability map in both modes.

The standalone command is stateless and defaults to Markdown. A skill inheriting a conversation's Bend selection must pass `--backend bend` explicitly. Full plugin checkouts contain the command; instruction-only evaluation snapshots do not yet package it or the toolchain. Do not pretend the command is available in those snapshots.

## Interpret

Postulate 001 remains an open hypothesis. Bend checks conditional conclusions under named premises; it does not establish those premises' truth, prove facts about the current task, or perform the task's own validation. Keep applying the invoking skill's behavioral and evidence requirements.

When composing a prompt for another agent or session, carry the selected backend explicitly and tell the recipient to resolve the proofs in its own environment. Do not assume your checked context, compiler, or paths exist there.
