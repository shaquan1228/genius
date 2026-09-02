# Method

Depth, the game frame, and how to price a decision. The update is in `bayes.md`. The interval rules are in `bounds.md`. The stress test is in `counter-math.md`.

## Depth

**Scan.** The ask is "what are my options". Or there are no numbers. Ten lines. No tree.

**Solve.** Numbers are present. Or the user asks for the math.

Select the depth before you write. A Scan in the Solve shape hides the answer. A Solve in the Scan shape does not answer the question. A Scan can move up to a Solve in its last line.

### Scan output shape

````
**Game** — <parties, the goal of each, one-shot or repeated, closed or open, where the accounting stops>

**Options**
1. <option> — <one line on cost and result>
2. <option> — <one line on cost and result>
3. <the option they did not name> — <why it is live>

**Recommendation** — <the option, and what it depends on>

**Do not know** — <the fact that moves this most, and its cost>
````

### Solve output shape

````
**TL;DR** — <the verdict, the margin, the end that decided it, one word: robust, thin, or fragile>

**Game** — <one line>

**Inputs**
| Quantity | Low | High | Source |

**Update** (only if another party has acted)
| Hypothesis | Prior | After the action |

**Tree**
<indented; □ is a decision, ○ is chance; p and payoff at each leaf>

**Price**
- <Option>: <arithmetic at the low end> = <value>   [high end: <value>]

**Verdict**
<one or two lines, in plain words>

**Counter-math**
- Breakeven — <input> changes this at <value>. The interval is <interval>. Inside or outside.
- Survival — <the branch that ends the game, or "none, EV applies">
- Do not know — <the top input, its cost, and if you must learn it first>
````

Cut a line with no content. Do not cut the breakeven, the survival line, or the "do not know" line.

## 1. Frame the game

Answer five questions in one line each. Do this before any arithmetic.

- **Who are the parties?** A party is anyone whose choice changes your payoff. A market, a committee, and your future self all count.
- **What is the goal of each party?** Use what their position pays them. Do not use what they say. A recruiter is paid for a signed offer.
- **One-shot or repeated?** A repeated game prices reputation, precedent, and the information you gain. A one-shot game does not.
- **Closed or open?** A closed game has fixed rules and payoffs. An open game gets new payoffs from events no party chose. Examples are a rate move, a re-org, a competitor, and a regulation. Most real decisions are open.
- **Where does the accounting stop?** This deal or the relationship. This quarter or the company. This release or the platform.

The last two questions are where simple EV fails.

In an open game, an option can price badly today and still be correct. It holds a position for a change that has not arrived. In a repeated game, a locally bad move can be correct at the true boundary. Examples are the discount you refuse, the escalation you decline, and the small contract that gets you the reference.

State the boundary. Then price inside it. An unstated boundary gives a clear answer to the wrong question.

## 2. The option set

Price the named options. Then price the options the question hid. Almost every question arrives too narrow.

Test these four every time:

- **Wait.** A later decision with more information is an option. It has its own price.
- **Do nothing.** The current state is a branch. It is rarely worth zero.
- **A mix.** Part of A and part of B. Or a smaller commitment. Or a staged start.
- **Buy information.** Pay a small cost to learn the input that drives the answer. See `counter-math.md` §6.

An option is live if the user can take it today. Drop the other options in one line.

## 3. The unit and the horizon

Use one unit and one time window. Convert each payoff into them. State both.

- Money, hours, users, or a 0 to 10 scale all work. Mixed units do not.
- Put non-money payoffs in at the start. Price them. A value added after the arithmetic makes the arithmetic wrong.
- Match the horizon to the decision. A four-year vest is not a four-year horizon if the user can leave in one year.
- After about three years, discount the value. Or use a shorter horizon and say so.
- Convert headline numbers to totals. Base salary is not total comp. List price is not margin. A contract value is not the margin on it.

## 4. Tree notation

`□` is a decision node. You choose. `○` is a chance node. Another party or the world chooses. The probabilities at one chance node sum to 1. The branches do not overlap.

```
□ decide
├─ Take the contract
│  ○ p=.70 delivery is clean → +$180k
│    p=.30 scope expands     → −$40k
└─ Decline
   ○ p=.55 the next lead lands → +$90k
     p=.45 the quarter is flat →   $0
```

Stop the tree where the evidence stops. A tree deeper than the numbers is false accuracy.

## 5. Solve the tree

Work back from the leaves.

- At a **chance** node, take the expectation. `Σ pᵢ · vᵢ`.
- At a **decision** node, take the **maximum**. Do not take the average. Do not force one branch. You will choose then. The node is worth its best branch.

The maximum rule is easy to break. A branch that reads like a bad result is often still a decision. If a counterparty holds firm, you still choose whether to accept or walk away. Price that node at the better of the two. If you force the branch, you understate the option and you can invert the verdict.

The maximum rule is also where option value comes from. An option that keeps a later decision open is worth the best branch of that decision. For the same reason, a failed negotiation prices at the next best option. It never prices at zero.

Solve the tree two times. Solve it at the low end and at the high end. The pair of results is the answer.

Two exclusions and one inclusion:

- **Sunk costs go in no branch.** Money and months already spent are equal on each option. They cancel.
- **Opportunity cost goes in each branch.** Price each option against what the same time or money does elsewhere.
- **The cost to decide is real.** Three weeks of negotiation cost three weeks.

## 6. When the chance node is a party who reacts

Against a fixed distribution, maximize EV. Against a party who reacts to you, the distribution is a function of your action.

The signal is simple. **The probability moves when your action moves.** `p(they walk away)` moves with the size of your ask. `p(a competitor cuts price)` moves with your price.

- Write the probability as a function of the action. Do not write it as a constant.
- Price three actions: small, medium, and large. Compare them.
- Add the payoff of the other party. A branch that is worse for them than their alternative has `p ≈ 0`. Their alternative matters more than your estimate.
- **Change what they can observe.** In a repeated game a predictable action gets priced in by the other side. If you always concede under pressure, pressure becomes free for them.
- **Deviate only on what you observed.** An estimate from watching a party is worth money. An estimate from a story you told yourself is the most costly habit here.
- It is better to remove a branch than to price it. Use a written deadline, a floor, a deposit, or a milestone payment. A converted premise is true by construction (GNS-006).
- GNS-006 covers a premise that another party's loop owns. The derivation is at `../../../docs/proofs/006-STRUCTURAL-ENFORCEMENT-CROSS-LOOP.md`.
- Do not model an opponent who is not one. A market price, a queue, and the weather do not react to you. Treat them as chance.
