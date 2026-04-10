# GNS-005 — Fork-Loaded Iteration

**Type:** Branch  
**Status:** Proven  
**Depends:** GNS-002  
**Method:** Direct proof, Modus Ponens chain  
**Branch Trigger:** Iteration(I)

```
Theorem:  ∀I: Iteration(I) → (Justified(I) ↔ LoadsFork(I))
English:  Iteration is justified if and only if it loads latent potential for a future fork.

Premises:
  P1: Iteration(I) → DwellState(I)
  P2: DwellState(I) → LoadsFork(I) ∨ Tinkering(I)
  P3: DwellState(I) → (Justified(I) ↔ LoadsFork(I))

Branch: GNS-002 ⟶ [Iteration(I)] ⟶ GNS-005 ∎

Operational rule:
  Name the fork you are preparing for.
  If you can name it → you are loading → continue.
  If you cannot    → you are tinkering → stop.

Cite as: "By GNS-005 (Fork-Loaded Iteration), ..."
```
