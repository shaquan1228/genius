import json
import os
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager, suppress
from pathlib import Path
from tempfile import TemporaryDirectory

from huggingface_hub import HfApi, Volume

from evals.python import REPO_ROOT, evaluation
from evals.python.comparison import ComparisonRequest, VariantRequest
from evals.python.evaluation import EvaluationSettings
from evals.python.integrations.hugging_face import source

type Prepared = tuple[VariantRequest, EvaluationSettings]


def save(path: Path, *, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def environment(settings: EvaluationSettings) -> dict[str, str]:
    return {
        f"EVAL_{key.upper()}": json.dumps(value)
        if isinstance(value, (dict, list, bool))
        else str(value)
        for key, value in settings.model_dump(mode="json").items()
        if key not in {"sandbox", "instruction_root", "deliveries", "limit"} and value is not None
    }


def credentials(settings: EvaluationSettings) -> dict[str, str]:
    keys = {
        "openai": ("OPENAI_API_KEY",),
        "anthropic": ("ANTHROPIC_API_KEY",),
        "hf-inference-providers": (),
    }
    provider = settings.model.split("/", 1)[0]
    if provider not in keys:
        raise ValueError("Choose an openai/, anthropic/, or hf-inference-providers/ model")
    secrets = {key: os.environ[key] for key in ("HF_TOKEN", *keys[provider])}
    if not all(secrets.values()):
        raise ValueError("Missing required provider credentials")
    return secrets


def download(
    api: HfApi,
    *,
    plans: tuple[Prepared, ...],
    output: Path,
    bucket: str,
    reused: bool,
) -> None:
    for selected, settings in plans:
        if (selected.result_ref is not None) != reused:
            continue
        directory = output / "runs" / str(settings.run_id)
        api.sync_bucket(
            f"hf://buckets/{bucket}/runs/{settings.run_id}",
            str(directory),
            delete=False,
            quiet=True,
        )
        evaluation.validate_run(directory, settings=settings)


def publish(api: HfApi, *, request: ComparisonRequest, output: Path, bucket: str) -> None:
    api.batch_bucket_files(
        bucket,
        add=[
            (path.read_bytes(), f"comparisons/{request.comparison_id}/{path.name}")
            for path in (
                output / name
                for name in ("request.json", "jobs.json", "comparison.json", "summary.md")
            )
            if path.is_file()
        ],
    )


def committed_harness() -> None:
    changed = source.git(
        "status",
        "--porcelain",
        "--untracked-files=all",
        "--",
        "evals/python",
        "evals/ocaml",
        "evals/bin",
        "evals/pyproject.toml",
        "evals/uv.lock",
        ":(exclude)evals/python/tests/**",
        repository=REPO_ROOT,
    )
    if changed:
        raise ValueError("Commit the trusted evaluation harness before dispatch")


def prepare_variant(
    selected: VariantRequest, *, shared: EvaluationSettings, snapshot: Path
) -> Prepared:
    destination = snapshot / ".variants" / selected.variant.name
    variant = source.instructions(selected.variant, destination=destination, repository=REPO_ROOT)
    settings = evaluation.prepare_run(
        shared.model_copy(
            update={
                "sandbox": "hf",
                "log_dir": "/results",
                "instruction_root": "/eval/instructions",
                "variant": variant.model_copy(update={"source_dir": str(destination)}),
                "run_id": selected.result_ref,
            }
        )
    )
    return selected.model_copy(update={"variant": variant}), settings


def upload(api: HfApi, *, snapshot: Path, namespace: str) -> Volume:
    repo = f"{namespace}/genius-evals"
    api.create_repo(repo, repo_type="dataset", private=True, exist_ok=True)
    commit = api.upload_folder(
        repo_id=repo, repo_type="dataset", folder_path=snapshot, delete_patterns=["*"]
    )
    return Volume(
        type="dataset", source=repo, revision=commit.oid, mount_path="/source", read_only=True
    )


def launch(
    api: HfApi,
    *,
    selected: VariantRequest,
    settings: EvaluationSettings,
    source_volume: Volume,
    timeout: str,
) -> str:
    namespace = source_volume.source.split("/", 1)[0]
    remote = settings.model_copy(
        update={
            "variant": selected.variant.model_copy(
                update={"source_dir": f"/source/.variants/{selected.variant.name}"}
            )
        }
    )
    job = api.run_job(
        image="ghcr.io/astral-sh/uv:python3.12-bookworm",
        command=["bash", "/source/evals/scripts/huggingface-bootstrap.sh"],
        namespace=namespace,
        timeout=timeout,
        env=environment(remote) | {"HF_NAMESPACE": namespace},
        secrets=credentials(settings),
        volumes=[
            source_volume,
            Volume(
                type="bucket",
                source=f"{namespace}/genius-eval-results",
                path=f"runs/{settings.run_id}",
                mount_path=f"/results/{settings.run_id}",
                read_only=False,
            ),
        ],
    )
    return job.id


def cancel(api: HfApi, *, submitted: dict[str, str], namespace: str) -> None:
    for job_id in submitted.values():
        with suppress(Exception):
            api.cancel_job(job_id=job_id, namespace=namespace)


@contextmanager
def jobs(  # noqa: PLR0913 - dispatch lifecycle shares explicit immutable inputs
    api: HfApi,
    *,
    request: ComparisonRequest,
    plans: tuple[Prepared, ...],
    source_volume: Volume,
    output: Path,
    timeout: str,
) -> Iterator[dict[str, str]]:
    submitted: dict[str, str] = {}
    runs = {selected.variant.name: settings.run_id for selected, settings in plans}
    namespace = source_volume.source.split("/", 1)[0]
    try:
        for selected, settings in plans:
            if selected.result_ref is not None:
                continue
            submitted[selected.variant.name] = launch(
                api,
                selected=selected,
                settings=settings,
                source_volume=source_volume,
                timeout=timeout,
            )
            save(
                output / "jobs.json",
                value={
                    "namespace": namespace,
                    "jobs": submitted,
                    "runs": runs,
                },
            )
            publish(api, request=request, output=output, bucket=f"{namespace}/genius-eval-results")
        yield submitted
    except BaseException:
        cancel(api, submitted=submitted, namespace=namespace)
        raise


def wait(api: HfApi, *, submitted: dict[str, str], namespace: str) -> None:
    if not submitted:
        return
    executor = ThreadPoolExecutor(max_workers=len(submitted))
    try:
        pending = [
            executor.submit(
                api.wait_for_job, job_id, namespace=namespace, timeout=18000, poll_interval=10
            )
            for job_id in submitted.values()
        ]
        for future in as_completed(pending):
            if future.result().status.stage != "COMPLETED":
                raise RuntimeError("A comparison job did not complete successfully")
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


@contextmanager
def acquire_runs(
    request: ComparisonRequest, *, output: Path, namespace: str, timeout: str = "4h"
) -> Iterator[tuple[ComparisonRequest, dict[str, Path]]]:
    committed_harness()
    if (output / "jobs.json").exists():
        raise ValueError("Output already contains dispatch state; use a new directory")
    api = HfApi()
    bucket = f"{namespace}/genius-eval-results"
    with TemporaryDirectory() as temporary:
        snapshot = Path(temporary)
        source.trusted_snapshot(snapshot, repository=REPO_ROOT)
        plans = tuple(
            prepare_variant(selected, shared=request.shared, snapshot=snapshot)
            for selected in request.variants
        )
        request = request.model_copy(
            update={
                "variants": tuple(selected for selected, _ in plans),
                "shared": plans[0][1].model_copy(update={"variant": None, "run_id": None}),
            }
        )
        download(api, plans=plans, output=output, bucket=bucket, reused=True)
        save(output / "request.json", value=request.model_dump(mode="json"))
        api.create_bucket(bucket, private=True, exist_ok=True)
        publish(api, request=request, output=output, bucket=bucket)
        source_volume = upload(api, snapshot=snapshot, namespace=namespace)
        with jobs(
            api,
            request=request,
            plans=plans,
            source_volume=source_volume,
            output=output,
            timeout=timeout,
        ) as submitted:
            wait(api, submitted=submitted, namespace=namespace)
            download(api, plans=plans, output=output, bucket=bucket, reused=False)
            yield (
                request,
                {
                    selected.variant.name: output / "runs" / str(settings.run_id)
                    for selected, settings in plans
                },
            )
            publish(api, request=request, output=output, bucket=bucket)
