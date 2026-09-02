# Proof Tree

Authoritative composability map for the genius proof system. Edit this file when adding proofs. Do not maintain composability maps inside individual proof files.

## Tree

```
GNS-001: Observation Precedence [PARENT LEMMA]
  └── GNS-002: Iterative Refinement [BRANCH]
        ├── step-constraint fork
        │     ├── GNS-003: Smallest Reversible Action [BRANCH]
        │     └── GNS-004: Independent Premise Validation [BRANCH]
        │           └── GNS-006: Structural Enforcement of Cross-Loop Premises [BRANCH]
        └── iteration-gate fork
              └── GNS-005: Fork-Loaded Iteration [BRANCH]
```

## Proof Types

**Parent Lemma** — GNS-001 only. No imports. Establishes the root behavioral constraint from which all branches descend.

**Branch Proof** — all others. Constrains a specific property of its parent's domain. Logically independent of its siblings — applies whenever its Branch Trigger holds, without requiring traversal of sibling proofs.

## Branch Triggers

| Proof | Trigger | Fires when |
|-------|---------|-----------|
| GNS-002 | `NonTrivial(A)` | Any non-trivial action |
| GNS-003 | `NonTrivial(A)` within iteration | Taking a step within the loop |
| GNS-004 | `NonTrivial(A) ∧ DependsOn(A, P)` | A step depends on a premise |
| GNS-005 | `Iteration(I)` | Before starting any iteration |
| GNS-006 | `NonTrivial(A) ∧ DependsOn(A, P) ∧ DependsOn(P, Output(L)) ∧ ExogenousLoop(L)` | A depended-on premise's truth rests on the output of a loop you don't run |

## Reading the Tree

The **step-constraint fork** (GNS-003 + GNS-004) fires on every non-trivial iteration step — check both before committing a step.

The **iteration-gate fork** (GNS-005) fires before iteration begins — confirm the iteration loads a fork before entering the loop.

GNS-006 sub-branches GNS-004: it fires only when a depended-on premise's truth-maker is the output of an exogenous loop — a loop you do not run (another person, team, system, the future, your future self) — resolving what "independent validation" means when the evidence lives outside your loop. It imports GNS-004 and is cited whenever its narrower trigger holds. The cross-agent case (a trusted collaborator) is its corollary GNS-006.1, not the theorem.

No proof requires its siblings. Each is cited by its own trigger alone.

## Adding a New Proof

1. Identify the parent: which proof's theorem does yours constrain or extend?
2. Identify the branch trigger: the antecedent of your theorem.
3. Add your proof to the tree above in the correct position.
4. Do not add a composability map inside your proof file — update this file instead.
