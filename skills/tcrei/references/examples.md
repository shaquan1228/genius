# Examples

Excerpts distilled from prompts that shipped a real result — the one line worth copying or fixing, never a whole prompt.

## Keep doing

- **Task names the outcome in one line.**
  > Make sure we're ready to monitor the new feature.

  Not "edit the analytics service." The outcome leaves the *how* to the agent.

- **Context folds references in as links and says where to look.**
  > Scan the client-side analytics util `[analytics-util]`; grep for the tracking service — the logic is sprawled, so prioritize the two or three packages that own it.

  Verified pointers plus a search strategy beat a prose description the agent cannot act on.

- **Rules fence scope explicitly.**
  > She means the copy in that one settings component folder only — not any other folder.

  A hard out-of-scope line is what stops "while I'm here" drift.

- **Iterate ends in a proof gate that defines done.**
  > Check for tests and add them before any code change; commit nothing unless the specs pass locally.

  The gate *is* the definition of done — without it the agent guesses when to stop.

- **Define done as a threshold, not perfection.**
  > A flaky-rate improvement of ≥80% over baseline is commit-worthy; run it five times, ship, let CI confirm.

  A concrete bar prevents the two-hour rabbit hole chasing 100%.

## Portability traps (rewrite before dispatch)

Each of these shipped fine on the author's own machine, then broke the moment the same prompt ran in an agent's environment that did not match. That gap is the entire reason for the observation-precedence rewrite (see the rewrite table in `prompt-anatomy.md`).

- **Hardcoded branch tooling.**
  > Use Graphite; all PRs off main, submitted as drafts.

  Assumes Graphite is authenticated here. Dispatched somewhere it is not, the step fails until the agent improvises. → State the intent ("open the PR off main as a draft") plus a preferred tool *with* a fallback.

- **Hardcoded working directory or host.**
  > Run in a worktree from the repo folder on your Desktop using the symlinked worktree command.

  A path and a command only the author's laptop has. → "Work in an isolated worktree, however this environment creates one."

- **A one-off environment patch baked in as a rule.**
  > Never stop because of the git host — unset the token and retry.

  A fix for one machine's quirk, shipped to every future reader as law. → Leave environment fixes to the environment; the prompt states intent, not local workarounds.

- **A tool named where an outcome belongs.**
  > plan → work → review → submit (as a chain of specific skill invocations)

  Fine as a hint, a trap as a mandate — a reader without those skills is stuck. → Name the outcome of each step; offer the skill as the preferred path, not the only one.
