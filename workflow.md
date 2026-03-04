# Workflow

Use this process for coding tasks across languages and frameworks.

## OODA Micro-Loop (Always On)

- Observe: State the latest facts, signals, and constraints before each step.
- Orient: Name the governing pattern, risks, and tradeoffs for this step.
- Decide: Choose the next smallest reversible action.
- Act: Execute, validate, and capture what changed.
- Repeat this loop after each meaningful result (new evidence, failing test, lint/type error, review feedback).

## 1) Clarify

- Restate the task in one sentence.
- Identify unknowns and ask only the critical questions.
- Confirm constraints and acceptance criteria.

## 2) Plan

- Break work into small verifiable steps.
- Identify files/systems likely to change.
- Note goals and non-goals.
- Prefer event-driven triggers over periodic checks when the product behavior allows it.

## 3) Execute With TDD

- Write a failing test for the next behavior.
- Implement the smallest change to pass.
- Refactor while preserving passing tests.
- Repeat until acceptance criteria are satisfied.

## 4) Verify

- Run targeted tests first, then broader checks as needed.
- Run lint/type/static checks relevant to the changed code.
- Confirm user-visible behavior and failure handling.

## 5) Stack Initialization (when starting stacked work)

When beginning a stacked PR workflow:

1. Enumerate all planned branches and their parent order before creating any.
2. Create each branch idempotently:
   ```bash
   git checkout <branch> 2>/dev/null || git checkout -b <branch>
   ```
3. Register each branch with Graphite:
   ```bash
   gt track --parent <parent-branch>
   ```
4. Remain on the leaf branch. Do not push until explicitly instructed.

## 6) Publish

- Verify branch scope is single-purpose and reviewable.
- Verify branch stack or ancestry is healthy before publish.
- Confirm required quality gates pass before publish.
- Confirm staged files are only task-relevant.
- Push only when explicitly instructed — never push by default.

## 7) Review Output

- Summarize what changed and why.
- Highlight tradeoffs and any deferred work.
- Provide clear follow-up steps when useful.
- Use concise status framing: TL;DR, Observed, Decided, Next steps, Blockers.
- In summaries, include explicit OODA trace for key decisions when non-trivial tradeoffs exist.