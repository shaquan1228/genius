# TCREI prompt anatomy

## The mapping

Google's TCREI is Task, Context, References, Evaluate, Iterate. The shape that ships reliably to agents collapses it to four headers without dropping a pillar:

| TCREI pillar | Where it lives | Why |
|---|---|---|
| **T**ask | `Task` | The outcome, stated once. |
| **C**ontext | `Context` | Observed facts and state. |
| **R**eferences | inside `Context` | Verified paths, links, and sibling patterns are context, not a separate list to drift out of sync. |
| **E**valuate | last step of `Iterate` | An explicit proof gate — the work is stable or better, or it is not done. |
| **I**terate | `Iterate` | Ordered steps, each carrying an executable spring. |

## Section anatomy

**Task** — one imperative sentence. The result the member/system should see, never the commands to get there. "Surface failed bill payment errors to the member in native checkout," not "edit PaymentMethodManager."

**Context** — only what you observed. Verified file paths with line numbers, the sibling that already does it right, the repo, the ticket link. Everything unconfirmed is tagged `[unverified]` so the executing agent re-checks instead of trusting. Assert no environment you did not see — the agent may be local, remote, or in a fresh clone, and a wrong "you are in X" is how a session talks itself into the wrong environment.

**Rules** — invariants the outcome holds: which repo, where the PR lands, what stays out of scope. Constraints on the *result*, not a script.

**Iterate** — numbered steps ordered so each produces what the next consumes: read the reference, apply, review, prove. The final step is the evaluation gate (GNS-004): named specs pass, lint is clean, the review criteria hold. Without it the prompt has no definition of done.

## Observation precedence: never hardcode the branch workflow

The prompt author cannot see the executing environment. Anything the agent can *observe* — which branch tool is authenticated, the working directory, the package manager — must be observed at runtime, not asserted by the author (GNS-001). The repeat offender is branch management.

Two real dispatches hardcoded Graphite. In one, `gt` was unauthenticated and the agent fell back to `git` + `gh`; in the other the rebase worked but the submit step (`gt submit`) had to be improvised. The steps "failed slightly" every time the environment did not match the author's assumption.

Rewrite mechanism into intent + observe-and-fallback:

| Hardcoded (author guessed the environment) | Observation-first (agent chooses) |
|---|---|
| `gt checkout native-billing-pay-failure-error` | Get onto branch `native-billing-pay-failure-error` using whatever branch tooling exists here. |
| `gt sync && gt restack` | Rebase onto latest `main`, resolving conflicts. |
| `gt submit --no-verify` | Open/update the PR — prefer Graphite if authenticated, otherwise plain `git push` + `gh pr create`. |
| `git checkout -b fix/foo` | Create branch `fix/foo` off `main` with the repo's branch tooling. |

State the outcome and, at most, a *preferred* tool with an explicit fallback. Do not enforce one branching workflow the prompt cannot verify is present.

For real excerpts of both the working shape and the portability traps, see `examples.md`.

## Worked template

````
Task
<one imperative sentence — the outcome>

Context
• Repo: <repo>
• Branch: <branch-name>  [unverified if you did not confirm it exists]
• <verified/path/to/file.ext:LINE> — <what is there and why it matters>
• Sibling that does it right: <path> — <the pattern to match>
• Ticket / thread: <link>
• <state only environments/facts you observed>

Rules
• The PR lands on <main/target>. Out of scope: <what not to touch>.
• Match the pattern in <reference> exactly.
• <invariant the result must hold>

Iterate
1. Read <reference> to confirm the pattern.
2. Get onto branch <branch> using whatever branch tooling this environment has (prefer Graphite if authenticated; else git + gh). Rebase onto latest main.
3. Apply the change; add a regression test at <path>.
4. Review the diff against: <criterion>, <criterion>.
5. Evaluate — run <specific specs/lint>; the gate is <what passing means>. Open/update the PR only once it passes.
````
