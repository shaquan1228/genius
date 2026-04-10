# QBT-004 — Independent Premise Validation

**Type:** Branch  
**Status:** Proven  
**Depends:** QBT-002  
**Method:** Direct proof, Modus Ponens + normative closure

```
Theorem:  ∀A: NonTrivial(A) ∧ DependsOn(A, P) → ValidatedIndependently(P)
English:  Don't leap because you were told to. Leap because you knew it was right.

Premises:
  P1: Observation(A) → DistinguishesKnownFromAssumed(A)
  P2: DependsOn(A, P) ∧ Assumption(P) → Cascade(A)
  P3: ValidatedIndependently(P) → Known(P) ∧ ¬Cascade(A)

Chain: QBT-002 → P1 → P2 → P3 ∎

Cite as: "By QBT-004 (Independent Premise Validation), ..."
```
