# Counter-math

The price is arithmetic done on premises. Arithmetic does not validate a premise (GNS-004). Counter-math tests each input. It reports what survives.

Run each section. Report the sections with content. Never omit the breakeven, the survival check, or the "do not know" line.

## 1. Solve the breakeven

For each input that can change the ranking, solve for the value that makes two paths equal. Report it as a threshold sentence. Do not report a number alone.

> "This commitment needs the unwinnable cases to be under 53% of the ones that look like it."

Two branches. Option A pays `a` with probability `p` and `b` if not. Option B pays `c`.

```
p·a + (1−p)·b = c   →   p = (c − b) / (a − b)
```

Show the substitution. You can test a breakeven against the world. You cannot test a point estimate. The threshold stays useful after each number that made it is replaced.

## 2. Judge the breakeven

The number alone is half the job. Compare it to the interval from `bounds.md` §1.

- The breakeven is far **outside** the interval. The verdict is **robust**. It holds for each input you accept.
- The breakeven is **inside** the interval. The verdict is **fragile**. It comes from one guess. Apply the crossing rule.
- The breakeven is at the edge. The verdict is **thin**. Use a tiebreaker. Use variance, reversibility, or option value.

Put one of those three words in the TL;DR.

## 3. Rank the inputs

Move one input across its interval. Hold the others. Record how much the gap moves. Rank the inputs by that movement.

The top of the list is the number to go and find. That ranking is often more useful than the verdict. It states one question in place of a vague worry. Name the inputs that move the gap very little. They stop taking attention.

## 4. Survival check

EV is an average over many tries. A branch that ends the game removes the tries. The average is then unreachable.

A branch ends the game if it takes you out. Examples are insolvency, no runway, and a lost license. A regulatory finding, a health result, and a lost reputation in a small market also end it. The test is not the size of the loss. The test is whether you can continue.

- One branch ends the game. Then the test is **survival, not the average**. Say that the test changed. A positive-EV option that can end the game loses to a lower-EV option that cannot.
- The normal fix is to cap the commitment until no branch ends the game. EV then applies to the capped version.
- Size a repeated commitment with the Kelly fraction. Pay `m` per unit of value, with success probability `p`. Then `f = (p − m) / (1 − m)` of the budget.
- Commit a quarter or a half of `f`. Compute `f` at the **low** end of `p`. Full Kelly on an overestimated edge is the normal way to lose a method that works.
- The same leaf ends the game for one party and not for another. Runway, dependents, and reserves change the answer. Ask when it matters.

## 5. Check n

EV describes the long run. Report the spread when the run is short.

- `n = 1` with a wide spread. Give the median and the low percentile next to the mean. A positive-EV commitment made one time is often still a bad commitment.
- The mean can sit on a branch that never occurs. Take a 20% chance of $2M and nothing otherwise. The mean is $400k. No result is near $400k. Say what the user will actually experience.
- `n` is large and each commitment is small. The mean is the correct summary. Say so and continue.

## 6. What you do not know but can learn

Each answer ends here. A probe turns an assumed input into an observed one. Price the probe.

```
VOI = the value of deciding after you learn − the value of deciding now
```

Compute both sides. Compare them to the cost of the probe. If the value wins, **buy the information**. Put that option in the tree with the others.

These probes usually beat their cost. One call to a person who has done it. One week of instrumented data. A paid pilot at 1% of the commitment. One more interview round. A small commitment before a large one. One direct question you have avoided. This is the smallest reversible step (GNS-003).

Do three things. Say **which input** the probe resolves. A probe aimed at the bottom of the §3 rank is not worth buying. Say **if you must wait for it**. You can start some options now and learn later. Say **what to re-price when it returns**. The probe starts a new loop, so observe again after it lands (GNS-002).

## 7. Optionality and reversibility

An option that keeps the right to change is worth more than its price. A one-way option pays for the choice it destroys.

- Ask the cost to undo each option. Give it in money and in months.
- When the gap is thin, reversibility decides. It is not a rounding error.
- A staged start turns a one-way option into a reversible one. It usually costs less than the choice is worth.

## 8. The game can change under you

An open game gets new payoffs from an event no party chose. Examples are a rate move, a re-org, a new competitor, a regulation, an outage, and an election.

- **An option can price badly today and still be correct.** It holds a position for a change that has not arrived. An early price is evidence about today's rules. It is not evidence about the decision. In a fast game that evidence decays.
- Ask what must change outside the game to make each option clearly correct. Then ask how likely that change is inside the horizon. An option that wins under three possible futures beats an option that wins under one.
- Prefer an option that is **robust across rule changes** to an option that is optimal under today's rules. The second kind is fragile. No sensitivity test on the inputs shows this. The thing that moves is not an input.
- If the horizon is long and the game is open, use wider intervals. Do not fake accuracy. Then say the honest thing. The answer is a position, not a prediction.

## 9. Premises another party owns

An input can depend on a loop you do not run. Examples are a counterparty, a committee, a market, and your future self. A request into that loop is direction. Direction is not validation (GNS-004).

- **Convert what you can.** Get it in writing. Set a dated deadline. Take a deposit. Stage the payment against a milestone. A converted premise is true by construction, so it leaves the tree (GNS-006).
- **Mark what you cannot.** Name each unconverted premise in the verdict as open risk. Say who owns it.

## 10. Check correlation

Branches with one shared cause fail together. If you add them as independent, you overstate the good case.

Ask what single fact makes several branches fail at the same time. Look for one customer, one funding market, one platform, or one person. If the options that look diverse all rest on it, the tree has one branch and not four.
