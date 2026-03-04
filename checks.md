# Light Checks

Use these checks as non-blocking guardrails.

## Task Input Checks

- Task includes acceptance criteria.
- Task includes test/verification expectations.
- Task mentions failure handling or edge-case behavior.

## Output Checks

- Solution is concise and directly addresses requested scope.
- Behavior and return values are explicit.
- Proposed tests validate behavior, not internals.
- Risks and assumptions are called out clearly.
- Framework convention check: prefer framework-native validation and constraint mechanisms over ad-hoc inline error mutation in orchestration code.
- OODA check: Does the response show Observe -> Orient -> Decide -> Act in reasoning and execution updates?

## Delivery Checks

- Commands and verification steps are runnable.
- Changes are incremental and easy to review.
- Residual work is documented.

## Source Control Checks

- Branch scope check: Is the branch or pull request single-purpose and reviewable?
- Stack health check: Is ancestry consistent and ready to publish?
- Gate check: Do required quality checks pass before publish?
- Staging check: Are only task-relevant files staged?

## Architecture and Meta Checks

- Boundary check: Does the solution use a public domain interface first?
- CQRS check: Are state changes invoked via domain commands and reads via domain queries?
- Ownership check: Is orchestration owned by one clear layer?
- Subscriber check: If async, is the subscriber thin (extract, dispatch, observe)?
- Payload contract check: Are event inputs minimal and explicit?
- Failure policy check: Are retryable, terminal, and ignorable paths defined?
- Sprawl check: Is workflow logic diffused across unrelated layers?
- Transformation check: Is external data normalized at a boundary instead of scattered across callers?
- Coupling check: Did cross-domain coupling increase without a clear benefit?
- Decision-loop check: After new evidence, did the plan/next action explicitly update?