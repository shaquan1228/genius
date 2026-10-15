"""Run the pinned upstream evaluator inside a private grading environment."""

import importlib
import importlib.metadata
import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Protocol, TypedDict, Unpack, cast


class ReferenceAPI(Protocol):
    def trusted_exec(
        self,
        code: str,
        *,
        inputs: list[object],
        entry_point: str,
        record_time: bool,
    ) -> tuple[list[object], list[float]]: ...


class EvaluationOptions(TypedDict):
    code: str
    inputs: list[object]
    entry_point: str
    expected: list[object]
    atol: float
    ref_time: list[float]
    fast_check: bool
    min_time_limit: float
    gt_time_limit_factor: float


class EvaluatorAPI(Protocol):
    def untrusted_check(
        self, dataset: str, **options: Unpack[EvaluationOptions]
    ) -> tuple[str, object]: ...


def installed(commit: str) -> bool:
    try:
        distribution = importlib.metadata.distribution("evalplus")
    except importlib.metadata.PackageNotFoundError:
        return False
    metadata = json.loads(distribution.read_text("direct_url.json") or "{}")
    return bool(metadata.get("vcs_info", {}).get("commit_id") == commit)


def installed_runtime(manifest: dict[str, Any]) -> bool:
    try:
        return installed(manifest["evaluator_commit"]) and all(
            importlib.metadata.version(name) == manifest[name + "_version"]
            for name in ("numpy", "psutil")
        )
    except importlib.metadata.PackageNotFoundError:
        return False


def dependencies(manifest: dict[str, Any], *, destination: str) -> None:
    if installed_runtime(manifest):
        return
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--quiet",
            "--no-deps",
            "--target",
            destination,
            "git+https://github.com/evalplus/evalplus.git@" + manifest["evaluator_commit"],
            "numpy==" + manifest["numpy_version"],
            "psutil==" + manifest["psutil_version"],
        ],
        check=True,
        stdout=sys.stderr,
        timeout=120,
    )
    sys.path.insert(0, destination)


def phase(record: dict[str, Any], *, name: str, code: str) -> str:
    reference = cast(ReferenceAPI, importlib.import_module("evalplus.gen.util"))
    evaluator = cast(EvaluatorAPI, importlib.import_module("evalplus.eval"))
    inputs = record[name + "_input"]
    expected, timing = reference.trusted_exec(
        record["prompt"] + record["canonical_solution"],
        inputs=inputs,
        entry_point=record["entry_point"],
        record_time=True,
    )
    status, _ = evaluator.untrusted_check(
        "humaneval",
        code=code,
        inputs=inputs,
        entry_point=record["entry_point"],
        expected=expected,
        atol=record["atol"],
        ref_time=timing,
        fast_check=True,
        min_time_limit=1.0,
        gt_time_limit_factor=4.0,
    )
    if status not in {"pass", "fail", "timeout"}:
        raise RuntimeError(f"Unexpected EvalPlus status: {status}")
    return status


def outcome(statuses: dict[str, str]) -> str:
    if "timeout" in statuses.values():
        return "timed_out"
    return "passed" if set(statuses.values()) == {"pass"} else "failed"


def evaluate(payload: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    manifest = payload["manifest"]
    record = json.loads(payload["record"])
    metadata = {"dataset": manifest, "task_id": record["task_id"]}
    try:
        code = Path("solution.py").read_text(encoding="utf-8")
        compile(code, "solution.py", "exec")
    except (SyntaxError, UnicodeError) as error:
        return "invalid_submission", str(error), metadata
    return evaluate_phases(record, code=code, metadata=metadata)


def evaluate_phases(
    record: dict[str, Any], *, code: str, metadata: dict[str, Any]
) -> tuple[str, str, dict[str, Any]]:
    statuses: dict[str, str] = {}
    metadata["phases"] = statuses
    try:
        for name in ("base", "plus"):
            statuses[name] = phase(record, name=name, code=code)
    except Exception as error:
        return "harness_error", f"EvalPlus {name} phase: {error}", metadata
    metadata.update(
        {
            "test_counts": {name: len(record[name + "_input"]) for name in statuses},
            "python_version": sys.version,
            "runtime": {
                name: importlib.metadata.version(name) for name in ("evalplus", "numpy", "psutil")
            },
        }
    )
    return outcome(statuses), json.dumps(statuses, sort_keys=True), metadata


def execute() -> tuple[str, str, dict[str, Any]]:
    payload = json.load(sys.stdin)
    with TemporaryDirectory(prefix="genius-evalplus-", dir=Path.cwd()) as destination:
        dependencies(payload["manifest"], destination=destination)
        return evaluate(payload)


def main() -> None:
    try:
        status, detail, metadata = execute()
    except Exception as error:
        status, detail, metadata = "harness_error", str(error), {}
    print(
        json.dumps(
            {
                "marker": os.environ["GENIUS_VERIFIER_MARKER"],
                "status": status,
                "detail": detail,
                "metadata": metadata,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
