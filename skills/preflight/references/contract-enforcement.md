# Hard enforcement (optional)

The skill re-reads the contract before each edit. That is a promise the model keeps, not one the harness enforces. For hard enforcement in Claude Code, wire a `PreToolUse` hook that blocks edits outside the in-scope list.

Sketch, not a drop-in:

1. On step 4, also write the contract to a session-local file, e.g. `.claude/preflight-contract.md`.
2. Add a `PreToolUse` hook matching `Edit|Write` in `.claude/settings.json`.
3. The hook script reads the in-scope list from the contract file. If the tool's `file_path` is not in the list, exit non-zero with a one-line reason. The edit is denied and the reason is surfaced.
4. Remove the contract file when the task ends, or the next session inherits stale scope.

Codex and Cursor have no equivalent hook surface today. There, step 5 of the skill is the only enforcement.
