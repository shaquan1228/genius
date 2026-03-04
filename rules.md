# Rules

This file is language-agnostic. Apply these defaults in Ruby, Python, and other languages unless project-local rules override them.

## Coding

- Keep methods/functions small and focused on one behavior.
- Keep classes/modules small and composable.
- Prefer straightforward control flow over hidden indirection.
- Use descriptive names for methods, variables, and types.
- Use constants or mappings when they improve clarity and reduce repetition.
- Model failure modes explicitly. Do not assume happy-path-only behavior.

## Design

- Prefer clear boundaries and stable interfaces.
- Keep domain logic close to domain models or core modules.
- Avoid over-engineering and speculative abstractions.
- Favor dependency minimization and use platform defaults where practical.

## Testing

- Follow red-green-refactor.
- Write tests for behavior and returned values before internal details.
- Cover happy path and meaningful edge cases.
- Keep tests fast and deterministic.
- Avoid brittle timing-dependent tests unless strictly required.

## Workflow

- Clarify ambiguity early with concise questions.
- Start with a plan for non-trivial work.
- Implement incrementally and verify each step.
- Run relevant lint/test checks after substantive changes.
- Summarize outcomes and residual risks.

## Source Control Workflow

- Prefer iterative delivery: keep branches and pull requests small, coherent, and sequential.
- Use a stack-aware workflow and keep ancestry healthy before publishing.
- Treat quality gates as required and stage only task-relevant files.
- Never push to remote unless explicitly instructed.

### Stack initialization

When the user asks to "begin working on a stack" (or equivalent), follow this protocol:

1. **Enumerate first.** List all branches in the stack before creating any. Confirm the
   order and parent relationships with the user if unclear.
2. **Create branches idempotently.** For each branch, check out if it already exists,
   otherwise create it:
   ```bash
   git checkout <branch> 2>/dev/null || git checkout -b <branch>
   ```
3. **Register with Graphite.** After each branch is checked out, register it:
   ```bash
   gt track --parent <parent-branch>
   ```
4. **Stay on the leaf branch.** After initializing the full stack, remain on the last
   (deepest) branch and begin work there unless the user specifies otherwise.
5. **No push until done.** Do not push any branch until the user explicitly asks to publish.

## Architecture Patterns (Meta Rules)

- Public Facade First: Prefer package or domain public interfaces before internal implementation calls.
- CQRS Interface Shape: Prefer explicit domain entrypoints such as `Domain.command(input)` for state changes and `Domain.query(filters)` for reads.
- Single Orchestration Owner: Keep each business workflow owned by one layer.
- Thin Async Subscribers: Subscribers should extract event data, trigger domain work, and emit observability.
- Boundary Transformation: Normalize external or raw data at boundary layers before returning to callers.
- Explicit Failure Policy: Define retryable, terminal, and ignorable failures for async and integration flows.
- Context Isolation: Pass explicit inputs and avoid ambient mutable state in handlers.
- Domain Separation: Keep async coordination and domain mutations in the owning domain.
