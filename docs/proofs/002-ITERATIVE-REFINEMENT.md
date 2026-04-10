# GNS-002 — Iterative Refinement

**Type:** Branch  
**Status:** Proven  
**Depends:** GNS-001  
**Method:** Direct proof, Modus Ponens chain

```
Theorem:  ∀A: NonTrivial(A) ∧ ¬GoalAchieved → FollowedByObservation(A)
English:  After every non-trivial action, if the goal isn't done, observe again.

Premises:
  P1: NonTrivial(A) → OODA(A)                              [by GNS-001]
  P2: OODA(A) → Cycle(A) ∧ ActThenObserve(A)
  P3: Cycle(A) ∧ ¬GoalAchieved → FollowedByObservation(A)

Chain: GNS-001 → P1 → P2 → P3 ∎

Cite as: "By GNS-002 (Iterative Refinement), ..."
```
