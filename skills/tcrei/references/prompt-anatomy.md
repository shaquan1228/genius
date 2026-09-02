# TCREI prompt anatomy

## The mapping

Google's TCREI is Task, Context, References, Evaluate, Iterate. The shape that ships reliably to agents collapses it to four headers. No pillar is dropped.

| TCREI pillar | Where it lives | Why |
|---|---|---|
| **T**ask | `Task` | The outcome, stated once. |
| **C**ontext | `Context` | Observed facts and state. |
| **R**eferences | inside `Context` | Verified paths, links, and sibling patterns are context. A separate list drifts out of sync. |
| **E**valuate | last step of `Iterate` | An explicit proof gate. The work is stable or better, or it is not done. |
| **I**terate | `Iterate` | Ordered steps. Each carries an executable spring. |

## Section anatomy

**Task.** One imperative sentence. State the result the member or system sees. Do not state the commands to get there. "Surface failed bill payment errors to the member in native checkout," not "edit PaymentMethodManager."

**Context.** Only what you observed. Verified file paths with line numbers. The sibling that already does it right. The repo. The ticket link. Tag everything unconfirmed `[unverified]`, so the executing agent re-checks instead of trusting. Do not assert an environment you did not see. The agent may be local, remote, or in a fresh clone. A wrong "you are in X" is how a session talks itself into the wrong environment.

**Rules.** Invariants the outcome holds: which repo, where the PR lands, what stays out of scope. Constraints on the result, not a script.

**Iterate.** Numbered steps. Each step produces what the next consumes: read the reference, apply, review, prove. The final step is the evaluation gate (GNS-004). Named specs pass. Lint is clean. The review criteria hold. Without it, the prompt has no definition of done.

## Observation precedence: do not hardcode the branch workflow

The prompt author cannot see the executing environment. The agent can observe which branch tool is authenticated, the working directory, and the package manager. Those must be observed at runtime, not asserted by the author (GNS-001). The repeat offender is branch management.

Two real dispatches hardcoded Graphite. In one, `gt` was unauthenticated and the agent fell back to `git` + `gh`. In the other, the rebase worked but the submit step (`gt submit`) had to be improvised. The steps "failed slightly" every time the environment did not match the author's assumption.

Rewrite mechanism into intent plus observe-and-fallback:

| Hardcoded (author guessed the environment) | Observation-first (agent chooses) |
|---|---|
| `gt checkout native-billing-pay-failure-error` | Get onto branch `native-billing-pay-failure-error` with the branch tooling present here. |
| `gt sync && gt restack` | Rebase onto latest `main`. Resolve conflicts. |
| `gt submit --no-verify` | Open or update the PR. Prefer Graphite if authenticated. Otherwise use `git push` + `gh pr create`. |
| `git checkout -b fix/foo` | Create branch `fix/foo` off `main` with the repo's branch tooling. |

State the outcome. Name at most one preferred tool with an explicit fallback. Do not enforce a branching workflow the prompt cannot verify is present.

For real excerpts of the working shape and the portability traps, see `examples.md`.

## Worked template

````
Task
<one imperative sentence: the outcome>

Context
• Repo: <repo>
• Branch: <branch-name>  [unverified if you did not confirm it exists]
• <verified/path/to/file.ext:LINE>: <what is there and why it matters>
• Sibling that does it right: <path>: <the pattern to match>
• Ticket / thread: <link>
• <state only environments and facts you observed>

Rules
• The PR lands on <main/target>. Out of scope: <what not to touch>.
• Match the pattern in <reference> exactly.
• <invariant the result must hold>

Iterate
1. Read <reference> to confirm the pattern.
2. Get onto branch <branch> with the branch tooling this environment has (prefer Graphite if authenticated; else git + gh). Rebase onto latest main.
3. Apply the change. Add a regression test at <path>.
4. Review the diff against: <criterion>, <criterion>.
5. Evaluate: run <specific specs/lint>. The gate is <what passing means>. Open or update the PR only once it passes.
````
