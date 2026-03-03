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
