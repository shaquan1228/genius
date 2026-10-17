# Genius evals

Compare baseline and Genius agents with [Inspect AI](https://inspect.aisi.org.uk/)
and [Inspect SWE](https://meridianlabs-ai.github.io/inspect_swe/).
The bundled datasets are a four-case smoke suite and the 164-problem HumanEval+ benchmark.

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

HumanEval+ downloads are pinned and checksum verified. Its `HumanEval/32` reference
fails the pinned official evaluator; full reference validation therefore exits nonzero.
On macOS, `validate --trusted-macos-memory-workaround` supports trusted upstream references.

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
