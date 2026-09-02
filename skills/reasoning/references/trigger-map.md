# Trigger map

Condensed from `../../../docs/proofs/PROOF-TREE.md`. Each row says when a proof fires and the question to ask. Read the full proof for the derivation.

| Proof | Fires when | Ask |
|---|---|---|
| GNS-001 Observation Precedence | Before any non-trivial action | What have I seen? What am I assuming? |
| GNS-002 Iterative Refinement | Any non-trivial action | What is the target shape? How will I know I reached it? |
| GNS-003 Smallest Reversible Action | Taking a step within the loop | Is there a smaller step? Can this one be undone? |
| GNS-004 Independent Premise Validation | A step depends on a premise | What checks this premise, other than my own reasoning? |
| GNS-005 Fork-Loaded Iteration | Before starting any iteration | Which future fork does this iteration load? If none, stop. |
| GNS-006 Structural Enforcement of Cross-Loop Premises | A premise's truth rests on a loop I do not run | Who or what produces this fact? Can I make its absence visible instead of trusting it? |

## Reading order in practice

- GNS-001 fires first, always. Nothing else runs until observation has happened.
- GNS-005 fires once, at the gate, before iteration starts.
- GNS-003 and GNS-004 fire together on every step. Check both before you commit a step.
- GNS-006 fires only when the GNS-004 validator lives outside your loop. Examples: another team, CI, a future session.

Full proofs: `../../../docs/proofs/`.
