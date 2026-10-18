"""Run independent HF variants and compare their native Inspect logs."""

import argparse
import json
import os
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager, suppress
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast
from uuid import uuid4

from huggingface_hub import HfApi, Volume

from evals.python import comparison
from evals.python.comparison import ComparisonRequest, VariantRequest
from evals.python.evaluation import EvaluationSettings, VariantSettings
from evals.python.integrations.hugging_face import source
from evals.python.integrations.hugging_face.job import configuration
from evals.python.paths import REPO_ROOT

ROLES = ("control", "treatment")


def save(path: Path, *, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def request_from_environment() -> ComparisonRequest:
    if os.environ.get("COMPARISON_REQUEST"):
        return ComparisonRequest.model_validate_json(os.environ["COMPARISON_REQUEST"])
    variants = {
        role: VariantRequest(
            variant=VariantSettings(
                name=role, source_ref=os.environ.get(f"{role.upper()}_REF", "HEAD")
            ),
            result_ref=os.environ.get(f"{role.upper()}_RESULT_REF") or None,
        )
        for role in ROLES
    }
    return ComparisonRequest(
        comparison_id=os.environ.get("COMPARISON_ID", f"comparison-{uuid4().hex}"),
        shared=configuration(os.environ),
        control=variants["control"],
        treatment=variants["treatment"],
    )


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


def download(api: HfApi, *, settings: EvaluationSettings, destination: Path, bucket: str) -> None:
    api.sync_bucket(
        f"hf://buckets/{bucket}/runs/{settings.run_id}", str(destination), delete=False, quiet=True
    )
    comparison.validate_run(destination, settings=settings)


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


def prepare_variants(
    request: ComparisonRequest, *, snapshot: Path
) -> tuple[ComparisonRequest, dict[str, EvaluationSettings]]:
    plans, variants = {}, {}
    for role in ROLES:
        selected = getattr(request, role)
        destination = snapshot / ".variants" / role
        variant = source.instructions(
            selected.variant, destination=destination, repository=REPO_ROOT
        )
        plans[role] = comparison.prepare_run(
            request.shared.model_copy(
                update={
                    "sandbox": "hf",
                    "log_dir": "/results",
                    "instruction_root": "/eval/instructions",
                    "variant": variant.model_copy(update={"source_dir": str(destination)}),
                    "run_id": selected.result_ref,
                }
            )
        )
        variants[role] = selected.model_copy(update={"variant": variant})
    variants["shared"] = plans["control"].model_copy(update={"variant": None, "run_id": None})
    return request.model_copy(update=variants), plans


def upload(api: HfApi, *, snapshot: Path, namespace: str) -> Volume:
    repo = f"{namespace}/genius-evals"
    api.create_repo(repo, repo_type="dataset", private=True, exist_ok=True)
    commit = api.upload_folder(
        repo_id=repo, repo_type="dataset", folder_path=snapshot, delete_patterns=["*"]
    )
    return Volume(
        type="dataset", source=repo, revision=commit.oid, mount_path="/source", read_only=True
    )


def launch(api: HfApi, *, settings: EvaluationSettings, source_volume: Volume, timeout: str) -> str:
    namespace = source_volume.source.split("/", 1)[0]
    variant = cast(VariantSettings, settings.variant)
    role = Path(str(variant.source_dir)).name
    remote = settings.model_copy(
        update={"variant": variant.model_copy(update={"source_dir": f"/source/.variants/{role}"})}
    )
    job = api.run_job(
        image="ghcr.io/astral-sh/uv:python3.12-bookworm",
        command=["sh", "/source/evals/bin/hf_bootstrap.sh"],
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
    plans: dict[str, EvaluationSettings],
    source_volume: Volume,
    output: Path,
    timeout: str,
) -> Iterator[dict[str, str]]:
    submitted: dict[str, str] = {}
    namespace = source_volume.source.split("/", 1)[0]
    try:
        for role in ROLES:
            if getattr(request, role).result_ref is not None:
                continue
            submitted[role] = launch(
                api, settings=plans[role], source_volume=source_volume, timeout=timeout
            )
            save(
                output / "jobs.json",
                value={
                    "namespace": namespace,
                    "jobs": submitted,
                    "runs": {name: plan.run_id for name, plan in plans.items()},
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


def reuse(
    api: HfApi,
    *,
    request: ComparisonRequest,
    plans: dict[str, EvaluationSettings],
    output: Path,
    bucket: str,
) -> None:
    for role in ROLES:
        if getattr(request, role).result_ref:
            download(
                api,
                settings=plans[role],
                destination=output / "runs" / str(plans[role].run_id),
                bucket=bucket,
            )


def execute(
    request: ComparisonRequest, *, output: Path, namespace: str, timeout: str = "4h"
) -> None:
    committed_harness()
    if (output / "jobs.json").exists():
        raise ValueError("Output already contains dispatch state; use a new directory")
    api = HfApi()
    bucket = f"{namespace}/genius-eval-results"
    with TemporaryDirectory() as temporary:
        snapshot = Path(temporary)
        source.trusted_snapshot(snapshot, repository=REPO_ROOT)
        request, plans = prepare_variants(request, snapshot=snapshot)
        reuse(api, request=request, plans=plans, output=output, bucket=bucket)
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
            for role in ROLES:
                download(
                    api,
                    settings=plans[role],
                    destination=output / "runs" / str(plans[role].run_id),
                    bucket=bucket,
                )
            result = comparison.compare_runs(
                output / "runs" / str(plans["control"].run_id),
                treatment=output / "runs" / str(plans["treatment"].run_id),
                measurement=request.measurement,
            )
            save(output / "comparison.json", value=result)
            (output / "summary.md").write_text(comparison.render_report(result))
            publish(api, request=request, output=output, bucket=bucket)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", nargs="?", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--namespace", default=os.environ.get("HF_NAMESPACE"))
    parser.add_argument("--timeout", default=os.environ.get("EVAL_JOB_TIMEOUT", "4h"))
    args = parser.parse_args()
    if not args.namespace:
        parser.error("--namespace or HF_NAMESPACE is required")
    request = (
        ComparisonRequest.model_validate_json(args.request.read_text())
        if args.request
        else request_from_environment()
    )
    execute(request, output=args.output, namespace=args.namespace, timeout=args.timeout)


if __name__ == "__main__":
    main()
