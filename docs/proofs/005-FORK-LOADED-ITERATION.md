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
