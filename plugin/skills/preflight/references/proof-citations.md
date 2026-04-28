# Proof citations for `/genius:preflight`

Per-field operational language. Each field's check is a proof's branch trigger fired at task initiation rather than mid-loop.

## Target branch + stack position — GNS-003

> "In the genius system, every non-trivial step within iteration is the smallest reversible action that advances the goal."

Wrong-branch commits are non-reversible without recovery (stash → detach → restack). Confirming the branch *before* the first edit keeps the step reversible. The Graphite stack position matters because amending the wrong branch in a stack invalidates downstream restacks.

## In-scope files — GNS-001

> "In the genius system, every non-trivial action is preceded by observation."

"Observed" means: the file path was named explicitly, or read into context, or grep-confirmed. Not "I assume there's a model at app/models/x.rb." If the field would require speculation to fill, the observation hasn't happened yet — pause and observe.

## Off-limits — GNS-005

> "Iteration within a stable form is justified if and only if it loads latent potential for a future fork."

Packwerk fixes, lint sweeps, and adjacent refactors do not load *this task's* fork. Naming them as off-limits is the operational form of the GNS-005 question: "name the fork you are preparing for." If the cleanup loads no fork for the current task, it's tinkering — exclude it.

## Output shape — GNS-002

> "In the genius system, non-trivial actions are refined through iteration toward the goal."

Iteration without a target shape produces output that overruns the budget (the report's 500-token failures). Naming the shape upfront — diff, numbered list, file path + summary, score-first — is the iteration's success criterion. Reaching the shape is how iteration stops.

## Verification gate — GNS-004

> "A non-trivial step that depends on a premise requires independent validation of that premise."

The chain says "the refactor is done." That's a premise. Independent validation = something not derived from the chain: a passing spec, a clean `srb tc`, a `git diff --stat` confirming the LOC matches the intent. Until that runs and returns the expected signal, "done" is hypothesis, not knowledge.
