# Examples

Excerpts from prompts that shipped a real result. Each shows the one line to copy or fix. None is a whole prompt.

## Keep doing

- **Task names the outcome in one line.**
  > Make sure we're ready to monitor the new feature.

  Not "edit the analytics service." The outcome leaves the how to the agent.

- **Context folds references in as links and says where to look.**
  > Scan the client-side analytics util `[analytics-util]`; grep for the tracking service — the logic is sprawled, so prioritize the two or three packages that own it.

  Verified pointers plus a search strategy beat a prose description the agent cannot act on.

- **Context names the build file and the sibling, not the language convention.**
  > Build is a hand-written `Makefile`; tests are doctest via `make tests FILTER=<suite>`. Copy `sizing_policy/generics/fixed_fraction.hpp:11` and add the include to `sizing_policies.hpp:6-11`. Nothing autoloads.

  A header-only C++ repo needs the umbrella-include edit spelled out. A Rails reader would assume autoloading.

- **Rules fence scope explicitly.**
  > She means the copy in that one settings component folder only — not any other folder.

  A hard out-of-scope line stops "while I'm here" drift.

- **Iterate ends in a proof gate that defines done.**
  > Check for tests and add them before any code change; commit nothing unless the specs pass locally.

  The gate is the definition of done. Without it, the agent guesses when to stop.

- **Define done as a threshold, not perfection.**
  > A flaky-rate improvement of ≥80% over baseline is commit-worthy; run it five times, ship, let CI confirm.

  A concrete bar prevents the two-hour rabbit hole chasing 100%.

## Portability traps (rewrite before dispatch)

Each of these worked on the author's own machine. Each broke when the same prompt ran in an agent environment that did not match. That gap is the reason for the observation-precedence rewrite. See the rewrite table in `prompt-anatomy.md`.

- **Hardcoded branch tooling.**
  > Use Graphite; all PRs off main, submitted as drafts.

  This assumes Graphite is authenticated here. Where it is not, the step fails until the agent improvises. Rewrite: state the intent ("open the PR off main as a draft"). Name a preferred tool with a fallback.

- **Hardcoded working directory or host.**
  > Run in a worktree from the repo folder on your Desktop using the symlinked worktree command.

  Only the author's laptop has that path and command. Rewrite: "Work in an isolated worktree, however this environment creates one."

- **A one-off environment patch baked in as a rule.**
  > Never stop because of the git host — unset the token and retry.

  A fix for one machine's quirk, shipped to every future reader as law. Rewrite: leave environment fixes to the environment. The prompt states intent, not local workarounds.

- **Test runner assumed from the language.**
  > Run the specs with rspec before committing.

  The target repo was C++. Rewrite: "Run the repo's test target for the touched suite. The gate is green output. Observe the build file for the command."

- **A tool named where an outcome belongs.**
  > plan → work → review → submit (as a chain of specific skill invocations)

  Fine as a hint. A trap as a mandate. A reader without those skills is stuck. Rewrite: name the outcome of each step. Offer the skill as the preferred path, not the only one.
