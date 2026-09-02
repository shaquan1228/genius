# Examples

Six decisions. Each shows a bad answer and a good answer.

These are calibration for judgment and tone. They are deliberately light. None builds a long scenario that lands on a single number. A single number is the failure this skill exists to prevent. The machinery lives in the other reference files. Use it when a real decision earns it.

Read the bad answers first. Each one is fluent, confident, and wrong.

---

## 1. A bid that asks you to build first

**Decision.** You are one of two finalists. The contract carries $700k of margin. Procurement wants a $300k custom integration built first.

**Bad**

> Finalist means roughly even odds. Half of $700k beats a $300k build, and the integration is reusable for other accounts anyway. Build it.

- "Roughly even" is the prior. The demand is new evidence and it points one way.
- Reusable elsewhere does not decide this contract. It is not an out.
- No hurdle is stated. The build needs about 43%, from `300 / 700`.

**Good**

> **Do not build.** The hurdle is `300 / 700`, so about 43%.
>
> A buyer who means to pick you does not need $300k of free engineering first. That demand comes far more often from buyers already committed elsewhere. Before it, most finalists in this position are live. After it, few are.
>
> Update on the demand and your chance lands somewhere in the mid twenties to low forties. The hurdle sits at or above the top of that. It fails at both ends, so the verdict is robust.
>
> **Do not know.** How often this buyer runs a real competition. Ask your channel contact who won their last three. That is one call. If the incumbent always renews, stop bidding the account, not just this deal.

---

## 2. Two pair against a large shove

**Decision.** You hold two pair. The board allows both a flush and a straight. They shove three times the pot.

**Bad**

> Two pair is strong and you beat everything they were continuing with earlier. You also have four cards that make a full house. Call.

- The hands you beat are the ones that fold. They are not in the range that shoves this size.
- Improving to a straight would still lose to a flush. An improvement that loses is not an out.
- No price is stated. Three times the pot needs about 43%.

**Good**

> **Fold.** A shove that large comes from hands that already beat you. The part of their range you beat folds instead of shoving.
>
> Only a full house wins. Four cards do that, which is under 10%. The price needs about 43%.
>
> For the call to work, they would need to shove this size as a bluff around half the time. Almost nobody does at three times the pot.
>
> **Do not know.** Their shove size with a bluff. It costs nothing to watch for and three pots to buy. Collect it. Do not pay for it.

---

## 3. An offer with a deadline

**Decision.** An offer at $185k, answer due in five days. You earn $210k now, but your team is being reorganized. You want to counter at $215k.

**Bad**

> Counter and they might move, hold, or pull the offer. If they pull it you get nothing. Averaged out that sits below what you earn today. Do not counter.

- A withdrawn offer is not zero. You still have your job.
- "They hold" is treated as a result. It is a decision. You can still stay.
- Staying is priced as certain. The reorg is the reason the question exists.

**Good**

> **Counter today.**
>
> Two of those branches are decisions, not results. If they hold, you choose between $185k and staying. If they withdraw, you stay. Price each branch at its better half, not at the half that reads worst. Forcing them inverts the answer.
>
> Staying is worth less as the reorg risk rises. Countering wins once that risk clears the high single digits. Your honest interval starts well above that. It wins across the whole interval.
>
> "This offer expires Friday" tells you nothing. A real deadline and a pressure tactic both produce that sentence. Ask for one more week instead. A real deadline usually cannot move and a manufactured one usually can. That question separates them. Asking for it in writing does not.
>
> **Do not know.** The reorg risk. It moves this more than any other input. One conversation this week. It does not gate the counter. Re-price only the accept-or-stay choice after it lands.

---

## 4. Ship Friday or wait

**Decision.** Ship the migration Friday, or wait two weeks for the new deploy tooling.

**Bad**

> Waiting is safer. The new tooling reduces the rollback risk. Ship in two weeks.

- Two options. Shipping behind a flag and shipping one slice are both live.
- It prices the risk of shipping and ignores the cost of waiting.
- "Safer" is not a verdict. It names no threshold and no comparison.

**Good**

> **Ship one slice Friday, behind a flag. Hold the rest.**
>
> **Game.** You, the on-call rotation, and one customer whose renewal falls inside the two weeks. Open, so events land during the wait either way.
>
> Waiting is not free. It moves the migration into the renewal window, which is the most expensive place for it to fail. The comparison is not risk against zero. It is risk now against risk later plus that exposure.
>
> A flagged slice buys most of the information the full ship would buy, at a fraction of the exposure. That is the smallest reversible step available here.
>
> **Do not know.** Whether the slice exercises the path that actually worries you. Ask the engineer who wrote it, today. If it does not, the slice proves nothing and the flag is theater.

---

## 5. A reference check

**Decision.** A candidate is strong on paper. Their reference says they were great to work with.

**Bad**

> The reference came back positive, so that is a good signal. Move to an offer.

- A candidate picks their own referees. Strong and weak candidates both produce that sentence.
- It never asks what a weak candidate's reference would sound like.
- Two options, offer or not. There are more.

**Good**

> **That reference moved nothing.** Candidates choose who speaks for them. Both stories predict "great to work with", so it carries no information.
>
> Ask for something only one story can produce. Try "what did they own end to end, and what shipped?" A referee for a weak candidate answers that vaguely. A referee for a strong one does not.
>
> **Options.** Offer. Offer with an earlier review point. A paid trial. One more round aimed at the specific doubt.
>
> **Do not know.** Whether the doubt is about the skill or about the level. Those need different questions and different options. Name which one before you book the next round.

---

## 6. "What are my options"

**Decision.** "Our biggest customer wants a feature. It means we rebuild the scheduler. What are my options?"

There are no numbers and the ask is the option set. Use Scan. Ten lines. No tree.

**Bad**

> You can build it or not build it. Building costs about two quarters. Not building risks the account. It depends on how much you value the relationship.

- Two options. There are five.
- No recommendation. It returns the question to the user.
- No missing fact, so the user learns nothing they can act on.

**Good**

> **Game.** You, one large customer, the other customers who watch what you do for them, and two quarters of roadmap. Repeated and open. The accounting stops at the relationship, not at this feature.
>
> **Options**
> 1. Build it as asked. The real cost is the roadmap it displaces, not the scheduler.
> 2. Build only the part that blocks them. Usually a small fraction of the work.
> 3. Price it as a change order. This is a probe and revenue at once. A customer who will not fund it did not need it.
> 4. Say no, with a date.
> 5. Ask what breaks for them if it ships in two quarters. Sometimes nothing does.
>
> **Recommendation.** Option 3, then option 2. Option 3 answers the unknown below, and the customer pays you to ask it.
>
> **Do not know.** Whether this blocks the renewal or is a wish. Ask their sponsor this week, before you commit engineers. If it blocks the renewal, re-price options 1 and 2 against the contract value.

---

## Traps

| Trap | It looks like | The fix |
|---|---|---|
| One optimistic number | A single estimate from the good end | Use an interval. Decide at the low end |
| Pricing the prior | "We are a finalist", after they made a demand | Update first. Then price what is left |
| Non-decisive outcomes | Counting results that improve and still lose | Count only outcomes that decide the result |
| A win that loses | Winning below the cost of winning | Count outcomes where you win and it pays |
| Ignoring the response | Pricing a branch the other party would not allow | Ask what must be true for them to still be here |
| A forced decision node | Pricing "they hold" as an accept | Take the better branch. You still choose there |
| Zero fallback | A withdrawn offer priced at nothing | Price it at the next best option |
| Sizing at the high end | The estimate was right and the budget still went | Size at the low end. Use a fraction of Kelly |
| Weak evidence, hard update | Updating on what both stories predict | Ask what the other hypothesis looks like |
| Two updates, one fact | A rumor and the article about that rumor | Correlated views of one fact are one observation |
| Undiagnostic probe | Asking for a claim in writing | Ask for what only one hypothesis can give |
| False choice of two | Two options, both named by the user | Add wait, do nothing, a mix, and buy information |
| Risk against zero | "Waiting is safer" | Price the cost of waiting too |
| Headline number | Base salary, list price, contract value | Convert to the unit over the full horizon |
| Sunk cost in a branch | "We already put six months into this" | It is equal on each option. It cancels |
| Fixed counterparty | A constant probability for a party who reacts | Write it as a function of your action |
| Wrong boundary | Pricing the deal when the account is the game | State where the accounting stops. Price inside it |
| Closed-game thinking | Optimal under exactly today's rules | Prefer options robust across rule changes you can name |
| Average over an ending | Positive EV with a branch that ends the game | Use survival. Cap the commitment. Then price again |
| Values added late | "The math says A, but I would regret it" | Put non-money payoffs in the unit at the start |
| Every input at its low end | A pessimistic answer to every question | Vary one input at a time |
| False accuracy | A five-level tree from three known numbers | Stop where the evidence stops |
| Interrogation | Twelve questions before any analysis | Ask only for inputs that change the ranking |
