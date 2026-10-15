# Genius evals

[Inspect AI](https://inspect.aisi.org.uk/) runs repeated baseline/Genius comparisons.
[Inspect SWE](https://meridianlabs-ai.github.io/inspect_swe/) supplies Claude Code and Codex integrations.
Both frameworks use the MIT license. Model calls and compute can cost money.

Inspect owns execution, repeats, model calls, limits, scoring, and logs.
Case authors edit two OCaml files:

- `suite.ml` contains case values and parameter lists.
- `fixtures.ml` contains reusable family builders that generate public files,
  private checks, and reference edits.

Adding 200 timeout cases means adding 200 values, or one `List.init`, to the suite.
It creates no checked-in fixture, grader, or solution files. Python supplies the
Inspect adapter, instruction profiles, agent settings, and hosted execution.

## Check the harness offline

Install OCaml 4.13+ (`ocamlc`), Python 3.12+, [uv](https://docs.astral.sh/uv/getting-started/installation/), Git, and Make.
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
token out of chat. A Hugging Face Inference Providers model needs only that
Hugging Face token. OpenAI and Anthropic models need their own provider API keys;
a ChatGPT or Claude subscription does not supply an API key for Inspect.

Run from a checkout of the completed eval stack, or `main` after both PRs
merge. The private source repository and results bucket already exist for
`shaquan1228`; the launch script safely reuses them. From the repository root:

```sh
uvx --from huggingface_hub==2.2.0 hf auth whoami
export HF_NAMESPACE='shaquan1228'
export EVAL_MODEL='hf-inference-providers/openai/gpt-oss-20b'
sh evals/hf_host.sh
```

That first example runs the Codex harness against a Hugging Face hosted model.
To evaluate the target Codex or Claude models, use `openai/<pinned-model-id>`
with `OPENAI_API_KEY` or `anthropic/<pinned-model-id>` with `ANTHROPIC_API_KEY`.
Set the matching key in your shell or secret manager before launching the Job.
The script selects Codex for Hugging Face and OpenAI models, and Claude Code for
Anthropic models. Set `EVAL_AGENT` and `EVAL_VERSION` to override the agent or
its pinned version.
The first run defaults to one epoch (eight agent sessions) to test the hosted
path. After checking its results, run `EVAL_EPOCHS=5 sh evals/hf_host.sh` for
the full 40-session comparison.

`hf_host.sh` uploads only tracked files from the current Git commit, so commit
changes before running it. It creates a private dataset repository containing
the evaluation source, a private results bucket, and a detached Hugging Face Job.
The Job
runs Inspect and launches a dedicated Hugging Face Sandbox VM for each sample.
Only task files and the selected skill enter that VM; held-out checks stay in
the Job and run against the VM after the agent finishes. The script prints the
Job ID. Watch it at `https://huggingface.co/jobs/shaquan1228/<job-id>` or with:

```sh
uvx --from huggingface_hub==2.2.0 hf jobs logs -f <job-id>
uvx --from huggingface_hub==2.2.0 hf jobs inspect <job-id>
```

The logs command streams output; use `jobs inspect` to confirm the final status.
Native Inspect logs are saved to the private
[`genius-eval-results` bucket](https://huggingface.co/buckets/shaquan1228/genius-eval-results)
under `live/`.

Both profiles share the selected model, agent version, effort, tools, and limits.
Every sample and epoch starts with fresh task files and a fresh agent session.
Codex configuration and session state live under `/tmp/genius-codex`, outside
the measured repository, so harness bookkeeping does not count as agent edits.
The agent's `attempts=1` prevents retries after a failed submission within one
session; epochs provide independent attempts for estimating pass rates.
Agent retries and model-response caching are disabled. Provider transport retries retain Inspect defaults.
Each session allows 40 messages, 50,000 tokens, and 300 seconds.
Task metadata records agent versions and hashes of instructions, fixtures, and the manifest.
Inspect logs record model usage, sample events, answers, errors, and scores.

Compare each task across profiles; require both correctness and scope to pass.
Inspect reports each score separately. Scores are not inferred from agent claims.

## Author cases

`suite.ml` defines the suite with typed family constructors:

```ocaml
open Fixtures

let cases = [
  Receipt.case ~id:"quantity" ~bug:Receipt.Ignore_quantity
    ~examples:[ ([(3., 4)], 12.); ([(3., 0)], 0.) ];
  Preflight.case ~id:"timeout-30" ~initial_timeout:15 ~requested_timeout:30;
  Decision.cheaper ~id:"lower-cost" ~a:10 ~b:8;
]

let () = emit cases
```

A case ID has no registry entry or matching directory. For a larger family:

```ocaml
let cases = List.init 200 (fun i ->
  Preflight.case ~id:(Printf.sprintf "timeout-%d" i)
    ~initial_timeout:15 ~requested_timeout:(30 + i))
```

Family builders generate the buggy project, visible tests, held-out checks, and
reference edits from these values. Receipt expectations are explicit input/output
tables, independent of its reference implementation. Preflight checks compare
both defaults against the requested value and independently test overrides and
invalid input. Decision cases share output schemas by kind, so new IDs and costs
need no Python edits. Add a new builder in `fixtures.ml` for a different task
shape; variations use its existing parameters.

## Execution boundary

The host compiles `fixtures.ml` and `suite.ml` in a temporary directory and reads
the resulting JSON into memory. Compilation and validated case indexes are cached
by source contents; changing the suite, families, or runner invalidates the cache.
No generated files are written into this checkout. Both local checks and the
hosted Job need OCaml 4.13+; the hosted bootstrap installs Debian's `ocaml-nox`.

Inspect receives only public project files, selected skill instructions, and a
case ID. Private checks and reference edits stay in the host's case index; they
are not copied into sample metadata or the agent workspace. Only the offline
scripted test agent applies the reference edits.

`check.sh` is the shared compiler runner. It compiles temporary copies and cleans
up after success or failure, leaving no compiler artifacts in the measured
worktree. A generated workspace can run its visible checks with, for example:

```sh
sh check.sh examples.ml receipt.ml test_receipt.ml
```

After the agent finishes, the grader sends the generated private OCaml checks to
the sandbox through standard input, using the host's trusted runner. A fresh
completion marker appears after every assertion; successful early exits without
that marker fail correctness. Private checks embed their own trusted helper, so
changing visible tests or helpers cannot make the seeded bugs pass. The marker
checks completion; it does not isolate hostile code sharing the grader process.

Scope checks compare the final worktree against its original commit.
They detect agent commits, untracked files, ignored files, and changed instructions.

The four cases cover clear-task completion, known preflight fields, numeric choice, and hindsight after one loss.
Task prompts, sources, and assertions are generated from `suite.ml` and `fixtures.ml`.
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

Python coverage and complexity include all adapter runtime code, harness tests,
and scripted helpers. OCaml checks are verified by compiling and executing the
seeds, solved fixtures, partial fixes, malformed code, and visible test commands;
they are not included in Python coverage or the Python CRAP calculation.
Strict mypy checks the Python modules without type-ignore exceptions; `ocamlc`
type-checks fixture modules and assertions on every execution.
