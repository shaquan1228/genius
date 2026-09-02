# Proof 003: Smallest Reversible Action

**Theorem ID:** GNS-003  
**Type:** Branch Proof  
**Branches From:** GNS-002  
**Branch Trigger:** NonTrivial(A) ∧ InOODALoop(A)  
**Status:** Proven  
**Date:** 2026-04-05  
**Method:** Direct proof via Modus Ponens chain, discharged by Conditional Proof  
**Scope:** Normative — proves what the system prescribes, not what agents always do

---

## Theorem Statement

**Natural language:**
In the genius system, every non-trivial action within an active OODA loop is the smallest reversible step that moves toward the goal.

**Formal:**

```
∀A: NonTrivial(A) ∧ InOODALoop(A) ∧ ¬GoalAchieved(A) → SmallestReversible(A)
```

`InOODALoop(A)` is a conjunct of the antecedent. It is not a derived step. It is the branch trigger. GNS-003 fires on a step that is already in the loop.

Two parent premises supply `InOODALoop(A)` for any non-trivial A:

- GNS-001 P1 — `NonTrivial(A) → OODA(A)`
- GNS-002 P2 — `OODA(A) → Cycle(A) ∧ ActThenObserve(A)`

These are premises of the parents. They are not theorems of the parents. This proof therefore assumes the trigger. It does not cite a theorem that gives no such result.

---

## Definitions

| Symbol | Meaning |
|--------|---------|
| NonTrivial(A) | Inherited from GNS-001 |
| GoalAchieved(A) | Inherited from GNS-002 |
| InOODALoop(A) | A is being processed within an active, iterating OODA cycle — OODA(A) ∧ Cycle(A) |
| DecidePhase(A) | A passes through the Decide phase of the OODA loop |
| SmallestStep(A) | A is the smallest action that could move toward the goal or resolve uncertainty |
| Reversible(A) | A can be undone or adjusted without cascading damage |
| SmallestReversible(A) | Defined as SmallestStep(A) ∧ Reversible(A) — the action is both minimal in scope and undoable |

**Scope boundary:** Same as GNS-001 — only rendered markdown content. HTML comments excluded.

**Normative scope:** There is one documented violation. It is not a counterexample:

- **Loop Too Big** — the agent observes the full codebase. The agent orients to every pattern. The agent decides on a complete refactor. The agent then changes fifty files in one step.

---

## Proof

```
Premises:
  P1: InOODALoop(A) → DecidePhase(A)
  P2: DecidePhase(A) ∧ ¬GoalAchieved(A) → SmallestStep(A) ∧ Reversible(A)

 1. Assume NonTrivial(A) ∧ InOODALoop(A) ∧ ¬GoalAchieved(A)
 2. InOODALoop(A)                                [1, ∧-Elimination]
 3. ¬GoalAchieved(A)                             [1, ∧-Elimination]
 4. DecidePhase(A)                               [2, P1, Modus Ponens]
 5. DecidePhase(A) ∧ ¬GoalAchieved(A)            [4, 3, ∧-Introduction]
 6. SmallestStep(A) ∧ Reversible(A)              [5, P2, Modus Ponens]
 7. SmallestReversible(A)                        [6, Definition of SmallestReversible]
 8. NonTrivial(A) ∧ InOODALoop(A) ∧ ¬GoalAchieved(A) → SmallestReversible(A)
                                                 [1–7, Conditional Proof] ∎

Cite as: "By GNS-003 (Smallest Reversible Action), ..."
```
