# Genius evals

Evaluate instruction variants with [Inspect AI](https://inspect.aisi.org.uk/)
and [Inspect SWE](https://meridianlabs-ai.github.io/inspect_swe/).
The bundled smoke suite covers structured answers and repository edits.
HumanEval+ and PokerBench are downloaded on demand from pinned sources.
Use `uv run --project evals python -m evals.python.integrations.hugging_face.compare --help`
to compare variants or reuse saved runs.

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
| `python/` | Dataset loading, evaluation workflows, and integrations |
| `python/datasets/` | Smoke declarations and benchmark adapters |
| `python/tests/` | Python tests and their `conftest.py` collection hook |

The Genius Bench kernel owns task validation and grading. The Python package is
installed as `genius-bench-kernel` and imported as `kernel`.
[Genius Bench](https://github.com/shaquan1228/genius-bench)

## Check the harness offline

Install [uv](https://docs.astral.sh/uv/), Git, Make, and a C compiler and linker.
Setup uses CPython 3.12. The lockfile pins Genius Bench to a Git commit, so the
first install builds the Python binding from source. Maturin can provision Rust
when Cargo is unavailable. Run from the repository root.

```sh
make -C evals setup
make -C evals check
make -C evals check-install
```

The checks use mock models and local sandboxes and require no API keys.
Inspect can download tokenizer data on the first run.
`check-install` installs the built package outside the checkout, runs the smoke
references, and reports the kernel version and source hash alongside install
measurements. Use `make -C evals format` to apply formatting.

With Docker running, use `uv run --project evals pytest evals/tests/docker.py`
to check three offline container evals and candidate/grader isolation.
The container configuration disables networking. Live CLI agents need separate
proxy setup. [Container configuration](docker/compose.yaml)

The subprocess `local` backend is for trusted code. Docker shares its host
kernel, and workspace volumes have no disk quota.

## Validate references

These commands make no model calls. HumanEval+ validation downloads the pinned
dataset on first use and checks its checksum.

```sh
uv run --project evals python -m evals.python.integrations.smoke
uv run --project evals python -m evals.python.integrations.evalplus.benchmarks info
uv run --project evals python -m evals.python.integrations.evalplus.benchmarks validate --limit 3
```

Full HumanEval+ reference validation exits nonzero because the `HumanEval/32`
reference fails the pinned official evaluator.

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
evals/bin/huggingface-run
```

The launcher uploads committed files, streams Job logs, and saves results to the
private `genius-eval-results` bucket in your HF namespace. Commit changes before launching.

| Setting | Usage |
| --- | --- |
| `EVAL_MODEL` | `openai/...`, `anthropic/...`, or `hf-inference-providers/...` |
| `EVAL_DATASET` | `smoke` (default), `humanevalplus`, `pokerbench`, or `reasoning_gate` |
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

Run Python with `uv run --project evals python` from the repository root.

```python
from evals.python import datasets

dataset = datasets.load_dataset(selection="smoke")
cases = datasets.list_cases(selection=dataset)
```

Edit `smoke.toml` to add a smoke case, or pass your own `Declaration` records to
`datasets.compile_dataset(cases=...)`. Each declaration pairs a Genius skill name
with a validated native `Task`. Use `datasets.clear_cache()` to release cached
dataset snapshots. [Smoke declarations](python/datasets/smoke.toml)

Genius collects the response, changed files, and verifier status in an
`Outcome`. `Task.grade(outcome=...)` scores that outcome and
`Task.grade_reference(verification=...)` scores the stored reference.
For example, this answer case earns correctness for an integer answer of 42
and fails scope if the candidate edits a file.

```python
from kernel import Criterion, Instruction, Outcome, Reference, Rubric, Task, Verification

task = Task(
    id="multiply",
    fixture=[],
    instruction=Instruction(prompt='What is six times seven? Reply with {"answer": <number>}.'),
    criterion=Criterion.Answer(rubric=Rubric(expected=[("answer", 42)], text_rule=None)),
    allowed_files=(),
    reference=Reference(edits=[], completion={"answer": 42}),
)
outcome = Outcome(
    response={"answer": 42},
    changed_files=["extra.txt"],
    verification=Verification.Unchecked(),
    facts=(),
)
print(dict(task.grade(outcome=outcome)))
```

Invalid declarations raise `ValidationError` with field-level `issues`.
A verifier harness failure raises `GradingError`. Candidate answers that fail
the rubric receive a false correctness score.
Inspect logs record the kernel's source hash as part of run provenance.
After a kernel upgrade, rerun both variants to compare them under the same grader.
[Genius Bench Python binding](https://github.com/shaquan1228/genius-bench/tree/main/bindings/python)
