# Proof 004: Independent Premise Validation

**Theorem ID:** GNS-004  
**Type:** Branch Proof  
**Branches From:** GNS-002  
**Branch Trigger:** NonTrivial(A) ∧ DependsOn(A, P)  
**Status:** Proven  
**Date:** 2026-04-06  
**Method:** Reductio ad Absurdum against a normative premise, discharged by Conditional Proof  
**Scope:** Normative — proves what the system prescribes, not what agents always do

---

## Theorem Statement

**Natural language:**
In the genius system, every non-trivial action that depends on a premise requires independent validation of that premise. Derivation is not validation. Direction is not validation. Only direct evidence is validation.

**Formal:**

```
∀A,P: NonTrivial(A) ∧ DependsOn(A, P) → ValidatedIndependently(P)
```

**Why it matters:** A chain of reasoning can be perfectly valid and still be wrong. If the first premise is false, every subsequent step inherits that falseness. Validation checks external correctness; derivation only checks internal consistency.

---

## Definitions

| Symbol | Meaning |
|--------|---------|
| NonTrivial(A) | Inherited from GNS-001 |
| PrecededByObservation(A) | Inherited from GNS-001 — explicit observation of facts, signals, and constraints occurred before A |
| DependsOn(A, P) | Action A's correctness requires premise P to be true. If P is false, A is unsound regardless of A's internal logic. |
| DistinguishesKnownFromAssumed(A) | The observation preceding A sorts what was seen from what was supposed — every premise A rests on is classified as one or the other |
| Assumption(P) | P is accepted without direct evidence — either derived from a chain of reasoning, or asserted by an authority/rule |
| Direction(P) | P is accepted because an authority, rule, or request instructed its acceptance. A species of Assumption(P): direction is not validation. |
| ValidatedIndependently(P) | P was confirmed through direct evidence or direct testing — not through the reasoning chain that produced it, and not because an authority directed its acceptance |
| Cascade(A, P) | P is false, A depends on P, and A's output has become a false premise for subsequent actions, propagating the error through the inference chain |
| CascadeRisk(A, P) | A depends on P and P's truth is not established, so Cascade(A, P) obtains for all anyone knows. Risk, not yet damage. |

**Scope boundary:** Same as GNS-001 — only rendered markdown content. HTML comments excluded.

**Normative scope:** Rushed Processing — skipping Orient and jumping to action, so that premises are never sorted into known and assumed — is a documented violation of this norm, not a counterexample.

---

## Proof

```
Premises:
  P1: PrecededByObservation(A) → DistinguishesKnownFromAssumed(A)
  P2: DistinguishesKnownFromAssumed(A) ∧ ¬ValidatedIndependently(P) → Assumption(P)
  P3: DependsOn(A, P) ∧ Assumption(P) → CascadeRisk(A, P)
  N:  ¬CascadeRisk(A, P)
      [normative premise: the system prescribes actions whose premises carry no cascade risk.
       N is what makes this proof normative rather than descriptive — it states the standard,
       and the derivation shows what the standard costs.]

 1. Assume NonTrivial(A) ∧ DependsOn(A, P)
 2. NonTrivial(A)                               [1, ∧-Elimination]
 3. DependsOn(A, P)                             [1, ∧-Elimination]
 4. PrecededByObservation(A)                    [2, GNS-001, Modus Ponens]
 5. DistinguishesKnownFromAssumed(A)            [4, P1, Modus Ponens]

 6.   Assume ¬ValidatedIndependently(P)         [for Reductio]
 7.   DistinguishesKnownFromAssumed(A) ∧ ¬ValidatedIndependently(P)  [5, 6, ∧-Introduction]
 8.   Assumption(P)                             [7, P2, Modus Ponens]
 9.   DependsOn(A, P) ∧ Assumption(P)           [3, 8, ∧-Introduction]
10.   CascadeRisk(A, P)                         [9, P3, Modus Ponens]
11.   CascadeRisk(A, P) ∧ ¬CascadeRisk(A, P)    [10, N, ∧-Introduction]
12.   ⊥                                         [11, Contradiction]

13. ValidatedIndependently(P)                   [6–12, Reductio ad Absurdum]
14. NonTrivial(A) ∧ DependsOn(A, P) → ValidatedIndependently(P)
                                                [1–13, Conditional Proof] ∎

Cite as: "By GNS-004 (Independent Premise Validation), ..."
```

**On the shape of the argument:** the requirement is reached by reductio, not by reading P3 forward. Direct evidence being *sufficient* to clear the risk would not show it is *necessary* — that inference affirms the consequent. What the reductio shows is that the alternative is unavailable: hold the norm N, and ¬ValidatedIndependently(P) is contradictory. That is why the burden cannot be discharged by more reasoning. Reasoning produces Assumption(P), and Assumption(P) is exactly what steps 8–10 turn into risk.
