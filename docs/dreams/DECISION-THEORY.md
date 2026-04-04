# Decision Theory

Frameworks for reasoning under uncertainty. Reference material for the Field General operating system (`docs/dreams/FIELD-GENERAL.md`).

---

## Core Concepts

### Indifference Principle

When your counterpart is equally comfortable choosing either option, you've found the equilibrium. At that point, neither side can gain by switching strategies unilaterally.

**In practice:**

- In negotiations: if the other party is genuinely indifferent between your offer and walking away, you've priced it correctly
- In technical debates: if a colleague can't decide between two approaches, the tradeoffs are probably balanced — pick whichever you can ship faster
- In pricing: if customers neither jump at the deal nor walk away, you're near the equilibrium price

**Key insight:** Equilibrium is a baseline — real advantage comes from recognizing when others deviate from it.

---

### Equilibrium Strategies

A balanced approach that can't be exploited by someone who knows your pattern. If your strategy is the same regardless of whether your counterpart knows it, it's robust.

**Ask yourself:**

- Would this approach still work if they knew exactly what I was doing?
- Am I relying on surprise, or on structural advantage?
- Is my approach balanced enough that knowing it doesn't help them?

**Example:**

A manager who sometimes pushes back on scope and sometimes accepts it — based on clear criteria — can't be gamed. A manager who always pushes back gets circumvented. A manager who always accepts gets overloaded.

---

### Probe-to-Commit Ratios

> **QBT-001**: [Proof](../proofs/001-OBSERVATION-PRECEDENCE.md) *(observation precedes commitment)*

How often should you test/explore vs. commit resources? This is the fundamental explore-exploit tradeoff.

The ratio depends on your information advantage:

- **Low information:** Probe more, commit less. You're still learning the landscape.
- **High information:** Commit decisively. Probing wastes resources when you already know the answer.
- **Uncertain information:** Mix probes and commits. Each probe should be designed to resolve a specific uncertainty.

**Example:**

Early in a new role, spend more time asking questions and observing (probing) than making changes (committing). After 90 days, the ratio should flip — you have enough context to act decisively. If you're still mostly probing at month 6, you're stalling.

---

## Cognitive Failure Modes

These are the recurring errors that degrade decision quality. Knowing them doesn't prevent them — you need systems to catch them in real time.

### 1. Frequency Bias

Overweighting rare or vivid outcomes while ignoring base rates.

**How it shows up:**

- Fixating on the one time a project blew up, ignoring the 20 times it went fine
- Overestimating unlikely scenarios because they're emotionally charged
- Making decisions based on anecdotes instead of data

**Countermeasure:** Before deciding, ask: "How often does this actually happen?" Ground decisions in actual frequencies, not memorable exceptions.

---

### 2. Rushed Processing

Sacrificing decision quality for speed under pressure. The speed-quality tension is real, but most people default to speed when they should default to quality.

**How it shows up:**

- Committing to a direction in the first 30 seconds of a discussion
- Skipping OODA phases (see `docs/dreams/OODA.md` Anti-Patterns)
- Feeling productive because you're moving fast, while making avoidable errors

**Countermeasure:** Maximize decision quality per unit time, not decisions per unit time. A 5-minute pause that prevents a 2-week mistake is the best trade you'll make.

---

### 3. Pattern Lock

Becoming too linear or predictable in your approach. When you find something that works, you repeat it — even after the environment changes.

**How it shows up:**

- Using the same negotiation tactic every time
- Defaulting to the same technical architecture regardless of requirements
- Applying yesterday's strategy to today's problem without re-evaluating

**Countermeasure:** Periodically audit your defaults. Ask: "Am I doing this because it's right for now, or because it worked last time?" See Principle 8 (Balanced Unpredictability) in `docs/dreams/FIELD-GENERAL.md`.

---

### 4. Misapplied Force

Pushing aggressively without a clear target or expected outcome. Effort without direction is waste.

**How it shows up:**

- Working 12-hour days without a clear definition of what "done" looks like
- Being assertive in a meeting without a specific outcome you're driving toward
- Applying pressure to a situation that requires patience

**Countermeasure:** Before applying force, name your target: "I'm pushing for X because Y." If you can't fill in X and Y clearly, you're not ready to push. See Principle 2 (Asymmetric Pressure) in `docs/dreams/FIELD-GENERAL.md`.

---

## Applied Examples

### Example 1: Product Prioritization Meeting

**Situation:** Three stakeholders each want their feature prioritized. You have capacity for one.

**Decision theory applied:**

- **Probe-to-commit:** Ask each stakeholder one clarifying question about user impact before committing. Don't over-research — you need just enough to break the tie.
- **Indifference check:** If you genuinely can't decide, the features are probably similar in value. Pick the one with the lowest risk and ship it.
- **Failure mode watch:** Guard against frequency bias (the loudest stakeholder isn't necessarily right) and rushed processing (don't pick the first one presented just to end the meeting).

### Example 2: Salary Negotiation

**Situation:** You've received an offer. You think it's below market but aren't sure by how much.

**Decision theory applied:**

- **Information first:** Research the distribution of compensation for this role. Think in ranges, not a single number.
- **Probe-to-commit:** Start with a question ("How was this number determined?") before countering. The response reveals their flexibility.
- **Equilibrium strategy:** Your counter should be defensible even if they know your reasoning. "Market data shows X" is robust. "I just want more" is not.

### Example 3: Technical Architecture Decision

**Situation:** Team is split between building custom vs. using an off-the-shelf solution.

**Decision theory applied:**

- **Distribution thinking:** Don't compare best-case custom vs. worst-case off-the-shelf (or vice versa). Compare the full range of likely outcomes for each.
- **Indifference principle:** If the team is genuinely split, the options are probably close in value. Choose based on reversibility — which one is easier to undo if wrong?
- **Failure mode watch:** Guard against pattern lock (choosing custom because "we always build our own") and misapplied force (over-engineering the custom solution because the team is excited).

---

## Summary

Decision theory provides the analytical backbone for the Field General framework:

- **Equilibrium** tells you what a balanced approach looks like
- **Probe-to-commit** tells you when to explore vs. act
- **Failure modes** tell you where your thinking is likely to break

Use these as diagnostic tools. When a decision feels stuck, check: Am I near equilibrium? Is my probe-to-commit ratio right? Which failure mode am I closest to?

For the complete operating framework, see `docs/dreams/FIELD-GENERAL.md`.
