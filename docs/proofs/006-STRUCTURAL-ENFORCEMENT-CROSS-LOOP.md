# Proof 006: Structural Enforcement of Cross-Loop Premises

**Theorem ID:** GNS-006  
**Type:** Branch Proof  
**Branches From:** GNS-004  
**Branch Trigger:** NonTrivial(A) ∧ DependsOn₀(A, P) ∧ DependsOn₀(P, Output(L)) ∧ ExogenousLoop(L)  
**Status:** Proven  
**Date:** 2026-06-08  
**Method:** Disjunctive Syllogism over an exhaustive premise, then Biconditional Introduction  
**Scope:** Normative — proves what the system prescribes, not what agents always do

---

## The conceptual move: loops of loops

Proofs GNS-001 through GNS-005 describe the loop — singular: observe, validate, take the smallest reversible step, observe again, fork when the spring is loaded. They assume a closed world where every premise can, in principle, be probed directly.

The genius system does not run in a vacuum. It runs inside a field of *other* loops — other people, teams, external systems, processes, markets, the future state of the world, your own future self in another context. Each is a loop you do not iterate and cannot observe in place. GNS-006 is the first proof to situate the loop among other loops: it governs the premise that reaches *out* of your loop and into a foreign one.

---

## Theorem Statement

**Natural language:**
A non-trivial action depends on a premise P. The truth of P depends on the output of an exogenous loop. You do not drive that loop. You cannot observe it in place.

You cannot validate P by a signal into that loop. A signal is a request, a notice, a reminder, an intention, or a hope. A signal is direction aimed at a loop you do not control. By GNS-004, direction is not validation.

Only **structural enforcement** converts P to knowledge. You change the shared environment. The correct outcome then becomes the path of least resistance. P is true by construction. P no longer depends on the output of the foreign loop.

**Formal:**

```
∀A,P,L: NonTrivial(A) ∧ DependsOn₀(A,P) ∧ DependsOn₀(P, Output(L)) ∧ ExogenousLoop(L)
        → ( ValidatedIndependently₁(P) ↔ Enforce₀₁(P) )
```

**On the indices:** State 0 is the world before you act on P. State 1 is the world after you act on P.

The subscripts do necessary work. An act of enforcement *changes what P depends on*. The dependency holds at state 0. It fails at state 1.

Remove the indices and the theorem contradicts its own premises. An unindexed `StructurallyEnforced(P) → ¬DependsOn(P, Output(L))` contradicts the antecedent. That forces `¬StructurallyEnforced(P)` inside the trigger. Both sides of the biconditional then become false. The remedy becomes unreachable. The indices keep the theorem satisfiable.

**Why it matters:** You cannot probe another loop's future output from inside your own loop — it has not happened, and when it does it is produced by iterations you do not run. So a premise that depends on it stays an assumption no matter how loudly you announce it. The only validation available is to remove the dependency.

---

## Definitions

| Symbol | Meaning |
|--------|---------|
| NonTrivial(A) | Inherited from GNS-001 |
| DependsOnₙ(A, P) | Inherited from GNS-004 — A's correctness requires P — evaluated in state n |
| ExogenousLoop(L) | A loop whose iterations you do not drive and cannot observe in place: another person or team, an external system, a process, a market, a future state of the world, your own future self |
| Output(L) | A result of loop L not yet produced — therefore not observable from any loop, including your own |
| Observableₙ(X) | You can observe X directly from inside your own loop in state n |
| Assumptionₙ(P) | Inherited from GNS-004 — P is accepted without direct evidence, in state n |
| Direction(P) | Inherited from GNS-004 — an authority, a rule, or a request tells you to accept P. Direction is a type of Assumption(P) |
| ValidatedIndependentlyₙ(P) | Inherited from GNS-004 — direct evidence confirms P in state n. The chain that produced P does not confirm it. Direction does not confirm it |
| Signaling(P, L) | An attempt to make P true by influencing L from outside without driving its iterations — requesting, notifying, nudging, intending, hoping. GNS-004's Direction(P), pointed at a loop you do not run |
| ProbeInPlace(P) | You validate P at the place where L produces Output(L). This is a GNS-003 reversible step aimed at the result of the foreign loop |
| Enforce₀₁(P) | You change the shared environment between state 0 and state 1. The correct outcome then holds by default. It is the path of least resistance for the next actor |
| StructurallyEnforced₁(P) | The state after the act — P is true by construction, not by the cooperation of L |
| Cascade(A, P) | Inherited from GNS-004 |

**Scope boundary:** Same as GNS-001 — only rendered markdown content. HTML comments excluded.

**Normative scope:** That an agent sometimes signals into a foreign loop and gets the outcome it wanted is not a counterexample. GNS-006 prescribes what converts the premise to knowledge, not what an agent occasionally gets away with when the foreign loop happens to cooperate.

---

## Proof

```
Premises:
  P1: DependsOn₀(P, Output(L)) ∧ ExogenousLoop(L) → Assumption₀(P)
  P2: Signaling(P, L) → ¬ValidatedIndependently₁(P)
      [GNS-004: Direction(P) is not validation]
  P3: DependsOn₀(P, Output(L)) ∧ ExogenousLoop(L) ∧ ValidatedIndependently₁(P)
        → ( ProbeInPlace(P) ∨ Signaling(P, L) ∨ Enforce₀₁(P) )
      [exhaustive: three moves act on a cross-loop premise from inside your own
       loop. Observe the foreign output in place. Push on the foreign loop.
       Change what P depends on. No action is not a fourth move. It leaves P as
       an assumption, as P1 states. Validation needs one of the three moves.]
  P4: ProbeInPlace(P) → Observable₀(Output(L))
  P5: ¬Observable₀(Output(L))
      [by the definition of Output(L): L has not yet produced it. No loop can
       observe it, and this includes your own loop.]
  P6: Enforce₀₁(P) → StructurallyEnforced₁(P)
                     ∧ ¬DependsOn₁(P, Output(L))
                     ∧ ValidatedIndependently₁(P)
                     ∧ ¬Cascade(A, P)
      [you can observe truth by construction in your own loop, because you built
       it. It meets the GNS-004 standard. It needs no cooperation from L.]

 1. Assume NonTrivial(A) ∧ DependsOn₀(A,P) ∧ DependsOn₀(P,Output(L)) ∧ ExogenousLoop(L)
 2. DependsOn₀(P,Output(L)) ∧ ExogenousLoop(L)      [1, ∧-Elimination]
 3. Assumption₀(P)                                  [2, P1, Modus Ponens]
 4. ValidatedIndependently₁(P) is required          [1, GNS-004]
 5. ¬ProbeInPlace(P)                                [P4, P5, Modus Tollens]

    → direction:
 6.   Assume ValidatedIndependently₁(P)
 7.   ProbeInPlace(P) ∨ Signaling(P,L) ∨ Enforce₀₁(P)   [2, 6, P3, Modus Ponens]
 8.   ¬Signaling(P, L)                              [6, P2, Modus Tollens]
 9.   Enforce₀₁(P)                                  [7, 5, 8, Disjunctive Syllogism ×2]
10.  ValidatedIndependently₁(P) → Enforce₀₁(P)      [6–9, Conditional Proof]

    ← direction:
11.  Enforce₀₁(P) → ValidatedIndependently₁(P)      [P6, ∧-Elimination]

12. ValidatedIndependently₁(P) ↔ Enforce₀₁(P)       [10, 11, ↔-Introduction]
13. NonTrivial(A) ∧ DependsOn₀(A,P) ∧ DependsOn₀(P,Output(L)) ∧ ExogenousLoop(L)
      → ( ValidatedIndependently₁(P) ↔ Enforce₀₁(P) )
                                                    [1–12, Conditional Proof] ∎

Cite as: "By GNS-006 (Structural Enforcement of Cross-Loop Premises), ..."
```

**The pivot:** A premise inside your own loop has a direct test. You probe reality (GNS-003 reversible step, GNS-001 observation).

A cross-loop premise has no such test. The reality to probe is the output of the foreign loop. L has not yet produced it. Your loop cannot produce it.

Step 5 rules out the probe. Step 8 rules out the signal. One move remains. You change what P depends on. Structural enforcement is the GNS-003 reversible step. It does not probe the premise. It removes the premise.

---

## Corollary GNS-006.1 — the cross-agent case

**Statement:** A trusted collaborator is an exogenous loop. Trust does not make that loop observable in place. Trust therefore opens no fourth move.

**Formal:**

```
∀A,P,L: [GNS-006 antecedent] ∧ Agent(L) ∧ Trusted(L)
        → ( ValidatedIndependently₁(P) ↔ Enforce₀₁(P) )
```

**Proof:** `Agent(L) ∧ Trusted(L)` narrows the range of L. It adds no conjunct that a step of the GNS-006 derivation uses. It does not weaken P5. A trusted party has not yet produced the future output. Instantiate GNS-006 at L. Then conjoin. ∎

**Reading:** The corollary is the narrow case. It is not the theorem.

A request to a trusted colleague is Signaling(P, L). Step 8 rules it out. A request to an untrusted person gets the same result.

A change to the shared environment is Enforce₀₁(P). The colleague then cannot forget the item. Trust changes the probability. Trust does not change the epistemics.
