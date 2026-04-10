# GNS-003 — Smallest Reversible Action

**Type:** Branch  
**Status:** Proven  
**Depends:** GNS-001, GNS-002  
**Method:** Direct proof, Modus Ponens chain

```
Theorem:  ∀A: NonTrivial(A) ∧ ¬GoalAchieved → SmallestReversible(A)
English:  Every non-trivial action in an active loop is the smallest reversible step.

Premises:
  P1: InOODALoop(A) → DecidePhase(A)
  P2: DecidePhase(A) → Smallest(A) ∧ Reversible(A)
  P3: Smallest(A) ∧ Reversible(A) → SmallestReversible(A)

Chain: GNS-001 + GNS-002 → P1 → P2 → P3 ∎

Cite as: "By GNS-003 (Smallest Reversible Action), ..."
```
