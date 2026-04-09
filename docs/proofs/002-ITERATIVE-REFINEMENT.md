# Proof 002: Iterative Refinement

**Theorem ID:** QBT-002
**Type:** Chain Proof (depends on QBT-001)
**Status:** Proven
**Date:** 2026-04-05
**Method:** Direct proof via Modus Ponens chain (imports QBT-001)
**Scope:** Normative — proves what the system prescribes, not what agents always do

---

## Theorem Statement

**Natural language:**
In the genius system, for every non-trivial action where the goal is not yet achieved, observation recurs after the action.

**Formal:**

```
∀A: NonTrivial(A) ∧ ¬GoalAchieved → FollowedByObservation(A)
```

**Combined with QBT-001:** Observation before action (QBT-001) + observation after action (QBT-002) = continuous cycle. This proves OODA is a loop, not a one-shot sequence.

---

## Definitions

| Symbol | Meaning | Grounding |
|--------|---------|-----------|
| NonTrivial(A) | Inherited from QBT-001: A has more than one viable approach, OR A involves uncertainty | `docs/dreams/OODA.md` line 88 |
| GoalAchieved | The desired outcome has been reached: acceptance criteria satisfied, decision resolved, or uncertainty reduced to the point where further iteration adds no value | `docs/dev/WORKFLOW.md` line 35: "Repeat until acceptance criteria are satisfied"; `docs/dreams/STOP-TINKERING.md` line 45: scoring determines whether to proceed or stop; `docs/dreams/OODA.md` line 148: "Run loop continuously until goal achieved" |
| OODA(A) | A is processed through the Observe→Orient→Decide→Act loop | Inherited from QBT-001 |
| Cycle(A) | OODA processing of A is continuous — not a one-shot sequence | `docs/dreams/OODA.md` line 9: "continuous cycle"; line 16: "Iterative by design" |
| ActThenObserve(A) | After the Act phase for A completes, the system returns to Observe | `docs/dreams/OODA.md` line 108: "→ Observe: Now need to handle duplicate emails..." |
| FollowedByObservation(A) | After A is executed, explicit observation of the new state occurs before the next action | `docs/dev/WORKFLOW.md` line 9: "Repeat this loop after each meaningful result" |

**Scope boundary:** Same as QBT-001 — only rendered markdown content. HTML comments excluded.

**Normative scope:** This proof establishes what the system prescribes. The "No Iteration" anti-pattern (`docs/dreams/OODA.md` lines 144-148) and "Pattern Lock" failure mode (`docs/dreams/DECISION-THEORY.md` lines 89-91) are documented violations, not counterexamples.

---

## Dependencies

```
IMPORT: QBT-001 (Observation Precedence)
STATEMENT: ∀A: NonTrivial(A) → PrecededByObservation(A)
SOURCE: docs/proofs/001-OBSERVATION-PRECEDENCE.md
```

QBT-001's conclusion is used as a premise: if non-trivial actions are preceded by observation, they occur within the OODA loop.

---

## Premises

### P1: Non-trivial actions occur within the OODA loop (by QBT-001)

```
∀A: NonTrivial(A) → OODA(A)
```

**Evidence:**

| Source | Line(s) | Text |
|--------|---------|------|
| QBT-001 | (conclusion) | `∀A: NonTrivial(A) → PrecededByObservation(A)` — observation precedes action, which means the action is within the OODA framework |
| `docs/dreams/OODA.md` | 9 | "OODA is a continuous cycle for making decisions under uncertainty" |
| `docs/rules.md` | 7 | "When making non-trivial decisions, always apply OODA loop" |

**Semantic validation:** QBT-001 proved that non-trivial actions are preceded by observation via the OODA loop. If an action goes through OODA, it is within the OODA framework. This premise bridges QBT-001's conclusion to QBT-002's domain: the loop's continuity.

---

### P2: OODA is a continuous cycle — after Act, the system returns to Observe

```
∀A: OODA(A) → Cycle(A) ∧ ActThenObserve(A)
```

**Evidence:**

| Source | Line(s) | Text |
|--------|---------|------|
| `docs/dreams/OODA.md` | 9 | "OODA is a continuous cycle for making decisions under uncertainty" |
| `docs/dreams/OODA.md` | 16 | "**Iterative by design** - Small reversible actions over big risky bets" |
| `docs/dreams/OODA.md` | 108 | "→ Observe: Now need to handle duplicate emails..." (example shows Act returning to Observe) |
| `docs/dreams/OODA.md` | 118 | "→ Observe: User wants tmux + iTerm2 integration..." (second example confirms the same pattern) |
| `docs/dreams/OODA.md` | 146-148 | Anti-pattern "No Iteration": Bad = "Run loop once, assume done"; Good = "Run loop continuously until goal achieved" |

**Semantic validation:** The word "cycle" (line 9) denotes a process that returns to its starting point. "Iterative by design" (line 16) explicitly names iteration as a design principle, not an optional feature. Both code examples (lines 108, 118) use the arrow notation "→ Observe:" to show the loop returning to its first phase after Act. The anti-pattern (lines 146-148) confirms the norm by documenting its violation: running the loop once is explicitly bad.

---

### P3: The cycle repeats until the goal is achieved

```
∀A: Cycle(A) ∧ ¬GoalAchieved → FollowedByObservation(A)
```

**Evidence:**

| Source | Line(s) | Text |
|--------|---------|------|
| `docs/dev/WORKFLOW.md` | 9 | "Repeat this loop after each meaningful result (new evidence, failing test, lint/type error, review feedback)" |
| `docs/dev/WORKFLOW.md` | 35 | "Repeat until acceptance criteria are satisfied" |
| `docs/dreams/OODA.md` | 148 | "**Good:** Run loop continuously until goal achieved" |
| `docs/dreams/OODA.md` | 128 | "**Enabling course correction** - Small actions are easy to undo or adjust" |

**Semantic validation:** WORKFLOW.md uses the word "Repeat" twice — line 9 specifies WHEN to repeat (after each meaningful result) and line 35 specifies WHEN TO STOP (acceptance criteria satisfied). OODA.md line 148 states the good pattern explicitly: "Run loop continuously until goal achieved." The conjunction of cycle continuation (P2) with non-goal-achievement produces the next observation. "Course correction" (line 128) only makes sense if you observe the result of your action — further confirming that observation follows action.

---

## Proof

```
 1.  Assume NonTrivial(A) ∧ ¬GoalAchieved          [Assumption for conditional proof]
 2.  NonTrivial(A)                                   [From 1, conjunction elimination]
 3.  OODA(A)                                         [From 2, P1 — Modus Ponens]
 4.  Cycle(A) ∧ ActThenObserve(A)                    [From 3, P2 — Modus Ponens]
 5.  Cycle(A)                                        [From 4, conjunction elimination]
 6.  ¬GoalAchieved                                   [From 1, conjunction elimination]
 7.  Cycle(A) ∧ ¬GoalAchieved                        [From 5, 6, conjunction introduction]
 8.  FollowedByObservation(A)                        [From 7, P3 — Modus Ponens]
 9.  NonTrivial(A) ∧ ¬GoalAchieved → FollowedByObservation(A)  [From 1–8, conditional proof]
                                                                                         ∎
```

**Inference rules used:**
- Modus Ponens (if P → Q and P, then Q) — steps 3, 4, 8
- Conjunction Elimination (if P ∧ Q, then P; and Q) — steps 2, 5, 6
- Conjunction Introduction (if P and Q, then P ∧ Q) — step 7
- Conditional Proof (assume P, derive Q, conclude P → Q) — step 9

**Complexity:** Minimal. Same core pattern as QBT-001 (Modus Ponens chain) with conjunction handling for the two-part antecedent.

---

## Cross-Document Verification

| Document | Result | Evidence |
|----------|--------|----------|
| `docs/dreams/OODA.md` | PASS | Defines the loop as a "continuous cycle" (line 9), "Iterative by design" (line 16). Examples show Act→Observe transitions (lines 108, 118). Anti-pattern "No Iteration" (lines 146-148) confirms: running once is bad. |
| `docs/dreams/FIELD-GENERAL.md` | PASS | Principle 6 (Control the Tempo, line 105): "Create space before reacting" — implies re-observation between actions. Principle 10 (Precision Over Volume, line 177): "Fewer, better moves" — quality over quantity requires evaluating results between moves. |
| `docs/dev/WORKFLOW.md` | PASS | Line 9: "Repeat this loop after each meaningful result." Line 35: "Repeat until acceptance criteria are satisfied." Line 64: "Apply OODA — For non-trivial decisions, run the loop explicitly." |
| `docs/dev/GIT-WORKFLOW.md` | PASS | The entire Amend vs New Commit structure (lines 19-35) is an iteration pattern: observe the result of your last commit, decide whether to amend or create new. Cleanup Protocol (lines 171-177): "When agent finishes task" = check results, then decide next action. |
| `docs/dreams/DECISION-THEORY.md` | PASS | Probe-to-Commit Ratios (lines 39-53): probing IS iterating — observe, probe, observe result, adjust. Pattern Lock (lines 89-91): failure to re-evaluate = failure to iterate = documented violation. |
| `docs/dreams/STOP-TINKERING.md` | PASS | 2-Week Rule (lines 82-91): "Document the pain → Wait 2 weeks → Re-evaluate." This IS iteration on a longer timescale — observe, wait, re-observe, then decide. Scoring at lines 43-46: the three score ranges (proceed/wait/stop) are iteration outcomes. |
| `docs/identity.md` | PASS | Line 22: "You think in OODA loops" — plural "loops" implies iteration, not a single pass. Line 11: "Small, focused units of behavior" — small units require iteration to achieve larger goals. |
| `docs/rules.md` | PASS | Line 7: "always apply OODA loop" — "always" across decisions implies repeated application, not once. Line 9: "always apply `docs/dreams/STOP-TINKERING.md`" — the tinkering test itself is a re-evaluation checkpoint. |

**Result: 8/8 documents consistent. Zero counterexamples. Proof is SOUND.**

---

## Soundness Assessment

- **Validity:** The proof uses Modus Ponens, Conjunction Elimination/Introduction, and Conditional Proof — all truth-preserving. The logical structure is valid. ✓
- **Premise truth (P1):** QBT-001 is proven. OODA.md and rules.md confirm non-trivial actions enter OODA. True. ✓
- **Premise truth (P2):** OODA.md defines OODA as a "continuous cycle" and shows Act→Observe transitions in examples. Anti-pattern confirms. True. ✓
- **Premise truth (P3):** WORKFLOW.md explicitly says "Repeat" twice with clear termination. OODA.md confirms "continuously until goal achieved." True. ✓

**The proof is sound.**

---

## Humanized Version

> ### Why the Loop Never Stops (Until You're Done)
>
> QBT-001 proved that genius always looks before it leaps. QBT-002 proves something just as important: **after leaping, it looks again.**
>
> OODA isn't a checklist you run once. It's a "continuous cycle for making decisions under uncertainty" (`docs/dreams/OODA.md`, line 9) — "Iterative by design" (line 16). Both code examples in the OODA doc show this explicitly: after acting, the arrow points right back to Observe ("→ Observe: Now need to handle duplicate emails...", line 108).
>
> The development workflow makes it a rule: "Repeat this loop after each meaningful result" (`docs/dev/WORKFLOW.md`, line 9). And it gives you the exit condition: "Repeat until acceptance criteria are satisfied" (line 35). Not until you feel done — until the goal is actually achieved.
>
> Even the anti-patterns confirm it. Running the loop once and assuming you're done? That's explicitly called out as bad practice (`docs/dreams/OODA.md`, lines 146-148). Failing to re-evaluate your approach as conditions change? That's Pattern Lock — a documented cognitive failure mode (`docs/dreams/DECISION-THEORY.md`, lines 89-91).
>
> The logic: non-trivial actions enter the OODA loop (by QBT-001). OODA is a continuous cycle that returns to Observe after Act. The cycle repeats until the goal is achieved. Therefore: if the goal isn't done, observation recurs after every non-trivial action.
>
> Together, QBT-001 and QBT-002 prove that OODA is a true loop — observation before, observation after, and the cycle continues until you're actually finished.

---

## Dependency Interface

Future proofs can import this result:

```
IMPORT: QBT-002 (Iterative Refinement)
STATEMENT: ∀A: NonTrivial(A) ∧ ¬GoalAchieved → FollowedByObservation(A)
SOURCE: docs/proofs/002-ITERATIVE-REFINEMENT.md
USAGE: "By QBT-002, since A is non-trivial and the goal is not yet achieved, observation recurs after A."
```

### Updated Composability Map

```
QBT-001: Observation Precedence [PARENT LEMMA]
  └── QBT-002: Iterative Refinement [THIS PROOF — CHAIN]
        "Observation recurs after action until the goal is achieved"
        ├── QBT-003: (future) Smallest Reversible Action
        │     "Because the loop repeats (QBT-002), each step should be minimal and reversible"
        └── QBT-NNN: (future) Any behavioral property requiring iteration
              "By QBT-002, the system re-observes. Therefore..."
```

---

## Quick Reference Card

```
QBT-002 — ITERATIVE REFINEMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Theorem:  ∀A: NonTrivial(A) ∧ ¬GoalAchieved → FollowedByObservation(A)
English:  After every non-trivial action, if the goal isn't done, observe again.
Scope:    Normative (what the system prescribes)
Method:   Direct proof, 3 premises (imports QBT-001), Modus Ponens chain
Status:   SOUND (8/8 docs verified, 0 counterexamples)
Depends:  QBT-001 (Observation Precedence)

Premises:
  P1: NonTrivial → OODA              (by QBT-001, OODA.md:9)
  P2: OODA → Cycle ∧ ActThenObserve  (OODA.md:9, 16, 108, 146-148)
  P3: Cycle ∧ ¬GoalAchieved → FollowedByObservation  (WORKFLOW.md:9, 35)

Chain: QBT-001 → P1 → P2 → P3 ∎

Cite as: "By QBT-002 (Iterative Refinement), ..."
```
