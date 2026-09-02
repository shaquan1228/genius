# Proof 005: Fork-Loaded Iteration

**Theorem ID:** GNS-005  
**Type:** Branch Proof  
**Branches From:** GNS-002  
**Branch Trigger:** Iteration(I)  
**Status:** Proven  
**Date:** 2026-04-08  
**Method:** Direct proof via Modus Ponens chain with biconditional introduction  
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

---

## Definitions

| Symbol | Meaning |
|--------|---------|
| Iteration(I) | A sequence of non-trivial actions taken within a stable form, none of which constitutes a fork on its own |
| DwellState(I) | The interval in which I occurs — a stable form between two forks |
| Fork | A discrete branching event — the moment a lineage, form, project, or commit boundary changes shape |
| LoadsFork(I) | I accumulates substrate, capability, or insight that a future fork will release |
| Justified(I) | I is normatively prescribed — the system says to do it |
| Tinkering(I) | Iteration that is not justified — iteration without a clear problem, blocking concern, or reduction in cognitive load |

**Scope boundary:** Same as GNS-001 — only rendered markdown content. HTML comments excluded.

**Normative scope:** This proof establishes what the system prescribes. The Productivity Paradox (`docs/dreams/STOP-TINKERING.md` lines 95-106) and the Pattern Lock failure mode (`docs/dreams/DECISION-THEORY.md` lines 89-99) are documented violations, not counterexamples.

---

## Proof

```
Premises:
  P1: Iteration(I) → DwellState(I)
  P2: DwellState(I) → LoadsFork(I) ∨ Tinkering(I)
  P3: DwellState(I) → (Justified(I) ↔ LoadsFork(I))

 1. Assume Iteration(I)
 2. DwellState(I)                          [P1, Modus Ponens]
 3. LoadsFork(I) ∨ Tinkering(I)            [P2, Modus Ponens]
 4. Justified(I) ↔ LoadsFork(I)            [P3, Modus Ponens]
 5. Iteration(I) → (Justified(I) ↔ LoadsFork(I))  [1–4, Conditional Proof] ∎

Operational rule:
  Name the fork you are preparing for.
  If you can name it → you are loading → continue.
  If you cannot    → you are tinkering → stop.

Cite as: "By GNS-005 (Fork-Loaded Iteration), ..."
```
