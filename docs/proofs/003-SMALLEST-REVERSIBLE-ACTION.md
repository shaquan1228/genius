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
