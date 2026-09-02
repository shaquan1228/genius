# Proof 005: Fork-Loaded Iteration

**Theorem ID:** GNS-005  
**Type:** Branch Proof  
**Branches From:** GNS-002  
**Branch Trigger:** Iteration(I)  
**Status:** Proven  
**Date:** 2026-04-08  
**Method:** Biconditional Introduction from two grounded conditionals, discharged by Conditional Proof  
**Scope:** Normative — proves what the system prescribes, not what agents always do

---

## Theorem Statement

**Natural language:**
In the genius system, iteration within a stable form is justified if and only if it loads latent potential for a future fork.

**Formal:**

```
∀I: Iteration(I) → (Justified(I) ↔ LoadsFork(I))
```

**Why it matters:** GNS-001/002/003 prove the mechanics of the loop (observe, iterate, smallest reversible step). GNS-005 proves the gating question one level above: when should iteration be running at all? It is the discriminator that separates preparation from tinkering.

**Sort note:** GNS-001 to GNS-004 quantify over actions A. GNS-005 quantifies over iterations I. An iteration I is a sequence of such actions.

P3a and P3b join the two sorts. P3a imports GNS-002. P3b imports GNS-003. Each premise grounds one direction of the biconditional.

---

## Definitions

| Symbol | Meaning |
|--------|---------|
| Iteration(I) | A sequence of non-trivial actions taken within a stable form, none of which constitutes a fork on its own |
| DwellState(I) | The interval in which I occurs — a stable form between two forks |
| Fork | A discrete branching event — the moment a lineage, form, project, or commit boundary changes shape |
| LoadsFork(I) | I accumulates substrate, capability, or insight that a future fork will release |
| Justified(I) | I is normatively prescribed — the system says to do it |
| Tinkering(I) | I extends the current form. It collects no substrate for a future fork |

**How to detect Tinkering:** The definition states a property of I. It does not state a verdict on I.

Three symptoms show the property in practice. The iteration answers no clear problem. It removes no blocking concern. It reduces no cognitive load.

These symptoms help you to recognize `¬LoadsFork(I)`. They are not the meaning of the term. Step 10 derives the verdict. The definition does not contain it.

**Scope boundary:** Same as GNS-001 — only rendered markdown content. HTML comments excluded.

**Normative scope:** This proof establishes what the system prescribes. There are two documented violations. Neither is a counterexample:

- **The Productivity Paradox** — the agent stays in motion inside a stable form. The effort makes the motion look like progress.
- **Pattern Lock** — the agent repeats an approach that worked before. The environment has since changed.

---

## Proof

```
Premises:
  P1:  Iteration(I) → DwellState(I)
  P2:  DwellState(I) → (LoadsFork(I) ⊻ Tinkering(I))
       [exhaustive and disjoint: in a dwell state, iteration collects substrate
        for a future fork, or it does not. There is no third state.]
  P3a: DwellState(I) ∧ LoadsFork(I) → Justified(I)
       [by GNS-002: the system prescribes iteration toward a goal that is not
        yet reached. The goal of a dwell state is the next fork.]
  P3b: DwellState(I) ∧ ¬LoadsFork(I) → ¬Justified(I)
       [by GNS-003: a prescribed step is the smallest step toward the goal.
        A step that moves toward no fork is not a step toward the goal.
        It therefore fails the GNS-003 constraint.]

 1. Assume Iteration(I)
 2. DwellState(I)                                 [1, P1, Modus Ponens]
 3. LoadsFork(I) → Justified(I)                   [2, P3a, Exportation]
 4. ¬LoadsFork(I) → ¬Justified(I)                 [2, P3b, Exportation]
 5. Justified(I) → LoadsFork(I)                   [4, Contraposition]
 6. Justified(I) ↔ LoadsFork(I)                   [3, 5, ↔-Introduction]
 7. Iteration(I) → (Justified(I) ↔ LoadsFork(I))  [1–6, Conditional Proof] ∎

Corollary 005.1 — Tinkering is never justified:

 8. LoadsFork(I) ⊻ Tinkering(I)                   [2, P2, Modus Ponens]
 9. Tinkering(I) → ¬LoadsFork(I)                  [8, Exclusive Disjunction]
10. Tinkering(I) → ¬Justified(I)                  [9, 4, Hypothetical Syllogism] ∎

Operational rule (Corollary 005.1, contraposed):
  Name the fork you are preparing for.
  If you can name it → you are loading → continue.
  If you cannot    → you are tinkering → stop.

Cite as: "By GNS-005 (Fork-Loaded Iteration), ..."
```
