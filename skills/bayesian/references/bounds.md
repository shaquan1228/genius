# Intervals

One number is a claim you cannot support. Two numbers with a threshold between them is an observation. Give an interval for each uncertain quantity.

The failure this prevents is not random. People take **one optimistic number** and then act as if it were measured. They count the good branch in full and the bad branch in part.

## 1. Build the interval

Start with the outside view. Find the reference class and its base rate before you form any view of this case. A bid, a hire, a migration, and a launch all have a population. The spread of that population is your starting interval. The inside view narrows it only when you can say what makes this case different.

- **Low end.** A defensible pessimistic reading, near a tenth percentile.
- **High end.** A defensible optimistic reading, near a ninetieth percentile.

**Then widen.** A stated ninety percent interval holds the truth about half the time. This is the best measured bias in forecasting and it runs one way. If an interval does not feel too wide, it is too narrow. Widen any interval marked `assumed` before you use it. Say that you widened it.

Take the ends from a base rate, from the past spread of the same thing, or from two independent estimates. Use a pessimistic and optimistic reading last. Say which source you used.

**Set each input's interval on its own.** An input's interval describes that input, not the world. See §2 for how the intervals combine.

## 2. Combine the intervals, then decide on the result

Two intervals do not combine by evaluating the model at both ends. That is interval arithmetic. It carries no probability, and it only finds the true extremes when the result moves one way with every input. A tree with a decision node does not.

**With two or more `assumed` inputs, propagate.** Give each input a distribution from its interval. Draw a few thousand samples. Run the tree on each draw. That is twenty lines of script and it replaces the guesswork.

Report three things:

- The result at P10, P50, and P90.
- **P(this option beats the next best one).** This is the number a reader can be scored on. A skill that never states one cannot be checked.
- Which inputs carry the spread.

Name any inputs that share a cause and draw them together. Two inputs driven by one fact are one input, and treating them as independent understates the spread.

**Then decide on expected value, subject to the survival cap.** First run `counter-math.md` §4. It removes any option that can end the game. Then take the best expected result of those left.

That is the stated risk position of this skill. It is neutral on expected value and hard-capped on ruin.

The low end is reported, and it feeds the survival cap. It is not the decision point. Deciding at a percentile looks careful and hides a large risk aversion that nobody chose. It also punishes an option for a wide interval. That width is a fact about your knowledge, not about the option.

When only one input is uncertain, or the numbers are rough, the tree still gets solved once per end. Say that the pair is a sensitivity range and not a distribution.

## 3. When the verdict crosses

Sometimes the better option changes across the interval. That is a real finding. It is not a verdict of "not yet".

A crossing means information could change your action, so the value of information is above zero. It does not mean the information is worth buying. Compute it.

```
VOI = the expected result when you decide after learning − the expected result when you decide now
```

Then compare VOI to the cost of the probe, including the cost of the delay. The output is one of two sentences.

- **VOI beats the cost.** "Buy this probe for this price, then act." Name the probe and the input it settles.
- **VOI does not beat the cost.** "Act on the best expected value now." Then say what would have changed it.

An example. One option is worth $95k at the low end of adoption and $140k at the high end. The alternative is a flat $120k. The verdict crosses. But the first option averages $117.5k. The alternative wins on expected value today, and the whole crossing is worth about $4.4k. If measuring adoption costs more than that, or delays the deal, take the alternative now and stop analyzing.

Never write that nothing else matters until the input is measured. Most crossings are worth less than they feel.

## 4. Count only what decides the result

An outcome that improves your position and still loses is not decisive.

Ask what you actually win after each favorable outcome lands.

| Outcome | Count it as | Why |
|---|---|---|
| You win outright | **Decisive** | Count it in full |
| You improve and still lose | **Not decisive** | Zero when the payoff is win-or-lose. It is a larger loss, not a gain |
| You win only against the parties who were leaving anyway | **Zero** | See §5 |
| You win against part of the cases | **Discount it** | Use a half, or a fraction you can defend. Name the discount |

The second row applies where the payoff is binary, such as a contract you win or lose. Where the payoff is continuous, a partial improvement is worth its own value. Losing by less is worth something. Say which kind of payoff you have.

Work examples of the second row, all binary. A milestone that makes a project look better and does not change the funding decision. A feature that keeps the customers who would never leave. A concession to a counterparty who would already sign. A benchmark win on a metric the buyer does not score. Each improves your position. None changes the result.

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

> The win probability runs **24% to 42%**, and the commitment needs **43%**. It misses even at the top, though only by a point. Call it thin, not robust.

> Expected value favors A, and A beats B in about 7 runs in 10. The low end clears the survival cap.

Use one sentence. Give the spread and the threshold together. If the better option changes across the interval, use §3.
