# Proof 003: Smallest Reversible Action

**Theorem ID:** GNS-003  
**Type:** Branch Proof  
**Branches From:** GNS-002  
**Branch Trigger:** NonTrivial(A) within iteration  
**Status:** Proven  
**Date:** 2026-04-05  
**Method:** Direct proof via Modus Ponens chain  
**Scope:** Normative — proves what the system prescribes, not what agents always do

---

## Theorem Statement

**Natural language:**
In the genius system, every non-trivial action within an active OODA loop is the smallest reversible step that moves toward the goal.

**Formal:**

```
∀A: NonTrivial(A) ∧ ¬GoalAchieved → SmallestReversible(A)
```

---

## Definitions

| Symbol | Meaning |
|--------|---------|
| NonTrivial(A) | Inherited from GNS-001 |
| GoalAchieved | Inherited from GNS-002 |
| InOODALoop(A) | A is being processed within an active, iterating OODA cycle |
| DecidePhase(A) | A passes through the Decide phase of the OODA loop |
| SmallestStep(A) | A is the smallest action that could move toward the goal or resolve uncertainty |
| Reversible(A) | A can be undone or adjusted without cascading damage |
| SmallestReversible(A) | SmallestStep(A) ∧ Reversible(A) — the action is both minimal in scope and undoable |

**Scope boundary:** Same as GNS-001 — only rendered markdown content. HTML comments excluded.

**Normative scope:** The "Loop Too Big" anti-pattern (`docs/dreams/OODA.md` lines 132-136) is a documented violation, not a counterexample.

---

## Proof

```
Premises:
  P1: InOODALoop(A) → DecidePhase(A)
  P2: DecidePhase(A) → Smallest(A) ∧ Reversible(A)
  P3: Smallest(A) ∧ Reversible(A) → SmallestReversible(A)

 1. Assume NonTrivial(A) ∧ ¬GoalAchieved
 2. InOODALoop(A)                   [by GNS-001 + GNS-002]
 3. DecidePhase(A)                  [P1, Modus Ponens]
 4. Smallest(A) ∧ Reversible(A)     [P2, Modus Ponens]
 5. SmallestReversible(A)           [P3, Modus Ponens] ∎

Cite as: "By GNS-003 (Smallest Reversible Action), ..."
```
