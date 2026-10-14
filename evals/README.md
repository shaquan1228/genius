# Genius evals

[Inspect AI](https://inspect.aisi.org.uk/) runs repeated baseline/Genius comparisons.
[Inspect SWE](https://meridianlabs-ai.github.io/inspect_swe/) supplies Claude Code and Codex integrations.
Both frameworks use the MIT license. Model calls and compute can cost money.

Inspect owns execution, repeats, model calls, limits, scoring, and logs.
This package supplies task data, instruction profiles, agent settings, and graders.

## Check the harness offline

Install Python 3.12+, [uv](https://docs.astral.sh/uv/getting-started/installation/), Git, and Make.
From the repository root:

```sh
make -C evals check
```

This installs locked dependencies, checks strict typing, runs tests, and enforces CRAP ≤5.
Tests exercise Inspect's real engine with its mock model and scripted test agents.
They use temporary local sandboxes, requiring no Docker or API keys.
Scripted passes verify the harness; they do not measure Genius performance.

Reports and native offline logs are saved under `evals/results/`.

## Run live comparisons on Hugging Face

Create a [Hugging Face account](https://huggingface.co/join) with a positive Jobs
credit balance. Authenticate from the shared workspace with
`uvx --from huggingface_hub==2.2.0 hf auth login`; the browser login keeps the
token out of chat. Set the provider API key in your shell or secret manager.
A ChatGPT or Claude subscription does not supply an API key for Inspect.

From the repository root, select your Hugging Face namespace and an exact model ID:

```sh
export HF_NAMESPACE='your-username'
export EVAL_MODEL='openai/<pinned-model-id>'
# Set OPENAI_API_KEY in your shell or secret manager.
sh evals/hf_host.sh
```

For Claude, use `anthropic/<pinned-model-id>` and `ANTHROPIC_API_KEY`.
The script selects Codex for OpenAI models and Claude Code for Anthropic models;
set `EVAL_AGENT` and `EVAL_VERSION` to override the agent or its pinned version.
The first run defaults to one epoch (eight agent sessions) to test the hosted
path. Set `EVAL_EPOCHS=5` for the full 40-session comparison.

`hf_host.sh` creates a private dataset repository containing the evaluation
source, a private results bucket, and a detached Hugging Face Job. The Job
runs Inspect and launches a dedicated Hugging Face Sandbox VM for each sample.
Only task files and the selected skill enter that VM; held-out checks stay in
the Job and run against the VM after the agent finishes. The script prints the
Job ID. Watch it at `https://huggingface.co/jobs/<namespace>/<job-id>` or with
`uvx --from huggingface_hub==2.2.0 hf jobs logs -f <job-id>`.
Native Inspect logs are saved to `hf://buckets/<namespace>/genius-eval-results/live/`.

Both profiles share the selected model, agent version, effort, tools, and limits.
Every sample and epoch starts with fresh task files and a fresh agent session.
The agent's `attempts=1` prevents retries after a failed submission within one
session; epochs provide independent attempts for estimating pass rates.
Agent retries and model-response caching are disabled. Provider transport retries retain Inspect defaults.
Each session allows 40 messages, 50,000 tokens, and 300 seconds.
Task metadata records agent versions and hashes of instructions, fixtures, and the manifest.
Inspect logs record model usage, sample events, answers, errors, and scores.

Compare each task across profiles; require both correctness and scope to pass.
Inspect reports each score separately. Scores are not inferred from agent claims.

## Module boundaries

| Module | Responsibility |
| --- | --- |
| `cases.py` | Validate manifest fields and task identifiers |
| `profiles.py` | Build sample files, prompts, and content hashes |
| `agents.py` | Configure native Inspect SWE integrations |
| `tasks.py` | Register profiles, shared limits, and metadata |
| `workspace.py` | Initialize sandboxes and detect changed files |
| `answers.py` | Validate strict decision output schemas |
| `scoring.py` | Combine independent correctness and scope checks |
| `hf_job.py` | Run both profiles in a hosted Hugging Face Job |
| `hf_sandbox.py` | Give each sample a dedicated Hugging Face Sandbox VM |
| `heldout/` | Check code against expectations after the agent finishes |
| `tests/` | Exercise graders and the native Inspect engine offline |

The manifest names each coding case's held-out check. The same runner executes
every check inside the sandbox after the agent finishes; adding a case needs no
new scorer branch or verifier registry entry. The checks run agent-produced code
inside that sandbox, never on the grading host.
Scope checks compare the final worktree against its original commit.
They detect agent commits, untracked files, ignored files, and changed instructions.

The four cases cover clear-task completion, known preflight fields, numeric choice, and hindsight after one loss.
Task prompts and fixtures live in `cases.json` and `fixtures/`.
Decision schemas check selected conclusions and bounded explanations, not explanation quality.
Question usefulness and reasoning quality require human review of saved traces.
These small regression tasks do not establish that Genius improves performance overall.

## Enforce CRAP ≤5

The standard [CRAP formula](https://pypi.org/project/pytest-crap/) is:

```text
CRAP = complexity² × (1 − coverage)³ + complexity
```

`make check` requires 100% statement and branch coverage using coverage.py.
Xenon's rank-A gate requires every function's cyclomatic complexity to be at most five.
At full coverage, CRAP equals complexity, so those gates enforce CRAP ≤5.
Radon exports measured complexity to `results/complexity.json`.

Coverage and complexity include all authored runtime code, held-out checks, tests, and scripted helpers.
Pre-existing buggy fixture data is excluded from the quality gate.
Strict typing checks the same authored modules without type-ignore exceptions.
