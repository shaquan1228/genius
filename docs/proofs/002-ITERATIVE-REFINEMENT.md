# Proof 002: Iterative Refinement

**Theorem ID:** GNS-002  
**Type:** Branch Proof  
**Branches From:** GNS-001  
**Status:** Proven  
**Date:** 2026-04-04  
**Method:** Direct proof via Modus Ponens chain  
**Scope:** Normative — proves what the system prescribes, not what agents always do

---

## Theorem Statement

**Natural language:**
In the genius system, for every non-trivial action where the goal is not yet achieved, observation recurs after the action.

**Formal:**

```
∀A: NonTrivial(A) ∧ ¬GoalAchieved → FollowedByObservation(A)
```

**Combined with GNS-001:** Observation before action (GNS-001) + observation after action (GNS-002) = continuous cycle. This proves OODA is a loop, not a one-shot sequence.

---

## Definitions

| Symbol | Meaning |
|--------|---------|
| NonTrivial(A) | Inherited from GNS-001: A has more than one viable approach, OR A involves uncertainty |
| GoalAchieved | The desired outcome has been reached: acceptance criteria satisfied, decision resolved, or uncertainty reduced to the point where further iteration adds no value |
| OODA(A) | A is processed through the Observe→Orient→Decide→Act loop |
| Cycle(A) | OODA processing of A is continuous — not a one-shot sequence |
| ActThenObserve(A) | After the Act phase for A completes, the system returns to Observe |
| FollowedByObservation(A) | After A is executed, explicit observation of the new state occurs before the next action |

**Scope boundary:** Same as GNS-001 — only rendered markdown content. HTML comments excluded.

**Normative scope:** This proof establishes what the system prescribes. The "No Iteration" anti-pattern (`docs/dreams/OODA.md` lines 144-148) and "Pattern Lock" failure mode (`docs/dreams/DECISION-THEORY.md` lines 89-91) are documented violations, not counterexamples.

---

## Proof

```
Premises:
  P1: NonTrivial(A) → OODA(A)                              [by GNS-001]
  P2: OODA(A) → Cycle(A) ∧ ActThenObserve(A)
  P3: Cycle(A) ∧ ¬GoalAchieved → FollowedByObservation(A)

 1. Assume NonTrivial(A) ∧ ¬GoalAchieved
 2. OODA(A)                                [P1, Modus Ponens]
 3. Cycle(A) ∧ ActThenObserve(A)           [P2, Modus Ponens]
 4. FollowedByObservation(A)               [P3, Modus Ponens] ∎

Cite as: "By GNS-002 (Iterative Refinement), ..."
```
