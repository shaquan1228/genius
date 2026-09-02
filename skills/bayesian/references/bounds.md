# Intervals

One number is a claim you cannot support. Two numbers with a threshold between them is an observation. Give an interval for each uncertain quantity.

The failure this prevents is not random. People take **one optimistic number** and then act as if it were measured. They count the good branch in full and the bad branch in part.

## 1. Build the two ends

- **Low end.** A defensible pessimistic reading. Use about a tenth percentile. It is not the worst case.
- **High end.** A defensible optimistic reading. Use about a ninetieth percentile. It is not the best case.

Neither end is a scenario minimum or a miracle. You must not be surprised by either result. Nobody uses an end they do not believe. That returns you to the single optimistic number.

**Set each input's interval on its own.** Do not put every input at its low end at the same time. Each input at its low end at once is a far rarer world than any single low end. That world biases every verdict toward "do nothing" and "not yet". Vary one input at a time. Use `counter-math.md` §3 to find the input that drives the verdict. Then make the verdict at the low end of that input.

Take the ends from a base rate, from the past spread of the same thing, or from two independent estimates. Use your pessimistic and optimistic reading last. Say which source you used.

## 2. Decide low. Commit low.

- **Make the verdict at the low end of the driving input.** If it fails there, it fails.
- **Size the commitment at the low end.** A commitment sized at the high end is how a correct estimate loses money. Kelly at a 52% estimate commits 3.4 times what a 40% estimate commits, on the same 35% cost.
- **The high end measures what is at stake in learning more.** It is the value of the question. It is never the answer.

## 3. The crossing rule

If the verdict changes between the low end and the high end, **you do not have a verdict**.

Say this. Name the input that crosses the threshold. Price the cheapest way to resolve it.

An example. An option is worth $95k at the low end of adoption and $140k at the high end. The alternative is worth a flat $120k. The verdict crosses. Adoption is the input to go and measure. Nothing else in the analysis matters until it is measured.

This is not a hedge. A crossing is a specific result. It says the decision is indeterminate on current evidence. It also names the one fact that settles it.

A crossing means no option yet loads a fork. GNS-005 is the proof. The derivation is at `../../../docs/proofs/005-FORK-LOADED-ITERATION.md`.

**When a deadline blocks the probe**, you must still decide. Use the midpoint. Say the confidence is low. Say what you would have measured. Then set a review date for when the fact arrives on its own.

## 4. Count only what decides the result

An outcome that improves your position and still loses is not decisive.

Ask what you actually win after each favorable outcome lands.

| Outcome | Count it as | Why |
|---|---|---|
| You win outright | **Decisive** | Count it in full |
| You improve and still lose | **Not decisive** | Zero. It is a larger loss, not a gain |
| You win only against the parties who were leaving anyway | **Zero** | See §5 |
| You win against part of the cases | **Discount it** | Use a half, or a fraction you can defend. Name the discount |

Work examples of the second row. A milestone that makes a project look better and does not change the funding decision. A feature that keeps the customers who would never leave. A concession to a counterparty who would already sign. A benchmark win on a metric the buyer does not score. Each improves your position. None changes the result.

The third row is the expensive one. It hides inside a win. Say you win the contract at a price below the cost of winning it. That is not a win. Count the outcomes where you win **and** the result covers the cost. That count is usually far smaller than the first count, and it is the honest one.

Make one more check before you commit the count. **Does your favorable outcome also help them?** The integration that unblocks you can unblock a competitor on the same platform.

## 5. Condition on their response

You do not face the distribution of the world. You face the distribution **given that the other party continued**.

This runs against you by construction.

- **When you are right, they quit.** You collect little from the good branch. The deals you would win cheaply get withdrawn. The counterparties you beat walk away.
- **When you are wrong, they continue.** All the volume is in the bad branch. The other party is happy to go on.

Two names for this are standard. It is the **winner's curse** at an auction. It is **adverse selection** in a market. The fact is the same. **An offer you can accept is an offer someone chose to make you.**

Use this test before you price a branch where the other party had a choice. Ask: *what must be true for them to still be here?* Answer it. Most of the cases you win then leave the count. That is the point. Price what is left.

## 6. Report the interval

Give the interval and the threshold together. The reader must not need to do arithmetic.

> The win probability is **24% to 42%**. The commitment needs **43%**. It misses at both ends. The decision is not close.

> The low end clears the hurdle by 5 points. Commit 2% of the budget, not 6.5%.

Use one sentence. Name the end that decided it. If the two ends disagree, use §3.
