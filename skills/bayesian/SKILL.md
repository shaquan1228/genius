---
name: bayesian
description: Bayesian analysis of a decision under uncertainty. Frame the game. Name each option. Update on what the other party has already done. Price each option as an interval, not as one number. Give the verdict and the counter-math that changes it. Use for offers, negotiations, vendor and bid decisions, hiring, pricing, roadmap trade-offs, timing calls, and "what are my options". Run it when the user never says "expected value", "EV", or "probability". Do not wait to be asked.
argument-hint: "[the decision, with any numbers you have]"
---

## Task

Frame the decision as a game. Name each option. Price each option as an interval. Give the verdict in one sentence.

## Context

- The trigger is a fork with an uncertain result (GNS-005). The user does not have to name it as one.
- An offer, a negotiation, a bid, a hire, a ship date, and "what are my options" are all forks.
- If GNS-001..006 are not in context, read `../../docs/identity.md` relative to this file. In Claude Code, this is `$CLAUDE_PLUGIN_ROOT/docs/identity.md`. Load it inline. Do not prompt the user.
- GNS-001 governs the frame. GNS-004 governs the counter-math. GNS-002 governs the loop after a probe returns.
- The full proofs ship with the plugin at `../../docs/proofs/`, relative to this file. Read one there when you need the derivation, not the citation.
- `../../docs/proofs/PROOF-TREE.md` says when each proof fires. Read it if a citation here is unclear.
- There are two depths. Scan answers "what are my options" in ten lines. Solve does the full analysis.
- `references/method.md` gives both output shapes, the game frame, the tree, and reactive parties. Read it first.
- `references/bayes.md` gives the update. Read it when another party has already acted.
- `references/bounds.md` gives the interval rules and the outcome count. Read it before you write a number.
- `references/counter-math.md` gives the breakeven, the survival check, and the probe. Read it before the verdict.
- `references/examples.md` gives a bad answer and a good answer for six decisions. Read it for calibration of judgment and tone, not of depth.

## Rules

- Do the analysis in the answer. Do not ask permission. Do not announce the skill.
- Select the depth first. Use Scan for "what are my options" or when there are no numbers.
- Use Solve when numbers are present, or when the user asks for the math.
- Frame the game before you price it (GNS-001).
- Name the parties, the goal of each party, and where the accounting stops.
- Say if the game is one-shot or repeated. Say if the game is closed or open.
- List each live option before you price it. Add the options the user did not name.
- Test these four options every time: wait, do nothing, a mix, and buy information.
- Adding an unnamed option is in scope. Replacing the user's decision with a different one is not.
- Find the reference class and its base rate before you form a view of this case.
- Give an interval for each uncertain quantity. Do not give one number.
- Widen any interval you marked `assumed`. A stated ninety percent interval holds the truth about half the time.
- Do not solve the tree once per input end and call the pair an interval. That is interval arithmetic.
- With two or more assumed inputs, sample them and run the tree on each draw. Report P10, P50, and P90.
- Report the probability that the best option beats the next one. Give a number a reader can score.
- Decide on expected value, after the survival check has removed any option that can end the game.
- Do not decide at a percentile. It hides a large risk aversion and it punishes an option for a wide interval.
- If the better option changes across the interval, compute the value of information. Do not answer "not yet".
- Then either buy the probe or act now on expected value. Say which, and say why.
- If another party has acted, update the hypothesis set before you price it.
- Count only the outcomes that decide the result. An outcome that improves your position and still loses is not decisive.
- Ask what must be true for the other party to still be here. Then price what is left.
- Mark each number `given`, `derived`, or `assumed`. Do not give an assumed number as a fact.
- Show the arithmetic. Then give the answer in plain words.
- Say when EV is the wrong test. A branch that ends the game is a survival question.
- End each answer with the fact you do not know that moves the answer most. Give its cost.
- Say what to re-price after the probe returns (GNS-002). Say whether the answer fell inside your interval.
- Do not build a tree if one option is clearly best, or if nothing is at stake (GNS-005). Say so and stop.
- Do not run this on a routine technical choice that has a conventional default.
- Price the decision the user gives. Do not judge the user.
- Keep the sentences short. Simple text is the deliverable.

## Evaluate

Both depths ship only if all of these hold:

- The frame names the parties, the goal of each, and where the accounting stops.
- Each live option appears. This includes the options the user did not name.
- The answer ends with the missing fact and its cost.

Solve also requires all of these:

- A reference class or base rate anchors each interval, or the answer says why none exists.
- Each uncertain quantity has an interval and a source mark. No single number stands alone.
- The output gives the probability that the best option beats the next one.
- The verdict rests on expected value under the survival cap, not on one end of an interval.
- A crossing verdict carries a value-of-information number, not a refusal to answer.
- The posterior sits next to the prior wherever another party has acted.
- Only decisive outcomes are in the count. Discounted outcomes are marked as discounted.
- The probabilities at each chance node sum to 1. Each price line shows its arithmetic.
- Each decision node inside the tree takes the maximum, not a forced choice.
- The counter-math gives a breakeven. It says if that breakeven is inside the interval.
- The survival check ran.

## Iterate

1. Load the identity if absent. Read `references/method.md`.
2. **Gate.** Confirm two or more live options and an uncertain result. If one option is clearly best, say so and stop (GNS-005). Then select Scan or Solve.
3. **Frame.** Name the game and where the accounting stops. List each live option (GNS-001). Scan stops after step 6.
4. **Update.** If another party has acted, use `references/bayes.md`. Put the prior next to the posterior.
5. **Set the intervals.** Use `references/bounds.md`. Anchor on a base rate, then widen. Count only decisive outcomes. Set the unit and the horizon.
6. **Propagate.** Build the tree. Sample the assumed inputs and run the tree on each draw. Report P10, P50, P90, and the probability the best option wins.
7. **Counter-math.** Solve each breakeven. Rank the inputs. Run the survival check. Price the cheapest probe (GNS-003, GNS-004).
8. **Report.** Use the output shape for the depth. Check the answer against Evaluate.
