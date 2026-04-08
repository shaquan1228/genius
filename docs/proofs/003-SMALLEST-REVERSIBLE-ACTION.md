<!-- NOTE: References to docs/rules.md are stale. rules.md was deleted 2026-04-05;
     its content was folded into docs/identity.md. TODO: update source citations. -->

# Proof 003: Smallest Reversible Action

**Theorem ID:** QBT-003
**Type:** Chain Proof (depends on QBT-001, QBT-002)
**Status:** Proven
**Date:** 2026-04-05
**Method:** Direct proof via Modus Ponens chain (imports QBT-001, QBT-002)
**Scope:** Normative — proves what the system prescribes, not what agents always do

---

## Theorem Statement

**Natural language:**
In the quanbot system, every non-trivial action within an active OODA loop is the smallest reversible step that moves toward the goal.

**Formal:**

```
∀A: NonTrivial(A) ∧ ¬GoalAchieved → SmallestReversible(A)
```

**Combined with QBT-001 + QBT-002:** Observation before (QBT-001) + observation after (QBT-002) + smallest reversible step (QBT-003) = the complete loop contract. The system observes, takes a minimal step, observes again, and repeats.

---

## Definitions

| Symbol | Meaning | Grounding |
|--------|---------|-----------|
| NonTrivial(A) | Inherited from QBT-001 | `docs/dreams/OODA.md` line 88 |
| GoalAchieved | Inherited from QBT-002 | `docs/dreams/OODA.md` line 148 |
| InOODALoop(A) | A is being processed within an active, iterating OODA cycle | By QBT-001 + QBT-002: non-trivial actions enter OODA and iterate |
| DecidePhase(A) | A passes through the Decide phase of the OODA loop | `docs/dreams/OODA.md` lines 52-66 |
| SmallestStep(A) | A is the smallest action that could move toward the goal or resolve uncertainty | `docs/dreams/OODA.md` line 54: "Choose the next smallest reversible action"; line 58: "What's the smallest thing I can do to learn more?" |
| Reversible(A) | A can be undone or adjusted without cascading damage | `docs/dreams/OODA.md` line 59: "Is this action reversible?"; line 16: "Small reversible actions over big risky bets" |
| SmallestReversible(A) | SmallestStep(A) ∧ Reversible(A) — the action is both minimal in scope and undoable | Conjunction of the two properties above |

**Scope boundary:** Same as QBT-001 — only rendered markdown content. HTML comments excluded.

**Normative scope:** The "Loop Too Big" anti-pattern (`docs/dreams/OODA.md` lines 132-136) is a documented violation, not a counterexample.

---

## Dependencies

```
IMPORT: QBT-001 (Observation Precedence)
STATEMENT: ∀A: NonTrivial(A) → PrecededByObservation(A)
SOURCE: docs/proofs/001-OBSERVATION-PRECEDENCE.md

IMPORT: QBT-002 (Iterative Refinement)
STATEMENT: ∀A: NonTrivial(A) ∧ ¬GoalAchieved → FollowedByObservation(A)
SOURCE: docs/proofs/002-ITERATIVE-REFINEMENT.md
```

QBT-001 establishes that non-trivial actions enter the OODA loop. QBT-002 establishes that the loop iterates. Together they place A within an active, iterating cycle — the context in which the Decide phase constrains step size.

---

## Premises

### P1: Non-trivial actions in an active loop pass through the Decide phase

```
∀A: InOODALoop(A) → DecidePhase(A)
```

**Evidence:**

| Source | Line(s) | Text |
|--------|---------|------|
| `docs/dreams/OODA.md` | 7 | "**Observe → Orient → Decide → Act**" — Decide is a mandatory phase in the sequence |
| `docs/dreams/OODA.md` | 52-66 | Decide section: "Choose the next smallest reversible action" with three guiding questions and three examples |
| `docs/dreams/OODA.md` | 152-157 | Integration: OODA maps to workflow steps — Decide maps to the execution choice |

**Semantic validation:** OODA is a four-phase sequence. QBT-001 and QBT-002 proved that non-trivial actions enter this sequence and iterate within it. If A is in the loop, it passes through all four phases — including Decide. No document describes a path that skips Decide.

---

### P2: The Decide phase selects the smallest reversible action

```
∀A: DecidePhase(A) → SmallestStep(A) ∧ Reversible(A)
```

**Evidence:**

| Source | Line(s) | Text |
|--------|---------|------|
| `docs/dreams/OODA.md` | 54 | "Choose the next smallest reversible action." |
| `docs/dreams/OODA.md` | 58 | "What's the smallest thing I can do to learn more?" |
| `docs/dreams/OODA.md` | 59 | "Is this action reversible?" |
| `docs/dreams/OODA.md` | 16 | "**Iterative by design** - Small reversible actions over big risky bets" |
| `docs/dreams/OODA.md` | 126 | "**Forcing small steps** - Prevents overwhelm from trying to solve everything at once" |
| `docs/dreams/OODA.md` | 128 | "**Enabling course correction** - Small actions are easy to undo or adjust" |

**Semantic validation:** The Decide phase heading (line 54) uses the exact phrase "smallest reversible action" — this is prescriptive, not suggestive ("Choose," not "Consider"). The three guiding questions (lines 58-60) operationalize both properties: smallest ("smallest thing I can do") and reversible ("Is this action reversible?"). The design principle (line 16) frames this as the system's explicit preference: small reversible actions OVER big risky bets. The cognitive load section (lines 126, 128) provides the rationale: small steps prevent overwhelm and enable course correction.

---

### P3: Smallest reversible actions preserve the loop's ability to course-correct

```
∀A: SmallestStep(A) ∧ Reversible(A) → SmallestReversible(A)
```

**Evidence:**

| Source | Line(s) | Text |
|--------|---------|------|
| `docs/dreams/OODA.md` | 128 | "**Enabling course correction** - Small actions are easy to undo or adjust" |
| `docs/dreams/OODA.md` | 132-136 | Anti-pattern "Loop Too Big": Bad = "decide on complete refactor, act on 50 files"; Good = "decide on one change, act on one file" |
| `docs/dreams/OODA.md` | 60 | "Does this move me toward my goal?" — the action must be goal-directed, not just small |
| `docs/dev/WORKFLOW.md` | 15 | "Break work into the smallest code deliverable" |
| `docs/identity.md` | 6 | "You favor practical decisions that ship incremental value quickly" |
| `docs/identity.md` | 12 | "Small, focused units of behavior" |
| `docs/dreams/FIELD-GENERAL.md` | 177 | Principle 10: "Quality decisions beat sheer activity. Fewer, better moves dominate outcomes." |
| `docs/dreams/DECISION-THEORY.md` | 45-47 | Probe-to-Commit: "Low information: Probe more, commit less" — probes are small reversible actions by design |

**Semantic validation:** P3 is a definitional conjunction — SmallestReversible(A) is defined as SmallestStep(A) ∧ Reversible(A). We include it as an explicit premise (rather than leaving it implicit) for the same reason as QBT-001's P3: transparency. But the evidence goes beyond definition. The "Loop Too Big" anti-pattern (lines 132-136) shows what happens when actions are NOT smallest-reversible: the loop breaks down. WORKFLOW.md independently prescribes "smallest code deliverable." Identity.md prescribes "small, focused units of behavior" and "incremental value." FIELD-GENERAL's Precision Over Volume confirms: fewer, better moves. DECISION-THEORY's Probe-to-Commit ratio confirms: under uncertainty (which is the precondition for non-triviality), prefer small exploratory actions.

---

## Proof

```
 1.  Assume NonTrivial(A) ∧ ¬GoalAchieved          [Assumption for conditional proof]
 2.  NonTrivial(A)                                   [From 1, conjunction elimination]
 3.  ¬GoalAchieved                                   [From 1, conjunction elimination]
 4.  PrecededByObservation(A)                        [From 2, QBT-001 — the action is in OODA]
 5.  FollowedByObservation(A)                        [From 1, QBT-002 — the loop iterates]
 6.  InOODALoop(A)                                   [From 4, 5 — A is in an active, iterating loop]
 7.  DecidePhase(A)                                  [From 6, P1 — Modus Ponens]
 8.  SmallestStep(A) ∧ Reversible(A)                 [From 7, P2 — Modus Ponens]
 9.  SmallestReversible(A)                           [From 8, P3 — Modus Ponens]
10.  NonTrivial(A) ∧ ¬GoalAchieved → SmallestReversible(A)  [From 1–9, conditional proof]
                                                                                        ∎
```

**Inference rules used:**

- Modus Ponens (if P → Q and P, then Q) — steps 7, 8, 9
- Conjunction Elimination (if P ∧ Q, then P; and Q) — steps 2, 3
- Conjunction Introduction (if P and Q, then P ∧ Q) — step 6 (implicit from 4, 5)
- Conditional Proof (assume P, derive Q, conclude P → Q) — step 10
- Import (QBT-001, QBT-002) — steps 4, 5

**Complexity:** Minimal. Same core pattern as QBT-001/002 with dependency imports.

---

## Cross-Document Verification

| Document | Result | Evidence |
|----------|--------|----------|
| `docs/dreams/OODA.md` | PASS | Decide phase (line 54): "Choose the next smallest reversible action." Design principle (line 16): "Small reversible actions over big risky bets." Cognitive load (lines 126, 128): small steps prevent overwhelm, enable course correction. Anti-pattern "Loop Too Big" (lines 132-136): acting on 50 files = violation. |
| `docs/dreams/FIELD-GENERAL.md` | PASS | Principle 2 (Asymmetric Pressure, line 33): apply force selectively, not broadly — precision implies minimal scope. Principle 10 (Precision Over Volume, line 177): fewer, better moves. Mantra (line 225): "act with precision" — precision is the opposite of large, sweeping action. |
| `docs/dev/WORKFLOW.md` | PASS | Line 15: "Break work into the smallest code deliverable." Line 16: "Verify after each change" — small changes enable per-change verification. |
| `docs/dev/GIT-WORKFLOW.md` | PASS | Line 14: "Prefer amend. New commit only when crossing a logical boundary" — amend is the reversible default; new commit only at logical boundaries. Line 15: "Commit early, commit often" — frequent small commits over infrequent large ones. |
| `docs/dreams/DECISION-THEORY.md` | PASS | Probe-to-Commit (lines 45-47): low information → probe more. Probes are small, reversible information-gathering actions. The ratio framework assumes actions can be sized — smallest-reversible is the sizing principle. |
| `docs/dreams/STOP-TINKERING.md` | PASS | The Tinkering Test (lines 8-44) gates whether to act at all. Once the gate passes, the implicit question is "how much?" — QBT-003 answers: the smallest reversible amount. Score 0-8 = HARD STOP is the ultimate constraint on action size: zero. |
| `docs/identity.md` | PASS | Line 6: "practical decisions that ship incremental value quickly" — incremental = small steps. Line 12: "Small, focused units of behavior." Line 17: "You optimize for low cognitive load" — small steps reduce cognitive load (OODA.md line 126). |
| `docs/rules.md` | PASS | Line 7: routes to OODA (which prescribes smallest reversible action in Decide). Line 9: routes to STOP-TINKERING (which gates action). Both frameworks converge on minimal action. |

**Result: 8/8 documents consistent. Zero counterexamples. Proof is SOUND.**

---

## Soundness Assessment

- **Validity:** The proof uses Modus Ponens, Conjunction Elimination/Introduction, Conditional Proof, and Import — all truth-preserving. The logical structure is valid. ✓
- **Premise truth (P1):** OODA defines four mandatory phases including Decide. If A is in the loop, it passes through Decide. True. ✓
- **Premise truth (P2):** OODA.md line 54 prescribes "smallest reversible action" in the Decide phase heading. Lines 58-59 operationalize both properties. Line 16 frames it as a design principle. True. ✓
- **Premise truth (P3):** Definitional conjunction confirmed by independent evidence from OODA.md, WORKFLOW.md, identity.md, and FIELD-GENERAL.md. True. ✓

**The proof is sound.**

---

## Humanized Version

> ### Why Every Step Should Be Small and Reversible
>
> QBT-001 proved you look before you leap. QBT-002 proved you look again after landing. QBT-003 proves what the leap itself should look like: **the smallest reversible step that moves toward the goal.**
>
> This isn't a style preference — it's structural. The OODA Decide phase doesn't say "choose an action." It says "choose the next smallest reversible action" (`docs/dreams/OODA.md`, line 54). The guiding questions make it explicit: "What's the smallest thing I can do to learn more?" and "Is this action reversible?" (lines 58-59). The design principle elevates this to a first-class value: "Small reversible actions over big risky bets" (line 16).
>
> And the reasoning is mechanical, not philosophical. Because the loop repeats (QBT-002), each step will be followed by re-observation. Large irreversible actions break this contract — you can't course-correct what you can't undo, and you can't observe meaningfully when 50 files changed at once. The "Loop Too Big" anti-pattern (lines 132-136) documents exactly this failure: acting on 50 files instead of one.
>
> Every other framework converges on the same point. WORKFLOW.md says "Break work into the smallest code deliverable" (line 15). Identity.md says "Small, focused units of behavior" (line 12). FIELD-GENERAL's Principle 10 says "Fewer, better moves dominate outcomes" (line 177). DECISION-THEORY's Probe-to-Commit says under uncertainty, probe more — and probes are small by definition (lines 45-47).
>
> The logic: non-trivial actions enter the iterating OODA loop (by QBT-001 + QBT-002). The loop's Decide phase selects the smallest reversible action. Therefore: every non-trivial action in an active loop is the smallest reversible step toward the goal.
>
> Together, QBT-001 + QBT-002 + QBT-003 form the complete loop contract: **observe, take the smallest reversible step, observe again, repeat until done.**

---

## Dependency Interface

Future proofs can import this result:

```
IMPORT: QBT-003 (Smallest Reversible Action)
STATEMENT: ∀A: NonTrivial(A) ∧ ¬GoalAchieved → SmallestReversible(A)
SOURCE: docs/proofs/003-SMALLEST-REVERSIBLE-ACTION.md
USAGE: "By QBT-003, since A is non-trivial and the goal is not yet achieved, A is the smallest reversible step."
```

### Updated Composability Map

```
QBT-001: Observation Precedence [PARENT LEMMA]
  └── QBT-002: Iterative Refinement [CHAIN]
        ├── QBT-003: Smallest Reversible Action [THIS PROOF — CHAIN]
        │     "Each step in the loop is minimal and reversible"
        └── QBT-004: Fork-Loaded Iteration [CHAIN]
              "Iteration is justified iff it loads a fork's spring"
```

---

## Quick Reference Card

```
QBT-003 — SMALLEST REVERSIBLE ACTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Theorem:  ∀A: NonTrivial(A) ∧ ¬GoalAchieved → SmallestReversible(A)
English:  Every non-trivial action in an active loop is the smallest reversible step.
Scope:    Normative (what the system prescribes)
Method:   Direct proof, 3 premises (imports QBT-001, QBT-002), Modus Ponens chain
Status:   SOUND (8/8 docs verified, 0 counterexamples)
Depends:  QBT-001 (Observation Precedence), QBT-002 (Iterative Refinement)

Premises:
  P1: InOODALoop → DecidePhase           (OODA.md:7, 52-66)
  P2: DecidePhase → Smallest ∧ Reversible (OODA.md:54, 58-59, 16)
  P3: Smallest ∧ Reversible → SmallestReversible  (OODA.md:128, 132-136; WORKFLOW.md:15)

Chain: QBT-001 + QBT-002 → P1 → P2 → P3 ∎

Cite as: "By QBT-003 (Smallest Reversible Action), ..."
```
