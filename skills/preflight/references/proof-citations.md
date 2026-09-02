# Proof citations for `/genius:preflight`

Operational language for each field. Each field check is a proof's branch trigger. It fires at task start, not mid-loop.

The full proofs ship with the plugin at `../../../docs/proofs/`, relative to this file. Read one there when you need the derivation, not the summary.

Tool names below are examples from one stack. The field names the outcome. The executing agent observes which tool provides it.

## Target branch + stack position (GNS-003)

> "In the genius system, every non-trivial action within an active OODA loop is the smallest reversible step that moves toward the goal."

A wrong-branch commit is not reversible without recovery (stash, detach, restack). Confirm the branch before the first edit. That keeps the step reversible. If a stacking tool is in use, the stack position matters too. An amend on the wrong branch in a stack invalidates downstream restacks.

Example (author's stack): `git branch --show-current`, then `gt log short` when Graphite is authenticated.

Example (C++ repo, no stacking tool): `git branch --show-current` only. Do not mention stack position.

## In-scope files (GNS-001)

> "In the genius system, every non-trivial action is preceded by observation."

"Observed" means one of three things. The file path was named explicitly. Or it was read into context. Or a grep confirmed it. "I assume there is a model at app/models/x.rb" is not observation. If the field needs speculation to fill, observation has not happened yet. Pause and observe.

## Off-limits (GNS-005)

> "Iteration within a stable form is justified if and only if it loads latent potential for a future fork."

Boundary-tool fixes, lint sweeps, and adjacent refactors do not load this task's fork. To name them as off-limits is to ask the GNS-005 question. "Name the fork you are preparing for." If the cleanup loads no fork for the current task, it is tinkering. Exclude it.

Example (author's stack): Packwerk violations surfaced by the change but unrelated to it.

Example (C++ repo): two files each define their own `BACKOFF_DOUBLING` constant. Merging them loads no fork for a sizing-policy task. Leave them.

## Output shape (GNS-002)

> "In the genius system, for every non-trivial action where the goal is not yet achieved, observation recurs after the action."

Iteration without a target shape produces output that overruns the budget (the report's 500-token failures). Name the shape up front: diff, numbered list, file path + summary, or score-first. The shape is the success criterion. Reaching it is how iteration stops.

## Verification gate (GNS-004)

> "Every non-trivial action that depends on a premise requires independent validation of that premise."

The chain says "the refactor is done." That is a premise. Independent validation is a check not derived from the chain. Examples: a passing spec, a clean type check, a `git diff --stat` that matches the in-scope list. Until that check runs and returns the expected signal, "done" is a hypothesis.

Example (author's stack): `bundle exec rspec <spec>`, `srb tc`, `bin/packwerk check`.

Example (C++ repo): `make tests FILTER=<suite>`, `make lint`, `make test-san`. The targets were read from the Makefile, not assumed. In a Python repo the same gate reads `pytest` and `mypy`. Observe which is present.
