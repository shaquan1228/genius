# The update

A party who has acted has told you something. Price against the hypotheses their action leaves. Do not price against the hypotheses they held before it.

This is the most common error in decision analysis. When the action is costly or aggressive, the error runs one way. It makes the answer too optimistic.

## The move

```
posterior ∝ prior × P(the action you saw | this hypothesis)
```

For two hypotheses, use odds. Odds are faster to say out loud.

```
posterior odds = prior odds × likelihood ratio
```

Three columns are the whole method. Put the hypotheses down the side. Add the prior. Add the likelihood of the action under each hypothesis. Normalize. Report the prior next to the posterior.

## 1. Set the prior

The prior is what you believed before the party acted.

- Take it from a base rate, a population frequency, or what their position pays them.
- Do not take it from how memorable the last case was.
- A rough prior said out loud is better than an exact prior left unsaid. "About a third" is usable.
- Nobody can attack a prior you did not state. That is why a wrong one survives.
- A prior is also an interval. Carry it through. See `bounds.md`.

## 2. The likelihood does the work

Do not ask how likely the hypothesis is. The prior answered that.

Ask this: **how likely is the action I saw, if this hypothesis is true?**

Here is the inversion error. `P(a hard demand | they already chose someone else)` is not `P(they already chose someone else | a hard demand)`. `P(a fast reply | they are keen)` is not `P(they are keen | a fast reply)`. The prior converts one into the other. Without the prior, a rare hypothesis with a loud signature takes over the answer.

**Diagnosticity.** An action that each hypothesis predicts equally tells you nothing.

| Observation | P(obs \| A) | P(obs \| B) | Ratio | Value |
|---|---|---|---|---|
| "This offer expires Friday". A is a real deadline. B is pressure. | 0.90 | 0.95 | 0.95 | none, both say it |
| A revised quote in two hours. A is they want the deal. B is they are filling a pipeline. | 0.70 | 0.15 | 4.7 | a real update |

Before you update, ask what the other hypothesis looks like. If it looks the same, you learned nothing.

Use this scale for the ratio. **Below 3 is weak. 3 to 10 is a real update. Above 10 is strong.** One weak observation does not collapse a hypothesis set. Several independent weak ones can. Check that they are independent first. Correlated views of one fact are one observation.

## 3. Build categories that hold

- Use **three to five hypotheses**. More is false accuracy. Fewer hides the branch that matters.
- The categories must not overlap. They must cover all cases. The priors sum to 1.
- Split them by **what decides the result**. Do not split them by what is interesting.
- For a deal, split into: it closes, it closes later or smaller, and it does not close.
- For a party, split into: they are committed to you, they are undecided, and they are committed elsewhere.
- Keep a bucket for **the story you have not thought of**. Give it 5% to 10%.

## 4. What you hold changes what they can hold

Your information and your position remove possibilities from theirs.

Say you know the budget already went elsewhere. The hypothesis "they are comparing us against a large competitor" then loses most of its weight. Say you know their integration lead resigned last month. The hypothesis "they can build this in house" loses weight the same way.

The effect is smaller than it feels. It moves a hypothesis set. It does not empty one.

## 5. Silence is an action

A delay, an email with no reply, a skipped meeting, and a passed deadline are observations. Each has a likelihood.

A party who wants to say yes usually says yes quickly. Put silence through the same three columns. Do not treat "nothing happened" as "nothing changed".

Silence cuts the other way from a costly action. A quiet party is more often a cool party. Update toward the pessimistic hypothesis, not the optimistic one.

## 6. Two failures to check

- **Two updates on one fact.** A rumor and an article about that rumor are one observation. Correlated evidence counted twice makes false certainty.
- **No update at all.** A hypothesis set that survives each observation was never a set. If nothing moved, say which observation should have moved it, and why it did not.

## 7. Report it simply

Give two columns and one sentence. The reader wants the shape of the change, not your arithmetic.

> Before the demand, 45% of the cases like this were live deals we win. After the demand, that is 7%. Buyers who mean to pick you do not need to extract free work first.

Then give the number. Do not give the number alone. A posterior with no explanation is not actionable. The explanation is what the reader checks against what they know about the party.
