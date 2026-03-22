# Development Workflow

How to execute coding tasks using TDD and OODA.

## OODA Micro-Loop (Always On)

Every non-trivial step runs through the OODA loop. See `docs/OODA.md` for detailed framework. Repeat this loop after each meaningful result (new evidence, failing test, lint/type error, review feedback).

---

## Process Steps

### 1. Clarify

- Restate the task in one sentence
- Identify unknowns and ask only the critical questions
- Confirm constraints and acceptance criteria

### 2. Plan

- Break work into small verifiable steps
- Identify files/systems likely to change
- Note goals and non-goals
- Prefer event-driven triggers over periodic checks when the product behavior allows it

### 3. Execute With TDD

- Write a failing test for the next behavior
- Implement the smallest change to pass
- Refactor while preserving passing tests
- Repeat until acceptance criteria are satisfied

### 4. Verify

- Run targeted tests first, then broader checks as needed
- Run lint/type/static checks relevant to the changed code
- Confirm user-visible behavior and failure handling

### 5. Publish

- Verify branch scope is single-purpose and reviewable
- Verify branch stack or ancestry is healthy before publish (see `docs/dev/GIT-WORKFLOW.md`)
- Confirm required quality gates pass before publish
- Confirm staged files are only task-relevant
- Push only when explicitly instructed — never push by default

### 6. Review Output

- Summarize what changed and why
- Highlight tradeoffs and any deferred work
- Provide clear follow-up steps when useful
- Use concise status framing: TL;DR, Observed, Decided, Next steps, Blockers
- In summaries, include explicit OODA trace for key decisions when non-trivial tradeoffs exist

---

## Best Practices

1. **Start with tests** - Red → Green → Refactor
2. **Small steps** - Each commit should be a working checkpoint
3. **Verify early** - Run tests after each change, not at the end
4. **Apply OODA** - For non-trivial decisions, run the loop explicitly
5. **Ship incrementally** - Don't wait for perfection

---

For git operations (commits, worktrees, stacks), see `docs/dev/GIT-WORKFLOW.md`.
