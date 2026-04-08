# Proof 004: Independent Premise Validation

**Theorem ID:** QBT-004
**Type:** Chain Proof (depends on QBT-001, QBT-002, QBT-003)
**Status:** Proven
**Date:** 2026-04-06
**Method:** Direct proof via Modus Ponens chain (imports QBT-001)
**Scope:** Normative — proves what the system prescribes, not what agents always do

---

## Theorem Statement

**Natural language:**
In the quanbot system, every non-trivial action that depends on a premise requires independent validation of that premise. Derivation is not validation. Direction is not validation. Only direct evidence is validation.

**Formal:**

```
∀A: NonTrivial(A) ∧ DependsOn(A, P) → ValidatedIndependently(P)
```

**Combined with QBT-001 + QBT-002 + QBT-003:** The complete loop contract is now: observe (QBT-001), validate your premises independently (QBT-004), take the smallest reversible step (QBT-003), observe again (QBT-002), repeat.

---

## Definitions

| Symbol | Meaning | Grounding |
|--------|---------|-----------|
| NonTrivial(A) | Inherited from QBT-001 | `docs/dreams/OODA.md` line 88 |
| DependsOn(A, P) | Action A's correctness requires premise P to be true. If P is false, A is unsound regardless of A's internal logic. | General logical dependency |
| Assumption(P) | P is accepted without direct evidence — either derived from a chain of reasoning, or asserted by an authority/rule | `docs/dreams/FIELD-GENERAL.md` line 17: "What do I know vs. what am I assuming?" — the question distinguishes knowledge from assumption |
| ValidatedIndependently(P) | P was confirmed through direct evidence or direct testing — not through the reasoning chain that produced it, and not because an authority directed its acceptance | `docs/dreams/OODA.md` line 72: "Did my action produce the expected result?"; `docs/dev/WORKFLOW.md` line 16: "Verify after each change, not at the end" |
| Cascade(A, P) | When P is false and A depends on P, A's output becomes a false premise for subsequent actions, propagating the error through the inference chain | `docs/dreams/OODA.md` lines 132-136: "Loop Too Big" anti-pattern; `docs/dreams/DECISION-THEORY.md` lines 76-85: "Rushed Processing" compounds avoidable errors |

**Scope boundary:** Same as QBT-001 — only rendered markdown content. HTML comments excluded.

**Normative scope:** "Rushed Processing" (`docs/dreams/DECISION-THEORY.md` lines 76-85) — skipping Orient and jumping to action — is a documented violation of this norm, not a counterexample.

---

## Dependencies

```
IMPORT: QBT-001 (Observation Precedence)
STATEMENT: ∀A: NonTrivial(A) → PrecededByObservation(A)
SOURCE: docs/proofs/001-OBSERVATION-PRECEDENCE.md
```

QBT-001 guarantees observation occurs. QBT-004 constrains what observation must include: not just reading state, but independently validating premises before building on them.

---

## Premises

### P1: Observation distinguishes what is known from what is assumed

```
∀A: PrecededByObservation(A) → DistinguishesKnownFromAssumed(A)
```

**Syntactic evidence:**

| Source | Line(s) | Text |
|--------|---------|------|
| `docs/dreams/FIELD-GENERAL.md` | 17 | "What do I know vs. what am I assuming?" |
| `docs/dreams/FIELD-GENERAL.md` | 18 | "Who has revealed their position, and who hasn't?" |
| `docs/dreams/OODA.md` | 40 | Orient: "Name the governing pattern, risks, and tradeoffs for this step." |
| `docs/dreams/OODA.md` | 44 | "What are the risks if I proceed?" |
| `docs/dreams/DECISION-THEORY.md` | 45 | "Low information: Probe more, commit less. You're still learning the landscape." |

**Semantic validation:** FIELD-GENERAL Principle 1 explicitly asks the agent to separate knowledge from assumption. This is not a suggestion — it's the first of ten principles, and it opens with "Default state is observation, not reaction" (line 14). The Orient phase of OODA reinforces this: naming risks (line 44) requires knowing which inputs are verified and which are not. DECISION-THEORY's Probe-to-Commit ratio (line 45) further confirms: when information is uncertain, the system prescribes exploration (probing) over commitment. All three frameworks converge: the system must distinguish what it knows from what it assumes.

---

### P2: An unvalidated assumption used as a premise cascades uncertainty to all dependent actions

```
∀A, P: DependsOn(A, P) ∧ Assumption(P) → InheritsUncertainty(A) ∧ Cascade(A, P)
```

**Syntactic evidence:**

| Source | Line(s) | Text |
|--------|---------|------|
| `docs/dreams/OODA.md` | 132-136 | Anti-pattern "Loop Too Big": Bad = "decide on complete refactor, act on 50 files"; Good = "decide on one change, act on one file" |
| `docs/dreams/OODA.md` | 128 | "**Enabling course correction** - Small actions are easy to undo or adjust" |
| `docs/dreams/DECISION-THEORY.md` | 76-85 | Rushed Processing: "Skipping the 'Orient' step in OODA and jumping straight from observation to action" leads to "avoidable errors" |
| `docs/dreams/DECISION-THEORY.md` | 47 | "Uncertain information: Mix probes and commits. Each probe should be designed to resolve a specific uncertainty." |
| `docs/dreams/FIELD-GENERAL.md` | 55 | "Am I overweighting a rare scenario because it's vivid?" — signals can mislead |
| `docs/dreams/FIELD-GENERAL.md` | 177 | "Quality decisions beat sheer activity. Fewer, better moves dominate outcomes." |

**Semantic validation:** The "Loop Too Big" anti-pattern (lines 132-136) illustrates cascading at the action level: acting on 50 files means 50 actions all depend on the same initial decision. If that decision is wrong, all 50 actions are wrong. The anti-pattern exists because cascading is the failure mode of large, unchecked chains. Rushed Processing (DECISION-THEORY lines 76-85) describes the same phenomenon at the reasoning level: skipping Orient means skipping the step where assumptions would be identified and questioned, so unvalidated assumptions propagate unchecked. The course correction principle (line 128) provides the rationale from the other direction: small steps enable correction precisely because they limit the cascade radius.

---

### P3: Independent validation converts assumptions to knowledge, breaking the cascade

```
∀P: ValidatedIndependently(P) → Known(P) ∧ ¬Cascade(_, P)
```

**Syntactic evidence:**

| Source | Line(s) | Text |
|--------|---------|------|
| `docs/dreams/OODA.md` | 72 | Act: "Did my action produce the expected result?" |
| `docs/dreams/OODA.md` | 73 | "What did I learn?" |
| `docs/dreams/OODA.md` | 74 | "What's the new state?" |
| `docs/dev/WORKFLOW.md` | 16 | "Verify after each change, not at the end" |
| `docs/dreams/FIELD-GENERAL.md` | 17 | "What do I know vs. what am I assuming?" |
| `docs/dreams/FIELD-GENERAL.md` | 225 | "Wait. Watch. Understand. Then act with precision." |

**Semantic validation:** The OODA Act phase (lines 72-74) asks three questions — and critically, the first is "Did my action produce the expected result?" This is independent validation: checking the output against an expectation, not against the logic chain that produced the output. If the only check were "does my conclusion follow from my premises?", a wrong premise would produce a wrong-but-logically-consistent conclusion that passes review. The Act phase demands checking against EXPECTED results — an external reference point, not an internal one. WORKFLOW.md's "Verify after each change, not at the end" (line 16) is the operational prescription: validate at each step, so that a false premise is caught at step 1 instead of propagating to step N. The Field General mantra (line 225) sequences the entire cycle: "Wait. Watch. **Understand.** Then act" — understanding requires validation, not just observation.

**The critical distinction:** Derivation asks "does this follow from my premises?" — internal consistency. Independent validation asks "are my premises actually true?" — external correctness. A chain can be internally consistent and externally wrong. Only independent validation catches this.

---

## Proof

```
 1.  Assume NonTrivial(A) ∧ DependsOn(A, P)         [Assumption for conditional proof]
 2.  NonTrivial(A)                                    [From 1, conjunction elimination]
 3.  PrecededByObservation(A)                         [From 2, QBT-001 — Modus Ponens]
 4.  DistinguishesKnownFromAssumed(A)                 [From 3, P1 — Modus Ponens]
 5.  DependsOn(A, P)                                  [From 1, conjunction elimination]
 6.  P is either Known(P) or Assumption(P)            [From 4 — observation classifies P]
 7.  If Assumption(P): Cascade(A, P)                  [From 5, 6, P2 — Modus Ponens]
 8.  ValidatedIndependently(P) → Known(P)             [From P3]
 9.  Known(P) → ¬Cascade(_, P)                        [From P3]
10.  To prevent cascade: ValidatedIndependently(P)     [From 7, 8, 9 — only path to ¬Cascade]
11.  ValidatedIndependently(P)                         [From 10 — normative: the system prescribes prevention]
12.  NonTrivial(A) ∧ DependsOn(A, P) → ValidatedIndependently(P)  [From 1–11, conditional proof]
                                                                                          ∎
```

**Inference rules used:**

- Modus Ponens (if P → Q and P, then Q) — steps 3, 4, 7, 8, 9
- Conjunction Elimination (if P ∧ Q, then P; and Q) — steps 2, 5
- Disjunction (P is Known or Assumed) — step 6
- Normative closure (the system prescribes cascade prevention, so it prescribes the only means) — steps 10, 11
- Conditional Proof (assume P, derive Q, conclude P → Q) — step 12
- Import (QBT-001) — step 3

**Note on step 10-11 (normative closure):** This step is not purely mechanical — it relies on the normative character of the quanbot system. The system prescribes small reversible actions (QBT-003) to enable course correction, which exists to prevent cascading errors. If the system prescribes cascade prevention (evidenced by QBT-003, "Loop Too Big" anti-pattern, "Verify after each change"), it must prescribe the necessary means: independent validation of premises. A system that prescribes the end but not the means is incoherent. Since quanbot is coherent (8/8 documents verified in QBT-001/002/003), it prescribes independent validation.

---

## Cross-Document Verification

| Document | Result | Evidence |
|----------|--------|----------|
| `docs/dreams/OODA.md` | PASS | Orient (line 40): "Name the governing pattern, risks, and tradeoffs" — risk assessment requires distinguishing validated from assumed. Act (line 72): "Did my action produce the expected result?" — independent check against expectation, not chain logic. Anti-pattern "Loop Too Big" (lines 132-136): cascading from unchecked premises. |
| `docs/dreams/FIELD-GENERAL.md` | PASS | Principle 1 (line 17): "What do I know vs. what am I assuming?" — the foundational question. Principle 3 (line 55): "Am I overweighting a rare scenario because it's vivid?" — unvalidated assumptions can be vivid but wrong. Principle 10 (line 177): "Quality decisions beat sheer activity" — validation is quality; building on assumptions is activity. |
| `docs/dev/WORKFLOW.md` | PASS | Line 16: "Verify after each change, not at the end" — per-step validation prevents cascade. This is independent validation applied operationally. |
| `docs/dev/GIT-WORKFLOW.md` | PASS | Decision trees (lines 41-53) begin with state observation and verification. The git workflow's emphasis on checking state before acting is independent validation applied to version control. |
| `docs/dreams/DECISION-THEORY.md` | PASS | Probe-to-Commit (lines 45-47): under uncertainty, probe (validate) before committing. "Each probe should be designed to resolve a specific uncertainty" (line 47) — probes ARE independent validation of assumptions. Rushed Processing (lines 76-85): skipping validation leads to compounding errors. |
| `docs/dreams/STOP-TINKERING.md` | PASS | Tinkering Test (lines 8-44): four questions that force you to validate your premise ("Can you describe the problem in one sentence?", "Are you actually blocked?"). Score 0-8 = HARD STOP when the premise for action doesn't survive validation. The test IS independent validation of "should I do this?" |
| `docs/identity.md` | PASS | Line 8: "Observe before acting" (QBT-001 — precondition for QBT-004). Line 9: "Verify after each change" (operational form of independent validation). Line 14: "Plan for failure paths explicitly" — failure paths include the case where your premise is wrong. |

**Result: 7/7 documents consistent. Zero counterexamples. Proof is SOUND.**

---

## Soundness Assessment

- **Validity:** The proof uses Modus Ponens, Conjunction Elimination, Disjunction, Normative Closure, and Conditional Proof — all truth-preserving in a normative system. The logical structure is valid. ✓
- **Premise truth (P1):** FIELD-GENERAL Principle 1 explicitly asks "What do I know vs. what am I assuming?" OODA Orient names risks and tradeoffs. DECISION-THEORY prescribes probing under uncertainty. True in the corpus. ✓
- **Premise truth (P2):** "Loop Too Big" anti-pattern shows cascading at the action level. Rushed Processing shows it at the reasoning level. Course correction (line 128) exists to limit cascade radius. True in the corpus. ✓
- **Premise truth (P3):** OODA Act checks against expected results (external). WORKFLOW prescribes per-step verification. FIELD-GENERAL distinguishes knowing from assuming. True in the corpus. ✓

**The proof is sound.**

---

## Humanized Version

> ### Why You Leap Because You Knew, Not Because You Were Told
>
> QBT-001 proved you look before you leap. QBT-002 proved you look again after. QBT-003 proved your leaps are small. QBT-004 proves something the others assumed but never stated: **why you leap at all.**
>
> You don't leap because a rule told you to. You don't leap because the logic chain looks clean. You leap because you independently validated the thing you're about to build on.
>
> This matters because of how errors compound. A chain of reasoning can be perfectly valid — each step follows logically from the previous one — and still be completely wrong. If the first link is false, every subsequent link inherits that falseness. Formal logic has a name for this: *ex falso quodlibet* — from falsehood, anything follows. A proof from a false premise can "prove" anything, including that working code is dead and should be deleted.
>
> The existing quanbot frameworks already point at this truth. FIELD-GENERAL's first question is "What do I know vs. what am I assuming?" (`docs/dreams/FIELD-GENERAL.md`, line 17). OODA's Act phase asks "Did my action produce the expected result?" (`docs/dreams/OODA.md`, line 72) — not "does my conclusion follow from my premises?" The difference is everything. Derivation checks internal consistency. Validation checks external correctness. A system can be internally consistent and externally catastrophic.
>
> The prescription is simple: before you build on a premise, validate it yourself. Don't inherit trust from the chain that produced it. Don't accept it because an authority — a prompt rule, a senior engineer, a "best practice" — told you it was correct. Trace the chain to its root and check the root directly. If the root survives independent scrutiny, build. If it doesn't, stop — because everything downstream is already wrong, you just haven't discovered it yet.
>
> The three earlier proofs tell you WHEN to observe, WHEN to re-observe, and HOW to act. QBT-004 tells you WHY: because unvalidated assumptions compound silently through inference chains, and the only defense is to validate the premise, not just the derivation.

---

## Dependency Interface

Future proofs can import this result:

```
IMPORT: QBT-004 (Independent Premise Validation)
STATEMENT: ∀A: NonTrivial(A) ∧ DependsOn(A, P) → ValidatedIndependently(P)
SOURCE: docs/proofs/004-INDEPENDENT-PREMISE-VALIDATION.md
USAGE: "By QBT-004, since A is non-trivial and depends on P, P must be independently validated."
```

### Updated Composability Map

```
QBT-001: Observation Precedence [PARENT LEMMA]
  ├── QBT-002: Iterative Refinement [CHAIN]
  │     └── QBT-003: Smallest Reversible Action [CHAIN]
  └── QBT-004: Independent Premise Validation [THIS PROOF — CHAIN]
        "Premises must be independently validated, not just derived or directed"
        ├── QBT-005: (future) Loop Completeness
        │     "QBT-001 + QBT-002 + QBT-003 + QBT-004 = the full behavioral contract"
        └── QBT-NNN: (future) Any property requiring premise integrity
              "By QBT-004, the premise was independently validated. Therefore..."
```

---

## Quick Reference Card

```
QBT-004 — INDEPENDENT PREMISE VALIDATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Theorem:  ∀A: NonTrivial(A) ∧ DependsOn(A, P) → ValidatedIndependently(P)
English:  Don't leap because you were told to. Leap because you knew it was right.
Scope:    Normative (what the system prescribes)
Method:   Direct proof, 3 premises (imports QBT-001), Modus Ponens + normative closure
Status:   SOUND (7/7 docs verified, 0 counterexamples)
Depends:  QBT-001 (Observation Precedence)

Premises:
  P1: Observation → DistinguishesKnownFromAssumed  (FIELD-GENERAL:17, OODA:40)
  P2: DependsOn(A,P) ∧ Assumption(P) → Cascade     (OODA:132-136, DECISION-THEORY:76-85)
  P3: ValidatedIndependently(P) → Known(P) ∧ ¬Cascade  (OODA:72, WORKFLOW:16)

Chain: QBT-001 → P1 → P2 → P3 ∎

Cite as: "By QBT-004 (Independent Premise Validation), ..."
```
