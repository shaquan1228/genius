"""Launch independent immutable HF runs and compare their native evidence."""

import argparse
import json
import os
import time
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from huggingface_hub import HfApi, Volume

from evals.python import comparison
from evals.python.comparison import ComparisonRequest, VariantRequest
from evals.python.evaluation import EvaluationSettings, VariantSettings
from evals.python.integrations.hugging_face import source
from evals.python.integrations.hugging_face.job import configuration
from evals.python.paths import REPO_ROOT

TERMINAL = {"COMPLETED", "ERROR", "CANCELED", "DELETED", "SUSPENDED"}


def save(path: Path, *, value: object) -> bytes:
    data = (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data


def runtime_file(name: str) -> bool:
    return Path(name).suffix in {".py", ".ml", ".mli", ".sh"} and "/tests/" not in name


def committed_harness() -> None:
    paths = (
        "evals/python",
        "evals/ocaml",
        "evals/bin",
        "evals/pyproject.toml",
        "evals/uv.lock",
        ":(exclude)evals/python/tests/**",
    )
    changed = source.git("diff", "HEAD", "--", *paths, repository=REPO_ROOT)
    untracked = (
        source.git("ls-files", "--others", "--exclude-standard", "--", *paths, repository=REPO_ROOT)
        .decode()
        .splitlines()
    )
    runtime = [name for name in untracked if runtime_file(name)]
    if changed or runtime:
        raise ValueError("Commit the trusted evaluation harness before dispatch")


def resolve_request(request: ComparisonRequest) -> ComparisonRequest:
    shared = request.shared
    selection = shared.model_copy(
        update={
            "variant": VariantSettings(name="selection", instructions=(), preamble=""),
            "sandbox": "hf",
            "instruction_root": "/eval/instructions",
            "log_dir": "/results",
            "sandbox_image": shared.sandbox_image or os.environ.get("EVAL_SANDBOX_IMAGE", ""),
        }
    )
    shared = comparison.prepare_run(selection).settings.model_copy(update={"variant": None})
    if not shared.version or shared.version in {"latest", "stable", "next"}:
        raise ValueError("Use an exact agent version")
    return request.model_copy(update={"shared": shared})


def validate_provider(request: ComparisonRequest) -> None:
    provider = request.shared.model.split("/", 1)[0]
    if provider not in {"openai", "anthropic", "hf-inference-providers"}:
        raise ValueError("Choose an openai/, anthropic/, or hf-inference-providers/ model")
    if provider == "hf-inference-providers" and request.shared.model_cost is None:
        raise ValueError("Routed providers require exact model_cost")


def credentials(request: ComparisonRequest) -> dict[str, str]:
    secrets = {"HF_TOKEN": os.environ["HF_TOKEN"]}
    provider = request.shared.model.split("/", 1)[0]
    key = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}.get(provider)
    validate_provider(request)
    if key:
        secrets[key] = os.environ[key]
    if not all(secrets.values()):
        raise ValueError("Missing required provider credentials")
    return secrets


def run_settings(
    request: ComparisonRequest, *, variant: VariantSettings, run_id: str
) -> EvaluationSettings:
    return request.shared.model_copy(update={"variant": variant, "run_id": run_id})


def validate_saved(directory: Path, *, settings: EvaluationSettings) -> None:
    comparison.validate_run(directory, settings=settings)


def environment(settings: EvaluationSettings) -> dict[str, str]:
    fields = {
        "model",
        "agent",
        "version",
        "dataset",
        "epochs",
        "cost_limit",
        "sandbox_image",
        "time_limit",
        "message_limit",
        "cache",
        "max_samples",
        "sample_ids",
        "model_cost",
        "instruction_delivery",
        "variant",
        "run_id",
        "log_dir",
    }
    data = settings.model_dump(mode="json")
    return {
        f"EVAL_{key.upper()}": json.dumps(value)
        if isinstance(value, (dict, list, bool))
        else str(value)
        for key, value in data.items()
        if key in fields and value is not None
    }


@dataclass
class HostedComparison:
    request: ComparisonRequest
    output: Path
    namespace: str
    api: HfApi
    timeout: str
    secrets: dict[str, str] = field(repr=False)
    jobs: dict[str, str] = field(default_factory=dict)
    pending: set[str] = field(default_factory=set)
    settings: dict[str, EvaluationSettings] = field(default_factory=dict)
    local_settings: dict[str, EvaluationSettings] = field(default_factory=dict)
    directories: dict[str, Path] = field(default_factory=dict)
    state: dict[str, object] = field(default_factory=dict)

    @property
    def bucket(self) -> str:
        return f"{self.namespace}/genius-eval-results"

    def publish(self, name: str, *, value: object) -> None:
        payload = save(self.output / name, value=value)
        self.api.batch_bucket_files(
            self.bucket, add=[(payload, f"comparisons/{self.request.comparison_id}/{name}")]
        )

    def publish_state(self) -> None:
        self.state["jobs"] = dict(self.jobs)
        self.state["runs"] = {role: settings.run_id for role, settings in self.settings.items()}
        self.state["namespace"] = self.namespace
        self.publish("jobs.json", value=self.state)

    def prepare_runs(self, snapshot: Path) -> None:
        resolved = {
            role: self.prepare_run(role, snapshot=snapshot) for role in ("control", "treatment")
        }
        self.request = self.request.model_copy(update=resolved)

    def prepare_run(self, role: str, *, snapshot: Path) -> VariantRequest:
        candidate: VariantRequest = getattr(self.request, role)
        variant = source.instructions(
            candidate.variant, destination=snapshot / ".variants" / role, repository=REPO_ROOT
        )
        run_id = candidate.result_ref or f"{role}-{uuid4().hex}"
        local = variant.model_copy(update={"source_dir": str(snapshot / ".variants" / role)})
        self.local_settings[role] = run_settings(self.request, variant=local, run_id=run_id)
        self.directories[role] = self.output / "runs" / run_id
        remote = variant.model_copy(update={"source_dir": f"/source/.variants/{role}"})
        self.settings[role] = run_settings(self.request, variant=remote, run_id=run_id)
        comparison.prepare_run(self.local_settings[role])
        if candidate.result_ref:
            self.download(role)
            validate_saved(self.directories[role], settings=self.local_settings[role])
        return candidate.model_copy(update={"variant": variant})

    def upload(self, snapshot: Path, *, harness_sha: str) -> str:
        payload = save(self.output / "request.json", value=self.request.model_dump(mode="json"))
        (snapshot / "comparison-request.json").write_bytes(payload)
        self.api.create_bucket(self.bucket, private=True, exist_ok=True)
        self.publish("request.json", value=self.request.model_dump(mode="json"))
        repo = f"{self.namespace}/genius-evals"
        self.api.create_repo(repo, repo_type="dataset", private=True, exist_ok=True)
        commit = self.api.upload_folder(
            repo_id=repo,
            repo_type="dataset",
            folder_path=snapshot,
            commit_message=f"Comparison {self.request.comparison_id}",
            delete_patterns=["*"],
        )
        self.state.update(
            comparison_id=self.request.comparison_id,
            harness_sha=harness_sha,
            source_repo=repo,
            source_revision=commit.oid,
        )
        self.publish_state()
        return commit.oid

    def dispatch(self, revision: str) -> None:
        for role in ("control", "treatment"):
            if getattr(self.request, role).result_ref:
                continue
            current = self.settings[role]
            run_id = str(current.run_id)
            job = self.api.run_job(
                image="ghcr.io/astral-sh/uv:python3.12-bookworm",
                command=["sh", "/source/evals/bin/hf_bootstrap.sh"],
                namespace=self.namespace,
                timeout=self.timeout,
                name=f"genius-{role}",
                secrets=self.secrets,
                env=environment(current)
                | {
                    "HF_NAMESPACE": self.namespace,
                    "EVAL_SANDBOX_IMAGE": current.sandbox_image,
                },
                volumes=[
                    Volume(
                        type="dataset",
                        source=f"{self.namespace}/genius-evals",
                        revision=revision,
                        mount_path="/source",
                        read_only=True,
                    ),
                    Volume(
                        type="bucket",
                        source=self.bucket,
                        path=f"runs/{run_id}",
                        mount_path=f"/results/{run_id}",
                        read_only=False,
                    ),
                ],
            )
            self.jobs[role] = job.id
            self.pending.add(role)
            self.publish_state()

    def poll(self) -> None:
        for role in tuple(self.pending):
            status = self.api.inspect_job(
                job_id=self.jobs[role], namespace=self.namespace
            ).status.stage
            if status in TERMINAL:
                self.pending.remove(role)
                if status != "COMPLETED":
                    raise RuntimeError(f"{role} job ended with {status}")

    def wait(self, *, seconds: int) -> None:
        deadline = time.monotonic() + seconds
        while self.pending:
            self.poll()
            if self.pending:
                if time.monotonic() >= deadline:
                    raise TimeoutError("Comparison exceeded host wait limit")
                time.sleep(10)

    def download(self, role: str) -> None:
        self.api.sync_bucket(
            f"hf://buckets/{self.bucket}/runs/{self.settings[role].run_id}",
            str(self.directories[role]),
            delete=False,
            quiet=True,
        )

    def report(self) -> None:
        for role in self.jobs:
            self.download(role)
        for role in ("control", "treatment"):
            validate_saved(self.directories[role], settings=self.local_settings[role])
        report = comparison.compare_runs(
            self.directories["control"],
            treatment=self.directories["treatment"],
            measurement=self.request.measurement,
        )
        report["comparison_id"] = self.request.comparison_id
        report["jobs"] = dict(self.jobs)
        summary = comparison.render_report(report)
        self.publish("comparison.json", value=report)
        (self.output / "summary.md").write_text(summary)
        self.api.batch_bucket_files(
            self.bucket,
            add=[(summary.encode(), f"comparisons/{self.request.comparison_id}/summary.md")],
        )

    def cancel(self) -> None:
        for role in self.pending:
            with suppress(Exception):
                self.api.cancel_job(job_id=self.jobs[role], namespace=self.namespace)

    def run(self, snapshot: Path) -> None:
        harness_sha = source.trusted_snapshot(snapshot, repository=REPO_ROOT)
        self.prepare_runs(snapshot)
        revision = self.upload(snapshot, harness_sha=harness_sha)
        try:
            self.dispatch(revision)
            self.wait(seconds=18000)
            self.report()
        except BaseException:
            self.cancel()
            raise


def execute(
    request: ComparisonRequest,
    *,
    output: Path,
    namespace: str,
    timeout: str = "4h",
    api: HfApi | None = None,
) -> None:
    committed_harness()
    request = resolve_request(request)
    secrets = credentials(request)
    output.mkdir(parents=True, exist_ok=True)
    if (output / "jobs.json").exists():
        raise ValueError("Output already contains dispatch state; use a new directory")
    host = HostedComparison(
        request=request,
        output=output,
        namespace=namespace,
        api=api or HfApi(),
        timeout=timeout,
        secrets=secrets,
    )
    with TemporaryDirectory() as temporary:
        host.run(Path(temporary))


def prepare_variant(role: str) -> VariantRequest:
    return VariantRequest(
        variant=VariantSettings(
            name=role, source_ref=os.environ.get(f"{role.upper()}_REF", "HEAD")
        ),
        result_ref=os.environ.get(f"{role.upper()}_RESULT_REF") or None,
    )


def prepare(output: Path) -> None:
    environment = dict(os.environ)
    default_agent = "claude" if environment["EVAL_MODEL"].startswith("anthropic/") else "codex"
    environment["EVAL_AGENT"] = environment.get("EVAL_AGENT") or default_agent
    settings = configuration(environment)
    request = ComparisonRequest(
        comparison_id=os.environ.get("COMPARISON_ID", f"comparison-{uuid4().hex}"),
        origin={
            name: os.environ[name]
            for name in ("GITHUB_REPOSITORY", "GITHUB_RUN_ID", "PR_NUMBER")
            if name in os.environ
        },
        shared=settings.model_copy(update={"variant": None, "deliveries": None}),
        control=prepare_variant("control"),
        treatment=prepare_variant("treatment"),
    )
    save(output / "request.json", value=request.model_dump(mode="json"))


def execute_file(path: Path, *, output: Path, namespace: str, timeout: str) -> None:
    try:
        execute(
            ComparisonRequest.model_validate_json(path.read_text()),
            output=output,
            namespace=namespace,
            timeout=timeout,
        )
    except Exception as error:
        verdict = "incompatible" if isinstance(error, ValueError) else "failed"
        save(output / "comparison.json", value={"verdict": verdict, "error": str(error)})
        (output / "summary.md").write_text(
            f"## Benchmark comparison\n\nVerdict: **{verdict}**\n\n{error}\n"
        )
        raise


def cancel_saved(output: Path, *, namespace: str) -> None:
    api = HfApi()
    for job_id in json.loads((output / "jobs.json").read_text())["jobs"].values():
        api.cancel_job(job_id=job_id, namespace=namespace)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "run", "cancel"])
    parser.add_argument("request", nargs="?", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--namespace", default=os.environ.get("HF_NAMESPACE"))
    parser.add_argument("--timeout", default=os.environ.get("EVAL_JOB_TIMEOUT", "4h"))
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.output)
    elif args.action == "cancel":
        cancel_saved(args.output, namespace=args.namespace)
    else:
        if args.request is None or not args.namespace:
            parser.error("run requires a request and --namespace")
        execute_file(
            args.request, output=args.output, namespace=args.namespace, timeout=args.timeout
        )


if __name__ == "__main__":
    main()
