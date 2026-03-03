# Portable AI Toolkit

This folder contains a portable, language-agnostic style stack for coding agents.

## What It Provides

- Engineer identity and coding principles
- Cross-language rules and workflow
- Role prompts for planning, implementation, and review
- A script that assembles prompts consistently
- A lightweight preflight warning pass

## Quickstart

0) Optional local profile link (for cross-repo reuse):

```bash
bin/setup
```

1) Create a task file:

```text
tmp/ai_task.txt
```

2) Add your task details and acceptance criteria.

3) Run prompt assembly:

```bash
LLM_MODE=print ai/scripts/run-agent.sh implementer tmp/ai_task.txt
```

4) You can also provide task input with stdin or inline text:

```bash
cat tmp/ai_task.txt | LLM_MODE=print ai/scripts/run-agent.sh implementer -
```

```bash
LLM_MODE=print ai/scripts/run-agent.sh implementer --text "Check this repo and suggest top improvements."
```

5) Optionally execute against a provider CLI:

```bash
export LLM_MODE=run
export LLM_CMD='your_llm_cli_command_here'
ai/scripts/run-agent.sh implementer tmp/ai_task.txt
```

## Files

- `identity.md`: engineering identity and defaults
- `rules.md`: language-agnostic coding and testing rules
- `workflow.md`: task execution process
- `checks.md`: light quality checks
- `examples.md`: sample tasks and expected behavior
- `prompts/`: role overlays
- `scripts/`: prompt assembly and preflight checks

## Portability Notes

- This setup does not depend on persistent memory.
- It is provider-agnostic as long as `LLM_CMD` can consume prompt text from stdin.
- Keep task files explicit about outcomes, tests, and failure handling for best results.

## Smoke Test Notes

- Command:
  - `LLM_MODE=print ai/scripts/run-agent.sh implementer tmp/ai_smoke_task.txt`
  - `LLM_MODE=run LLM_CMD='cat' ai/scripts/run-agent.sh implementer tmp/ai_smoke_task.txt`
- Result:
  - Print mode and run mode both returned full assembled prompts.
  - Output size check confirmed non-empty payloads in both modes.
- Tuning note:
  - Prompt quality improves when task input includes acceptance criteria, validation steps, and failure-path expectations.
