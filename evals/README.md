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

## Compare real agents

Install Docker with Compose and start its daemon.
Set `ANTHROPIC_API_KEY` for Claude or `OPENAI_API_KEY` for Codex.
Inspect SWE downloads the pinned agent binary inside each Docker sandbox.
Its model bridge uses Inspect credentials, rather than existing agent subscription sessions.

Install dependencies from the repository root:

```sh
uv sync --project evals --locked
```

Run both profiles with Claude Code:

```sh
uv run --project evals inspect eval evals/tasks.py \
  --model 'anthropic/<pinned-model-id>' --epochs 5 --max-samples 1 \
  --log-dir evals/results/live
```

Replace the model placeholder with an exact provider model ID.
Four tasks, two profiles, and five epochs create 40 independent agent sessions.
The agent's `attempts=1` prevents retries after a failed submission within one session;
epochs provide independent attempts for estimating pass rates.
Claude Code defaults to version `2.1.278`; override it with `-T version=<exact-version>`.

Run the same tasks with Codex:

```sh
uv run --project evals inspect eval evals/tasks.py \
  --model 'openai/<pinned-model-id>' -T agent=codex -T version=0.137.0 \
  --epochs 5 --max-samples 1 --log-dir evals/results/live
```

Both profiles share the selected model, agent version, effort, tools, and limits.
Every sample and epoch starts with fresh task files and a fresh agent session.
Agent retries and model-response caching are disabled. Provider transport retries retain Inspect defaults.
Each session allows 40 messages, 50,000 tokens, and 300 seconds.
Task metadata records agent versions and hashes of instructions, fixtures, and the manifest.
Inspect logs record model usage, sample events, answers, errors, and scores.

Open the reports:

```sh
uv run --project evals inspect view --log-dir evals/results/live
```

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

## Automate runs

[The GitHub Actions workflow](../.github/workflows/evals.yml) runs offline checks on relevant pull requests and main updates.
It uploads coverage, complexity, test reports, and native offline evaluation logs.

For real comparisons, manually dispatch **Genius evals** with an agent, exact model ID, version, and epoch count.
Configure the matching repository secret: `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`.
The comparison job starts after quality checks and uploads native logs even after failures.
Its total runtime limit is 45 minutes; individual sessions retain the limits above.
Model calls run only through manual dispatch, using the configured provider account.
