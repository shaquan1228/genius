# Genius evals

[Inspect AI](https://inspect.aisi.org.uk/) runs repeated baseline/Genius comparisons.
[Inspect SWE](https://meridianlabs-ai.github.io/inspect_swe/) supplies Claude Code and Codex integrations.
Both frameworks use the MIT license. Model calls and compute can cost money.

Inspect owns execution, repeats, model calls, limits, scoring, and logs.
`ocaml/suite.ml` is a pure list of eval definitions. Each definition explicitly composes
its starting project, task, checks, edit scope, and offline reference. Adding cases
adds values; it creates no checked-in fixture, grader, or solution files.

The code is split by language. `ocaml/` defines cases; `python/` runs them.
One transport module on each side is the only bridge between the two:

```text
ocaml/*.ml  ──►  ocaml/transport.ml  ──JSON──►  python/transport.py  ──►  python/*.py
 (values)         (sole encoder)                 (sole decoder:            (immutable
                                                  immutable Case)           cases only)
```

The OCaml modules have separate responsibilities:

| Module | Owns |
| --- | --- |
| `fixture.mli` / `fixture.ml` | Abstract immutable file collections, duplicate detection, explicit overlays |
| `fixtures.ml` | Parameterized starting projects and their visible tests |
| `check.ml` | Expected behavior and private assertion generation |
| `task.ml` | Prompts and selected skills |
| `reference.ml` | Known edits and replies for offline harness verification |
| `eval.ml` | Case assembly with explicit edit scope |
| `suite.ml` | Pure case declarations |
| `transport.ml` | JSON encoding for Python and the executable exporter entry point |
| `check.sh` | Compiler runner shared by export, visible tests, and grading |

`python/transport.py` is the only Python module that reads OCaml sources, runs
the compiler, writes OCaml code, or decodes the export. It returns frozen `Case`
values: tuples and read-only mappings, safe to cache and share. Each case's
`checks` is a tagged union, `code` or `answer`; Python branches on its type, never
on a string, so a new OCaml answer kind needs no Python change. Other Python
modules adapt those cases to Inspect and handle agent sessions, scoring, logs,
and Hugging Face execution. OCaml domain modules have no JSON or Inspect
dependencies. `python/tests/test_boundary.py` enforces both rules.

## Check the harness offline

Install OCaml 4.13+ (`ocamlc`), Python 3.12+, [uv](https://docs.astral.sh/uv/getting-started/installation/), Git, and Make.
From the repository root:

```sh
make -C evals check
```

This installs locked dependencies, checks strict typing, runs tests, and enforces CRAP ≤5.
`make -C evals lint-ocaml` compiles the OCaml modules with every warning as an error.
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

A suite declares the parts of a case explicitly:

```ocaml
let cases = [
  Eval.case ~id:"quantity"
    ~fixture:(Fixtures.Receipt.fixture ~bug:Ignore_quantity)
    ~task:Task.Receipt.fix_total
    ~checks:Check.Receipt.(totals [
      expect ~items:[ item ~price:3.0 ~quantity:4 ] ~total:12.0;
      expect ~items:[ item ~price:3.0 ~quantity:0 ] ~total:0.0;
    ])
    ~allowed_files:["receipt.ml"]
    ~reference:Reference.receipt;
]
```

The fixture does not choose the prompt, expectations, reference answer, or edit
scope. Scope is declared independently of reference edits. A suite may reuse a
fixture with different tasks or checks. `Fixture.of_files` rejects duplicate
paths; `Fixture.overlay base overrides` explicitly replaces matching paths and
leaves both inputs unchanged. `Eval.case` rejects checks that read files missing
from the fixture and reference edits outside `allowed_files`; the error names the
case and the files.

Use helpers inside a suite to describe larger parameter sets:

```ocaml
let timeout_case i =
  let requested = 30 + i in
  Eval.case ~id:(Printf.sprintf "timeout-%d" i)
    ~fixture:(Fixtures.Preflight.fixture ~timeout:15)
    ~task:(Task.Preflight.change_timeout ~initial:15 ~requested)
    ~checks:(Check.Preflight.defaults ~timeout:requested)
    ~allowed_files:["config.ml"; "client.ml"]
    ~reference:(Reference.preflight ~timeout:requested)

let cases = List.init 200 timeout_case
```

A new starting-project shape belongs in `ocaml/fixtures.ml`; a new property belongs in
`check.ml`. Prompts live in `task.ml`. Reference edits live in `reference.ml` and
are used only by offline scripted agents. Case IDs have no matching directory or
Python registry entry. The `Check.choice` constructor uses the closed `A | B`
type, while decision replies and expected values are separate explicit inputs.

## Execution boundary

The host compiles the fixed OCaml module set in a temporary directory.
`ocaml/transport.ml` consumes `Suite.cases` and emits JSON; `python/transport.py`
decodes that output into memory. Importing `Suite` itself has no output or
execution side effects. Compilation and validated case indexes are cached
by source contents; changing any module, interface, or the runner invalidates
the cache.
No generated files are written into this checkout. Both local checks and the
hosted Job need OCaml 4.13+; the hosted bootstrap installs Debian's `ocaml-nox`.

Inspect receives only public project files, selected skill instructions, and a
case ID. Private checks and reference edits stay in the host's case index; they
are not copied into sample metadata or the agent workspace. Only the offline
scripted test agent applies the reference edits.

`ocaml/check.sh` is the shared compiler runner. It compiles temporary copies and cleans
up after success or failure, leaving no compiler artifacts in the measured
worktree. A generated workspace can run its visible checks with, for example:

```sh
sh check.sh receipt.ml test_receipt.ml
```

After the agent finishes, the grader sends the generated private OCaml checks to
the sandbox through standard input, using the host's trusted runner. A fresh
completion marker appears after every assertion; successful early exits without
that marker fail correctness. Private checks contain independent assertions, so changing visible tests or the
agent's copy of the runner cannot make the seeded bugs pass. The marker
checks completion; it does not isolate hostile code sharing the grader process.

Scope checks compare the final worktree against its original commit.
They detect agent commits, untracked files, ignored files, and changed instructions.

The four cases cover clear-task completion, known preflight fields, numeric choice, and hindsight after one loss.
The suite composes sources, prompts, and assertions from their respective modules.
Reply checks compare each expected field with its exact JSON type and bound the reason;
they do not judge explanation quality.
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
