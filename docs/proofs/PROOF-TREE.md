# Proof Tree

Authoritative composability map for the quanbot proof system. Edit this file when adding proofs. Do not maintain composability maps inside individual proof files.

## Tree

```
QBT-001: Observation Precedence [PARENT LEMMA]
  └── QBT-002: Iterative Refinement [BRANCH]
        ├── step-constraint fork
        │     ├── QBT-003: Smallest Reversible Action [BRANCH]
        │     └── QBT-004: Independent Premise Validation [BRANCH]
        └── iteration-gate fork
              └── QBT-005: Fork-Loaded Iteration [BRANCH]
```

## Proof Types

**Parent Lemma** — QBT-001 only. No imports. Establishes the root behavioral constraint from which all branches descend.

**Branch Proof** — all others. Constrains a specific property of its parent's domain. Logically independent of its siblings — applies whenever its Branch Trigger holds, without requiring traversal of sibling proofs.

## Branch Triggers

| Proof | Trigger | Fires when |
|-------|---------|-----------|
| QBT-002 | `NonTrivial(A)` | Any non-trivial action |
| QBT-003 | `NonTrivial(A)` within iteration | Taking a step within the loop |
| QBT-004 | `NonTrivial(A) ∧ DependsOn(A, P)` | A step depends on a premise |
| QBT-005 | `Iteration(I)` | Before starting any iteration |

## Reading the Tree

The **step-constraint fork** (QBT-003 + QBT-004) fires on every non-trivial iteration step — check both before committing a step.

The **iteration-gate fork** (QBT-005) fires before iteration begins — confirm the iteration loads a fork before entering the loop.

No proof requires its siblings. Each is cited by its own trigger alone.

## Adding a New Proof

1. Identify the parent: which proof's theorem does yours constrain or extend?
2. Identify the branch trigger: the antecedent of your theorem.
3. Add your proof to the tree above in the correct position.
4. Do not add a composability map inside your proof file — update this file instead.
