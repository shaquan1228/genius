# Proof 006: Structural Enforcement of Cross-Loop Premises

**Theorem ID:** GNS-006  
**Type:** Branch Proof  
**Branches From:** GNS-004  
**Branch Trigger:** NonTrivial(A) ∧ DependsOn(A, P) ∧ DependsOn(P, Output(L)) ∧ ExogenousLoop(L)  
**Status:** Proven  
**Date:** 2026-06-08  
**Method:** Direct proof via Modus Ponens + disjunctive syllogism + normative closure  
**Scope:** Normative — proves what the system prescribes, not what agents always do

---

## The conceptual move: loops of loops

Proofs GNS-001 through GNS-005 describe the loop — singular: observe, validate, take the smallest reversible step, observe again, fork when the spring is loaded. They assume a closed world where every premise can, in principle, be probed directly.

The genius system does not run in a vacuum. It runs inside a field of *other* loops — other people, teams, external systems, processes, markets, the future state of the world, your own future self in another context. Each is a loop you do not iterate and cannot observe in place. GNS-006 is the first proof to situate the loop among other loops: it governs the premise that reaches *out* of your loop and into a foreign one.

---

## Theorem Statement

**Natural language:**
When a non-trivial action depends on a premise whose truth depends on the output of an exogenous loop — a loop you do not drive and cannot observe in place — that premise cannot be validated by *signaling* into that loop (requesting, notifying, nudging, intending, hoping). Signaling is direction aimed at a loop you do not control, and by GNS-004 direction is not validation. Such a premise is converted to knowledge only by **structural enforcement**: altering the shared environment so the correct outcome is the path of least resistance — true by construction, no longer contingent on the foreign loop's output.

**Formal:**

```
∀A,P,L: NonTrivial(A) ∧ DependsOn(A,P) ∧ DependsOn(P, Output(L)) ∧ ExogenousLoop(L)
        → ( ValidatedIndependently(P) ↔ StructurallyEnforced(P) )
```

**Why it matters:** You cannot probe another loop's future output from inside your own loop — it has not happened, and when it does it is produced by iterations you do not run. So a premise that depends on it stays an assumption no matter how loudly you announce it. The only validation available is to remove the dependency.

---

## Definitions

| Symbol | Meaning |
|--------|---------|
| NonTrivial(A) | Inherited from GNS-001 |
| DependsOn(A, P) | Inherited from GNS-004 — A's correctness requires P |
| ExogenousLoop(L) | A loop whose iterations you do not drive and cannot observe in place: another person or team, an external system, a process, a market, a future state of the world, your own future self |
| Output(L) | A result of loop L not yet produced — therefore not yet observable from any loop, including your own |
| Signaling(P, L) | An attempt to make P true by influencing L from outside without driving its iterations — requesting, notifying, nudging, intending, hoping. The GNS-004 category "Direction," pointed at a loop you do not run |
| StructurallyEnforced(P) | The shared environment is altered so the correct outcome obtains by default — the path of least resistance for whatever acts next — making P true by construction rather than by L's cooperation |

**Scope boundary:** Same as GNS-001 — only rendered markdown content. HTML comments excluded.

**Normative scope:** That an agent sometimes signals into a foreign loop and gets the outcome it wanted is not a counterexample. GNS-006 prescribes what converts the premise to knowledge, not what an agent occasionally gets away with when the foreign loop happens to cooperate.

---

## Proof

```
Premises:
  P1: DependsOn(P, Output(L)) ∧ ExogenousLoop(L) → Assumption(P)
  P2: Signaling(P, L) → ¬ValidatedIndependently(P)        [GNS-004: direction is not validation]
  P3: StructurallyEnforced(P) → Known(P) ∧ ¬DependsOn(P, Output(L)) ∧ ¬Cascade(A)

 1. Assume NonTrivial(A) ∧ DependsOn(A,P) ∧ DependsOn(P, Output(L)) ∧ ExogenousLoop(L)
 2. ValidatedIndependently(P) required                    [GNS-004, Modus Ponens]
 3. Assumption(P)                                         [P1]
 4. Output(L) not observable in your own loop → cannot validate in place   [P1]
 5. Signaling cannot discharge the requirement            [P2]
 6. Only own-loop path to validation: remove DependsOn(P, Output(L))   [from 4, 5]
 7. StructurallyEnforced(P) does exactly that             [P3]
 8. ValidatedIndependently(P) ↔ StructurallyEnforced(P)   [from 6, 7] ∎

Cite as: "By GNS-006 (Structural Enforcement of Cross-Loop Premises), ..."
```

**The pivot:** For a premise inside your own loop, you validate by probing reality directly (GNS-003 reversible step, GNS-001 observation). For a cross-loop premise, the reality you would need to probe — the foreign loop's output — is not yet produced and not in your loop to produce. So GNS-004's requirement cannot be met in place; the only way to satisfy it is to change what P depends on. Structural enforcement is GNS-003's reversible step redirected from *probing* a premise to *dissolving* it.