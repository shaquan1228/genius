# Genius evals

Evaluate instruction variants with [Inspect AI](https://inspect.aisi.org.uk/)
and [Inspect SWE](https://meridianlabs-ai.github.io/inspect_swe/).
The bundled datasets are a four-case smoke suite and the 164-problem HumanEval+ benchmark.
Use `python -m evals.python.integrations.hugging_face.compare --help` to compare variants or reuse saved runs.

Comparison requests use schema 2: `variants` contains two or more uniquely named
`VariantRequest` values; `baseline` selects one name. A variant's `result_ref` reuses
compatible saved evidence. Pass request JSON as `COMPARISON_REQUEST` or a CLI file argument.
Reports expose `runs` and per-variant `comparisons`. `compare_summaries` accepts numeric
`RunSummary` values from other runners; `compare_runs` reads compatible native logs.
Single-run preparation and validation use `evaluation.prepare_run` and `evaluation.validate_run`.
Accuracy/time verdicts require an explicit accuracy tolerance and describe observed means.
The `benchmark` PR label launches independent HF jobs and reports accuracy and mean task time.

## Source layout

| Path | Contains |
| --- | --- |
| `ocaml/` | Domain types, validation, grading, and `.ocamlformat` configuration |
| `ocaml/tools/` | Build executables for source provenance and binding generation |
| `python/` | Dataset loading, evaluation workflows, and integrations |
| `python/kernel/` | The installed Python package `kernel` and its binding-generation support |
| `python/tests/` | Python tests and their `conftest.py` collection hook |

The shared Makefile, Dune project, and Python package configuration live at this root.

## Check the harness offline

Install opam, [uv](https://docs.astral.sh/uv/), Git, Make, and a C compiler.
Run from the repository root:

```sh
opam init --bare --no-setup
uv sync --project evals --python 3.12 --extra dev --locked --inexact
make -C evals setup-kernel
opam install --switch genius-kernel-414 --yes ocamlformat.0.29.0
opam exec --switch=genius-kernel-414 -- make -C evals check
```

The offline checks use mock models and local sandboxes; no API keys are needed.
Use `make -C evals format` under the same opam switch to apply formatting.

## Validate references

These commands make no model calls or hosted requests:

```sh
opam exec --switch=genius-kernel-414 -- uv run --project evals python -m evals.python.integrations.smoke
opam exec --switch=genius-kernel-414 -- uv run --project evals python -m evals.python.integrations.evalplus.benchmarks info
opam exec --switch=genius-kernel-414 -- uv run --project evals python -m evals.python.integrations.evalplus.benchmarks validate --limit 3
```

HumanEval+ downloads are pinned and checksum verified by `python/datasets/humanevalplus.py`.
Its `HumanEval/32` reference
fails the pinned official evaluator; full reference validation therefore exits nonzero.

## Run on Hugging Face

Hosted runs incur model and compute charges. Authenticate with a Hugging Face account
that has Jobs credit, then set the matching `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`
in your shell for direct provider models.

```sh
uvx --from huggingface_hub==2.2.0 hf auth login
export HF_NAMESPACE='<your-username-or-organization>'
export EVAL_MODEL='openai/<pinned-model-id>'
export EVAL_DATASET='humanevalplus'
export EVAL_LIMIT=3
export EVAL_EPOCHS=1
sh evals/bin/hf_host.sh
```

The launcher uploads committed files, streams Job logs, and saves results to the
private `genius-eval-results` bucket in your HF namespace. Commit changes before launching.

| Setting | Usage |
| --- | --- |
| `EVAL_MODEL` | `openai/...`, `anthropic/...`, or `hf-inference-providers/...` |
| `EVAL_DATASET` | `smoke` (default) or `humanevalplus` |
| `EVAL_LIMIT` | Maximum cases per profile; omit for the full dataset |
| `EVAL_SAMPLE_IDS` | JSON list of unique case IDs; use instead of `EVAL_LIMIT` |
| `EVAL_EPOCHS` | Repeats per case; the hosted launcher defaults to `1` |
| `EVAL_COST_LIMIT` | Model cost cap per sample and epoch, default `$0.25`; excludes compute |
| `EVAL_MODEL_COST` | JSON prices per million tokens: `input`, `output`, `input_cache_write`, `input_cache_read` |
| `EVAL_MAX_SAMPLES` | Concurrent samples, `1`–`16`; default `1` |
| `EVAL_AGENT`, `EVAL_VERSION` | Override the automatically selected agent and its pinned version |
| `EVAL_INSTRUCTION_DELIVERY` | `files` (default), `manifest`, or `inline` |
| `EVAL_DELIVERIES` | JSON list of delivery modes for a serial diagnostic comparison |
| `EVAL_JOB_TIMEOUT` | Hosted Job deadline, default `4h` |

HF provider routes require all four exact prices in `EVAL_MODEL_COST` and use your
HF token. Direct OpenAI and Anthropic routes can use Inspect's built-in pricing.
Cost caps are checked after each response, so the final response can exceed the cap.
Delivery diagnostics currently support reasoning cases.

Inspect logs retain scores, verifier evidence, crashes, and cutoffs. Parent logs
include sample lifecycle events and a final completeness report.

## Use from Python

Run Python under the same opam switch as the setup commands.

```python
from evals.python import datasets

dataset = datasets.load_dataset(selection="smoke")
cases = datasets.list_cases(selection=dataset)
```

For dataset authoring, start with [datasets/smoke.py](python/datasets/smoke.py).
Use `datasets.compile_dataset(cases=...)` to work with your own declarations.

Each domain component owns its type and constructors in its OCaml `.ml` and `.mli` files.
The public binding interface is generated from those compiled owner contracts.
`ocaml/genius_evals_kernel.ml` is the sole list of public modules; Dune derives compiled
interface dependencies from its module aliases and discovers library sources automatically.
The binding tools resolve compiler type paths and render supported declarations independently
of the kernel's owner conventions, which are checked in the kernel tests. The build supplies
the library identity, Python package, and exception exports; `_bridge.py` owns error conversion.
When rendering multiple interfaces, the adapter supplies their compiled modules under its
`native` namespace. A single interface binds directly against that namespace.
Constrained records and alternatives are private:
Python authors use `Task.create(...)`, `Verifier.create(...)`, `Instruction.create(...)`,
`TextRule.create(...)`, and `Rubric.create(...)`. These factories return immutable native
values after checking their invariants. Raw representations stay inside the OCaml
implementation; projections and graders accept the validated values directly.

`Rubric.create(expected=...)` accepts a checked `Response`. Create responses with
`Response.create(fields=[ResponseField.create(name="choice", value=ResponseValue.create(string="B"))])`.
Structured reference completions use `Completion.create(structured=...)`; fields remain readable through
`response.fields`. Resource resolution returns a new validated task and preserves the
original declaration.

Alternative factories require exactly one named input: `Content.create(inline="text")` or
`Content.create(resource="checker")`, and `Completion.create(plain="done")` or
`Completion.create(structured=response)`. The OCaml owner checks that contract; generated
Python overloads reject both or neither input during type checking. Named payloads remain
available for inspection, such as `content.text` and `completion.response`.

The `kernel` package exports types and exceptions. Operations belong to those types:
`Case.create(task=...)`, `Task.grade(task=..., response=..., outcome=...)`,
`Fixture.files(fixture=...)`, and `Experiment.resolve(...)`. Compiled source provenance
is available through the native `Kernel.current` value and its `sources` collection.
Bindings adapt native results and named calls without duplicating domain policy.

Inspect calls loaded skill files `documents`; their path-to-bytes mapping stays local
to the file and SDK adapter. `Instruction` remains the core task's skill and prompt.

```python
from kernel import ValidationError, Verifier

try:
    Verifier.create(
        inputs=("solution.py",), files=(), tools=(), command=(), stdin="", timeout_seconds=0
    )
except ValidationError as error:
    for issue in error.issues:
        print(issue.code, issue.field, issue.message, tuple(issue.values))
```

The OCaml constructors return typed `result` values. The generated native Python adapter
unwraps successful results and raises `ValidationError` with native issues on rejected
input. A verifier harness malfunction raises `GradingError`, retaining its native failure
in `error.error`; an incorrect or malformed candidate answer receives an unsuccessful
correctness score. Domain objects and errors cross the in-process bridge directly.
Runtime JSON decoding remains at external text boundaries such as candidate responses.

The pinned bridge patch preserves private-record construction restrictions, distinct
polymorphic result parameters, and domain type context while adapting result payloads.
