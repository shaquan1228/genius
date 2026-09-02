# Proof 002: Iterative Refinement

**Theorem ID:** GNS-002  
**Type:** Branch Proof  
**Branches From:** GNS-001  
**Branch Trigger:** NonTrivial(A) ∧ ¬GoalAchieved(A)  
**Status:** Proven  
**Date:** 2026-04-04  
**Method:** Direct proof via Modus Ponens chain, discharged by Conditional Proof  
**Scope:** Normative — proves what the system prescribes, not what agents always do

---

## Theorem Statement

**Natural language:**
In the genius system, for every non-trivial action where the goal is not yet achieved, observation recurs after the action.

**Formal:**

```
∀A: NonTrivial(A) ∧ ¬GoalAchieved(A) → FollowedByObservation(A)
```

**Combined with GNS-001:** GNS-001 puts observation before the action. GNS-002 puts observation after the action. The two proofs together describe a continuous cycle. They do not describe a single sequence.

This proof does not derive the cycle. P2 states it. P2 unfolds the definition of the OODA loop.

---

## Definitions

| Symbol | Meaning |
|--------|---------|
| NonTrivial(A) | Inherited from GNS-001: A has more than one viable approach, OR A involves uncertainty |
| GoalAchieved(A) | The outcome that A aims at is reached. Three signals show this: the acceptance criteria pass, the decision is resolved, or more iteration adds no value |
| OODA(A) | A is processed through the Observe→Orient→Decide→Act loop |
| Cycle(A) | OODA processing of A is continuous — not a one-shot sequence |
| ActThenObserve(A) | After the Act phase for A completes, the system returns to Observe |
| FollowedByObservation(A) | After A is executed, explicit observation of the new state occurs before the next action |

**Scope boundary:** Same as GNS-001 — only rendered markdown content. HTML comments excluded.

**Normative scope:** This proof establishes what the system prescribes. There are two documented violations. Neither is a counterexample:

- **No Iteration** — the agent runs the loop one time. The agent then assumes the goal is reached.
- **Pattern Lock** — the agent repeats an approach that worked before. The environment has since changed.

---

## Proof

```
Premises:
  P1: NonTrivial(A) → OODA(A)                                          [by GNS-001]
  P2: OODA(A) → Cycle(A) ∧ ActThenObserve(A)
  P3: Cycle(A) ∧ ActThenObserve(A) ∧ ¬GoalAchieved(A) → FollowedByObservation(A)

 1. Assume NonTrivial(A) ∧ ¬GoalAchieved(A)
 2. NonTrivial(A)                                    [1, ∧-Elimination]
 3. ¬GoalAchieved(A)                                 [1, ∧-Elimination]
 4. OODA(A)                                          [2, P1, Modus Ponens]
 5. Cycle(A) ∧ ActThenObserve(A)                     [4, P2, Modus Ponens]
 6. Cycle(A) ∧ ActThenObserve(A) ∧ ¬GoalAchieved(A)  [5, 3, ∧-Introduction]
 7. FollowedByObservation(A)                         [6, P3, Modus Ponens]
 8. NonTrivial(A) ∧ ¬GoalAchieved(A) → FollowedByObservation(A)
                                                     [1–7, Conditional Proof] ∎

Cite as: "By GNS-002 (Iterative Refinement), ..."
```
