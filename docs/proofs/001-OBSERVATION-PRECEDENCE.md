<!-- NOTE: References to docs/rules.md are stale. rules.md was deleted 2026-04-05;
     its content was folded into docs/identity.md. TODO: update source citations. -->

# Proof 001: Observation Precedence

**Theorem ID:** QBT-001
**Type:** Foundational Lemma (Parent Proof)
**Status:** Proven
**Date:** 2026-04-04
**Method:** Direct proof via Hypothetical Syllogism (Modus Ponens chain)
**Scope:** Normative — proves what the system prescribes, not what agents always do

---

## Theorem Statement

**Natural language:**
In the quanbot system, every non-trivial action is preceded by observation.

**Formal:**

```
∀A: NonTrivial(A) → PrecededByObservation(A)
```

---

## Definitions

| Symbol | Meaning | Grounding |
|--------|---------|-----------|
| A | Any action taken within the quanbot system | — |
| NonTrivial(A) | A has more than one viable approach, OR A involves uncertainty | `docs/dreams/OODA.md` line 88: "Non-trivial decisions (more than one viable option)" |
| OODA(A) | A is processed through the Observe→Orient→Decide→Act loop | `docs/dreams/OODA.md` lines 7, 99-109 |
| ObserveFirst(A) | The Observe phase executes before Orient, Decide, or Act for A | `docs/dreams/OODA.md` lines 7, 19-28 |
| PrecededByObservation(A) | Before A is executed, explicit observation of facts, signals, and constraints occurred | `docs/dreams/OODA.md` lines 22-28; `docs/dreams/FIELD-GENERAL.md` line 15 |

**Scope boundary:** Only rendered markdown content counts. HTML comments (e.g., `rules.md` lines 11-27) are excluded from the corpus.

**Normative scope:** This proof establishes what the system prescribes. Documented failure modes (e.g., "Rushed Processing" in `docs/dreams/DECISION-THEORY.md` lines 78-85) are violations of the norm, not counterexamples to it.

---

## Premises

### P1: Every non-trivial action runs through OODA

```
∀A: NonTrivial(A) → OODA(A)
```

**Syntactic evidence:**

| Source | Line(s) | Text |
|--------|---------|------|
| `docs/rules.md` | 7 | "When making non-trivial decisions, always apply OODA loop from `docs/dreams/OODA.md`" |
| `docs/identity.md` | 22 | "You think in OODA loops: Observe → Orient → Decide → Act" |
| `docs/dreams/OODA.md` | 88 | "Non-trivial decisions (more than one viable option)" |
| `docs/dev/WORKFLOW.md` | 7 | "Every non-trivial step runs through the OODA loop" |

**Semantic validation:** Four independent documents assert that OODA is mandatory for non-trivial actions. The qualifier "non-trivial" appears identically in the premise and the source text. The word "always" in `rules.md` and the universal quantifier in the formal premise are semantically equivalent. No interpretation gap.

---

### P2: The OODA loop begins with Observe

```
∀A: OODA(A) → ObserveFirst(A)
```

**Syntactic evidence:**

| Source | Line(s) | Text |
|--------|---------|------|
| `docs/dreams/OODA.md` | 7 | "**Observe → Orient → Decide → Act**" |
| `docs/dreams/OODA.md` | 19-28 | Observe section appears first; asks "What changed?", "What new information?", "What are the current constraints?" |
| `docs/dreams/OODA.md` | 140 | Anti-pattern: "Observe problem → immediately decide" (skipping Orient is bad, but Observe still comes first) |
| `docs/dreams/OODA.md` | 152-157 | Integration: "Clarify - OODA to understand the request" (Observe maps to Clarify, the first workflow step) |

**Semantic validation:** The arrow notation `→` denotes sequential ordering. Observe is structurally and semantically FIRST in the sequence. Even the anti-patterns (lines 130-148) assume Observe has already occurred — the errors are about skipping Orient or not iterating, never about skipping Observe. The document structure reinforces this: the Observe section precedes all others.

---

### P3: Executing the Observe phase constitutes prior observation

```
∀A: ObserveFirst(A) → PrecededByObservation(A)
```

**Syntactic evidence:**

| Source | Line(s) | Text |
|--------|---------|------|
| `docs/dreams/OODA.md` | 22-28 | Observe phase: "State the latest facts, signals, and constraints" with questions about changes, new information, and current constraints |
| `docs/dreams/FIELD-GENERAL.md` | 15 | "Default state is observation, not reaction. Let others reveal information through mistakes, timing, and emotion." |
| `docs/dreams/FIELD-GENERAL.md` | 225 | Mantra: "Wait. Watch. Understand. Then act with precision." |

**Semantic validation:** P3 is a definitional bridge — it connects the OODA-specific term "Observe" to the general concept of "observation." This is the weakest premise precisely because it is near-tautological: calling a step named "Observe" an act of observation is almost self-evident. We include it as an explicit premise (rather than leaving it implicit) for two reasons: (1) transparency — all logical steps should be visible, and (2) the Field General framework provides independent confirmation that the system's default state is observation, grounding the bridge in more than just naming. The mantra "Wait. Watch. Understand." (line 225) is a natural-language restatement of "preceded by observation."

---

## Proof

```
 1.  Assume NonTrivial(A)                         [Assumption for conditional proof]
 2.  OODA(A)                                       [From 1, P1 — Modus Ponens]
 3.  ObserveFirst(A)                               [From 2, P2 — Modus Ponens]
 4.  PrecededByObservation(A)                      [From 3, P3 — Modus Ponens]
 5.  NonTrivial(A) → PrecededByObservation(A)      [From 1–4 — Conditional Proof]
                                                                              ∎
```

**Inference rules used:**
- Modus Ponens (if P → Q and P, then Q) — steps 2, 3, 4
- Conditional Proof (assume P, derive Q, conclude P → Q) — step 5
- Universal Instantiation (implicit — applying universal premises to arbitrary A)

**Complexity:** Minimal. Three applications of the simplest inference rule in propositional logic.

---

## Cross-Document Verification

The proven theorem was tested against every document in the corpus:

| Document | Result | Evidence |
|----------|--------|----------|
| `docs/dreams/OODA.md` | PASS | Defines the loop. Observation is phase 1. Anti-patterns (lines 130-148) confirm: skipping observation leads to bad outcomes. |
| `docs/dreams/FIELD-GENERAL.md` | PASS | Principle 1 (Information Before Action) is an independent restatement. Mantra (line 225): "Wait. Watch. Understand. Then act with precision." |
| `docs/dev/WORKFLOW.md` | PASS | Step 1 (Clarify) = observation. "Restate the task... identify unknowns." Imports OODA micro-loop (line 7). |
| `docs/dev/GIT-WORKFLOW.md` | PASS | Decision trees (lines 41-53, 109-119) begin with state observation. Graphite protocol (line 125): "BEFORE any git operation: Check if in worktree." |
| `docs/dreams/DECISION-THEORY.md` | PASS | Probe-to-Commit (lines 39-52): low information → probe more. 3 of 4 failure modes (lines 59-113) involve insufficient observation. "Rushed Processing" (line 78) is a documented VIOLATION, not a counterexample. |
| `docs/dreams/STOP-TINKERING.md` | PASS | Tinkering Test (lines 8-44) forces observation (score 4 questions) before deciding to proceed. Score 0-8 = HARD STOP when observation reveals no problem. |
| `docs/identity.md` | PASS | "You think in OODA loops" (line 22). "You optimize for readability and correctness first" (line 18) — observation-oriented values. |
| `docs/rules.md` | PASS | "When making non-trivial decisions, always apply OODA loop" (line 7). Routes to FIELD-GENERAL and STOP-TINKERING, both of which enforce observation first. |

**Result: 8/8 documents consistent. Zero counterexamples. Proof is SOUND.**

---

## Soundness Assessment

A proof is **sound** when it is valid (conclusion follows from premises) AND all premises are true.

- **Validity:** The proof uses only Modus Ponens and Conditional Proof — both are truth-preserving inference rules. The logical structure is valid. ✓
- **Premise truth (P1):** Four independent docs assert OODA is mandatory for non-trivial actions. True in the corpus. ✓
- **Premise truth (P2):** OODA.md defines the sequence with Observe first. No doc contradicts this. True in the corpus. ✓
- **Premise truth (P3):** OODA's Observe phase is definitionally observation. FIELD-GENERAL independently confirms. True in the corpus. ✓

**The proof is sound.**

---

## Humanized Version

> ### Why Observation Comes First for Non-Trivial Actions
>
> When quanbot faces a non-trivial decision — one with more than one viable approach or genuine uncertainty (`docs/dreams/OODA.md`, line 88) — one principle surfaces across every framework: **look before you leap.**
>
> The system's rules are explicit. Non-trivial decisions must run through the OODA loop (`docs/rules.md`, line 7). The OODA loop always starts with Observe — state the facts, identify what changed, understand the constraints (`docs/dreams/OODA.md`, lines 7, 19-28). And observation, by definition, means you've looked at the situation before doing anything about it.
>
> This isn't just a process quirk. The Field General framework makes it Principle Number One: "Default state is observation, not reaction" (`docs/dreams/FIELD-GENERAL.md`, line 15). The development workflow starts with Clarify — which is observation applied to task execution (`docs/dev/WORKFLOW.md`, lines 15-18). Even the Tinkering Test forces you to answer four observational questions before you're allowed to touch anything (`docs/dreams/STOP-TINKERING.md`, lines 8-44).
>
> The logic is simple: non-trivial action requires OODA. OODA starts with Observe. Observe IS observation. Therefore: non-trivial action is always preceded by observation.
>
> Three steps. One conclusion. This is the normative foundation — what the system prescribes for every non-trivial action. When agents skip observation (as documented in "Rushed Processing," `docs/dreams/DECISION-THEORY.md`, line 78), that is a violation of this norm, not a disproof of it.
>
> This is the foundational claim of the entire system — and every other proof about quanbot's behavior will build on it.

---

## Dependency Interface

Future proofs can import this result using the following convention:

```
IMPORT: QBT-001 (Observation Precedence)
STATEMENT: ∀A: NonTrivial(A) → PrecededByObservation(A)
SOURCE: docs/proofs/001-OBSERVATION-PRECEDENCE.md
USAGE: "By QBT-001, since A is non-trivial, A was preceded by observation."
```

### Composability Map

```
QBT-001: Observation Precedence [THIS PROOF — PARENT LEMMA]
  ├── QBT-002: (future) Workflow Correctness
  │     "If observation precedes action, then Clarify→Plan→Execute is sound"
  ├── QBT-003: (future) Decision Quality
  │     "If observation precedes action, then probe-before-commit follows"
  ├── QBT-004: (future) Strategic Patience
  │     "If observation precedes action, then information-before-action holds"
  └── QBT-NNN: (future) Any behavioral property
        "By QBT-001, observation occurred. Therefore..."
```

### Recursive Proofing

A **proof chain** is a sequence where the conclusion of proof N becomes a premise of proof N+1. A **proof collection** is a set of proofs whose conclusions are conjoined to form a compound premise. Both patterns are supported by the dependency interface above.

---

## Verification

Run `docs/proofs/verify-proof.sh` to check that all premises still hold in the current doc corpus. See that file for details.

---

## Quick Reference Card

```
QBT-001 — OBSERVATION PRECEDENCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Theorem:  ∀A: NonTrivial(A) → PrecededByObservation(A)
English:  Every non-trivial action is preceded by observation.
Scope:    Normative (what the system prescribes)
Method:   Direct proof, 3 premises, Modus Ponens chain
Status:   SOUND (8/8 docs verified, 0 counterexamples)

Premises:
  P1: NonTrivial → OODA        (rules.md:7, OODA.md:88)
  P2: OODA → ObserveFirst      (OODA.md:7, 19-28)
  P3: ObserveFirst → Observed   (OODA.md:22-28, FIELD-GENERAL.md:15)

Chain: P1 → P2 → P3 ∎

Cite as: "By QBT-001 (Observation Precedence), ..."
```
