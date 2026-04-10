# Proof 004: Independent Premise Validation

**Theorem ID:** GNS-004  
**Type:** Branch Proof  
**Branches From:** GNS-002  
**Branch Trigger:** NonTrivial(A) ∧ DependsOn(A, P)  
**Status:** Proven  
**Date:** 2026-04-06  
**Method:** Direct proof via Modus Ponens + normative closure  
**Scope:** Normative — proves what the system prescribes, not what agents always do

---

## Theorem Statement

**Natural language:**
In the genius system, every non-trivial action that depends on a premise requires independent validation of that premise. Derivation is not validation. Only direct evidence is validation.

**Formal:**

```
∀A: NonTrivial(A) ∧ DependsOn(A, P) → ValidatedIndependently(P)
```

**Why it matters:** A chain of reasoning can be perfectly valid and still be wrong. If the first premise is false, every subsequent step inherits that falseness. Validation checks external correctness; derivation only checks internal consistency.

---

## Proof

```
Premises:
  P1: Observation(A) → DistinguishesKnownFromAssumed(A)
  P2: DependsOn(A, P) ∧ Assumption(P) → Cascade(A)
  P3: ValidatedIndependently(P) → Known(P) ∧ ¬Cascade(A)

 1. Assume NonTrivial(A) ∧ DependsOn(A, P)
 2. DistinguishesKnownFromAssumed(A)    [GNS-002 → observation, P1]
 3. Cascade risk if P unvalidated       [P2, Modus Ponens]
 4. ValidatedIndependently(P) required  [P3, normative closure] ∎

Cite as: "By GNS-004 (Independent Premise Validation), ..."
```
