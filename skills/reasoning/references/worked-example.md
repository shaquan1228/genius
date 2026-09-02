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

## Second example, C++ repo

Task: "Retry the unconfirmed-order resolver job with backoff."

**GNS-001 — observe.**

> `grep -rn "backoff\|retry" src/` → `composition/events/publisher.cpp:443` has `backoff_pause(attempt)`, doubling from 0.25s. `composition/events/consumer.cpp:950` has `retry_delay(attempt)`, same doubling, capped at 30s. Each file defines its own constants. The resolver job at `composition/jobs/resolve_unconfirmed_order.hpp:19` uses a flat `RESOLUTION_RETRY_SECONDS = 30`. Build is a Makefile. Tests are doctest via `make tests`. `.clang-tidy` caps functions at 25 lines.

Two assumptions died: that no backoff existed, and that CMake or gtest was present.

**GNS-005 — name the fork.** Adding doubling backoff to the job loads the fork "jobs share the events layer's retry shape." Extracting a shared backoff header now would load a bigger fork, but the task did not ask for it. Name it, leave it.

**GNS-003 — smallest reversible step.** Replace the flat constant with a doubling delay inside the job. Do not touch publisher or consumer. One file, one function, under the 25-line cap.

**GNS-004 — validate the premise.** Premise: "the job retries with growing delay and stops at the cap." Validator: a doctest case that drives attempts 0 through 8 and asserts the delay sequence. `make tests FILTER=resolve_unconfirmed_order` green. `make lint` clean.

**GNS-002 — iterate to shape.** Target was "diff plus green filtered test." Reached. Stop.

**Report:**

> TL;DR: resolver job now backs off 0.25s doubling to 30s, matching the events layer.
> Observed: two existing backoff loops in publisher/consumer with duplicated constants; flat 30s in the job; Makefile + doctest + clang-tidy.
> Decided: local doubling in the job only. No shared header this PR.
> Next steps: a shared backoff header would remove three copies. Separate task.
> Blockers: none.

**Without the identity:** "Added a `Backoff` utility under `utils/`, refactored publisher and consumer to use it, and wired the job. Ran the full suite, all green." Three files that were off-limits changed. The fork was not named. The full suite is a weaker validator than the filtered case that asserts the delay sequence.
