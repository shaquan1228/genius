# STOP TINKERING

Read this when you're tempted to add complexity, optimize prematurely, or continue past "good enough."

---

## The Tinkering Test

> **QBT-001**: [Proof](../proofs/001-OBSERVATION-PRECEDENCE.md) *(observation precedes action — this test is the instrument)*

Before adding complexity (new tools, abstractions, optimizations, extended work):

### Score each question 0-5:
- **5** = Strongly yes
- **3-4** = Somewhat/Maybe
- **1-2** = Barely/Unclear
- **0** = No/Bad

#### 1. Problem Clarity (0-5)
Can you describe the problem in one sentence?
- **5**: Crystal clear, measurable problem ("Tests take 10 minutes")
- **3**: Vague but real ("This is hard to maintain")
- **0**: Can't articulate or "someone said X is better"

#### 2. Cognitive Load (0-5)
Will this reduce cognitive load overall?
- **5**: Eliminates entire category of problems
- **3**: Neutral trade (new complexity = removed complexity)
- **0**: Adds net complexity with no clear reduction

#### 3. Junior-Me Test (0-5)
Can junior-you understand this in 2 minutes?
- **5**: Obvious, simple, self-explanatory
- **3**: Takes 5-10 minutes to explain
- **0**: Requires deep understanding of abstractions/patterns

#### 4. Blocked vs Bored (0-5)
Are you actually blocked?
- **5**: Cannot proceed without this, users impacted
- **3**: Slowed down significantly
- **0**: Just curious or saw something shiny

### Scoring:
- **15-20 points**: Proceed (clear problem, reduces load, understandable, blocking)
- **9-14 points**: Wait 2 weeks, document pain points, re-evaluate
- **0-8 points**: HARD STOP. Close this file. Go ship value.

---

## Examples

### Dev Environment: "Should I switch to a new terminal?"
- Problem clarity: 0 (no specific problem)
- Cognitive load: 0 (adds learning curve)
- Junior-me: 2 (new tool to learn)
- Blocked: 0 (current terminal works)
- **Score: 2/20 → HARD STOP**

### Code: "Should I extract this working code into a framework?"
- Problem clarity: 0 ("could be more elegant" is not a problem)
- Cognitive load: 0 (adds abstraction)
- Junior-me: 0 (harder to debug)
- Blocked: 0 (code works)
- **Score: 0/20 → HARD STOP**

### Code: "Should I add validation at the boundary?"
- Problem clarity: 5 (bad data causes crashes downstream)
- Cognitive load: 5 (prevents debugging bad data)
- Junior-me: 5 (obvious: validate input)
- Blocked: 5 (users experiencing errors)
- **Score: 20/20 → PROCEED**

### Session: "Should I fix this other thing I noticed?"
- Problem clarity: 3 (noticed an issue)
- Cognitive load: 3 (small fix)
- Junior-me: 5 (straightforward)
- Blocked: 0 (not related to current goal)
- **Score: 11/20 → WAIT (create ticket, finish current goal first)**

---

## The 2-Week Rule

For scores **9-14** (unclear benefit):

1. **Document the pain** - Write down specific instances where this hurt
2. **Wait 2 weeks** - Use current approach, note every time it's painful
3. **Re-evaluate** - If still painful after 2 weeks with documented evidence, proceed

This prevents:
- Premature optimization
- Tool-hopping based on hype
- Solving problems you don't actually have

---

## The Productivity Paradox

**Time spent tinkering = Time NOT spent shipping**

Example:
- Time spent: 4 hours "improving" setup
- Time saved: 5 minutes/day
- Break-even: 48 days
- Cognitive load: Higher (new tool)
- Actual productivity: Lower (time lost)

**Ask: Could I ship a feature in those 4 hours instead?**

---

## What to Do Instead

When you feel the urge to tinker:

### If score is 0-8 (HARD STOP):
1. **Close this file immediately**
2. **Go ship value** - Write code, fix bugs, help users
3. **Resist the urge** - Boredom is not a reason to change things
4. **No exceptions** - If you can't score above 8, you're tinkering

### If score is 9-14:
1. **Create a ticket** - Document the pain point
2. **Set a reminder** - 2 weeks from now
3. **Finish current work** - Don't context switch

### If score is 15-20:
1. **Proceed** - You have a real problem
2. **Keep it simple** - Smallest solution that works
3. **Measure impact** - Verify it actually helped

---

## Remember

You didn't learn to code to:
- Configure tools perfectly
- Write elegant abstractions for their own sake
- Optimize non-bottlenecks

You learned to code to **build things that matter**.

**Use your tools. Don't improve them.**

**Ship your code. Don't perfect it.**

**Finish your task. Don't expand it.**

---

## Quick Reference Card

```
TINKERING TEST SCORECARD
━━━━━━━━━━━━━━━━━━━━━━━━━
1. Problem clarity?     /5
2. Reduces load?        /5
3. Junior-me gets it?   /5
4. Actually blocked?    /5
                      ────
   TOTAL:             /20

15-20: Proceed
 9-14: Wait 2 weeks
  0-8: HARD STOP
```

Now close this file and go build something.
