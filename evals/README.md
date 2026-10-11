# Genius evals

Run the same tasks with and without Genius. No evaluation framework or Python package is required.

## Quick start

Requires Python 3.10+, Git, and macOS or Linux. Test the runner without calling a model:

```sh
python3 -m unittest discover -s evals/tests -p 'test_*.py' -v
python3 evals/run.py --smoke --repeats 2
```

Smoke mode uses a deterministic test double. Its passes say the runner works, not that Genius improves a model.

For real trials, install and authenticate Claude Code. Use a version supporting `--bare` and an exact model ID:

```sh
python3 evals/run.py \
  --agent-command 'python3 evals/adapters/claude.py --model <pinned-model-id> --effort medium' \
  --repeats 3 --timeout 300
```

Replace `<pinned-model-id>` with the model you want to compare. Four tasks and three repeats create 24 model sessions.
The adapter caps each session at 20 turns and $2 estimated API cost. Override its flags inside `--agent-command`.
The provider's cost cap is approximate. Calls use your provider account.

Results are saved to a new temporary directory printed at the end. Use `--output evals/results/run-001` to keep them locally.
The output directory must not exist. Use `--genius-root /path/to/other/checkout` to test another instruction version.

## What runs automatically

- Copy each task into a fresh Git repo on branch `eval` for every trial.
- Shuffle task and variant order using a saved seed. Both variants run once per repeat.
- Keep the model, tools, effort, and limits fixed. Add the selected Genius skill only to its variant.
- Run held-out correctness checks after the agent returns. Detect edits outside each task's allowed files.
- Keep a separate instruction copy for each Genius trial. Fail the trial if those instructions change.
- Save inputs, agent output and traces, grading output, individual records, and `results.jsonl`.
- Write `summary.json` with pass counts, paired results, runtime, and provider-reported cost.

The manifest covers clear-task completion, known preflight fields, a small numeric choice, and a decision review after one loss.
Task prompts and fixtures are in `cases.json` and `fixtures/`. Held-out checks live in `checks.py`, outside agent workspaces.
The suite, instruction bundle, and runner have saved content hashes. Adapter output records CLI version and reported models.
Check reported models for unexpected fallback before comparing results.

## Agent adapter contract

`--agent-command` starts a command without a shell. It receives one JSON request on stdin:

```json
{"task_id":"clear-task","prompt":"...","workspace":"/absolute/path","skill_path":null}
```

Start a fresh agent session in `workspace`. When `skill_path` is supplied, load that skill and its referenced instructions.
Disable existing Genius injections, global instructions, memory, plugins, and other session carryover in both variants.
The included Claude adapter uses [bare mode](https://code.claude.com/docs/en/cli-reference), which skips automatic discovery.
Add another adapter for Codex or Cursor without changing task definitions or scoring.

Return one JSON object on stdout; put diagnostics on stderr:

```json
{"text":"final answer","metrics":{"cost_usd":null,"input_tokens":null,"output_tokens":null,"clarification_tool_calls":null},"metadata":{"agent":"name","model_requested":"pinned-id"}}
```

Extra fields such as `trace` are preserved in the saved output. Missing metrics remain `null`, not zero.
Exit nonzero on provider, permission, or budget failure. Timeouts kill the adapter's process group.
The runner exits nonzero if any trial fails. Failed trials remain in the results and summary.

## What still needs review

Correctness and file scope are checked in code. Question quality, useful reasoning, and decision explanations require human review.
`clarification_tool_calls` counts actual question-tool calls, not every question and not whether a question was unnecessary.
Each result has an empty review field. Use the saved answer and trace; do not count question marks as questions.

These are small regression tasks, not evidence that Genius is better overall. Add representative tasks before drawing broad conclusions.
Repeated runs share one provider account; caching and service load can affect time and cost. Small samples carry substantial noise.
Fresh directories separate task files, not operating-system access. Run agent commands in a disposable container when you need containment.
The Claude adapter permits its fixed file and shell tools; it does not enable a blanket permission bypass.
