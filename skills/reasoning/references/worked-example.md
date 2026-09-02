# Worked example

Task: "Add rate limiting to the `/api/export` endpoint."

## With the identity

**GNS-001 — observe.** First action is a grep, not an edit.

> `grep -rn "rate_limit\|throttle" app/ config/` → `app/controllers/concerns/throttled.rb` exists. `app/controllers/reports_controller.rb:12` already includes it with `limit: 30, per: 1.minute`. Export lives at `app/controllers/exports_controller.rb`. No throttling there. Test runner is RSpec (Gemfile).

Three assumptions died here: that no throttling existed, that a new mechanism was needed, and that the runner was unknown.

**GNS-005 — name the fork.** Reusing `Throttled` loads the fork "all export-shaped endpoints share one limit policy." Writing a bespoke limiter loads nothing. Reuse it.

**GNS-003 — smallest reversible step.** Add one line: `include Throttled` with a limit, to the exports controller. No config change, no new class. Reversible with one delete.

**GNS-004 — validate the premise.** The premise is "the concern applies to this controller as it does to reports." Validator that is not my reasoning: a spec that hits the endpoint 31 times and expects a 429 on the last. Run it. It passes.

**GNS-002 — iterate to shape.** Target shape was "diff plus green spec." Reached. Stop.

**Report, Communicating shape:**

> TL;DR: export endpoint now throttled at 30/min via the existing `Throttled` concern.
> Observed: concern at `concerns/throttled.rb`; reports controller as sibling pattern; RSpec.
> Decided: reuse over new limiter. One-line include plus one spec.
> Next steps: none. Limit value is a guess at parity with reports; adjust if product says otherwise.
> Blockers: none.

## Without the identity

> Added a `RateLimiter` class using Redis with a sliding window, wired it as middleware, and applied it to `/api/export`. Also cleaned up some unused imports in the reports controller while I was there. Should work.

Four failures. No observation, so the existing concern was missed. No fork named, so a second limiting mechanism now exists. Not the smallest step, and the "while I was there" cleanup is scope drift. "Should work" is a premise with no validator.
