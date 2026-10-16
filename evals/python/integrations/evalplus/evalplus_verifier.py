"""Standalone EvalPlus verifier; only standard-library imports precede bootstrap."""

import importlib
import importlib.metadata
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal, Protocol, TypedDict, Unpack, assert_never, cast

Status = Literal["passed", "failed", "invalid_submission", "timed_out", "harness_error"]
PhaseName = Literal["base", "plus"]
PhaseStatus = Literal["pass", "fail", "timeout"]
PHASES: tuple[PhaseName, ...] = ("base", "plus")


@dataclass(frozen=True, kw_only=True)
class Result:
    status: Status
    detail: str = ""
    metadata: dict[str, object] = field(default_factory=dict)


class Manifest(TypedDict):
    evaluator_commit: str
    numpy_version: str
    psutil_version: str


class Problem(TypedDict):
    task_id: str
    prompt: str
    canonical_solution: str
    entry_point: str
    base_input: list[object]
    plus_input: list[object]
    atol: float


class Payload(TypedDict):
    manifest: Manifest
    record: str


@dataclass(frozen=True, kw_only=True)
class Dependencies:
    manifest: Manifest
    destination: str


@dataclass(frozen=True, kw_only=True)
class Phase:
    record: Problem
    name: PhaseName
    code: str


@dataclass(frozen=True, kw_only=True)
class Evaluation:
    record: Problem
    code: str
    metadata: dict[str, object] = field(default_factory=dict)


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


def installed_runtime(manifest: Manifest) -> bool:
    try:
        return installed(commit=manifest["evaluator_commit"]) and all(
            importlib.metadata.version(name)
            == {"numpy": manifest["numpy_version"], "psutil": manifest["psutil_version"]}[name]
            for name in ("numpy", "psutil")
        )
    except importlib.metadata.PackageNotFoundError:
        return False


def dependencies(request: Dependencies) -> None:
    manifest, destination = request.manifest, request.destination
    if installed_runtime(manifest=manifest):
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


def phase(request: Phase) -> PhaseStatus:
    record, name, code = request.record, request.name, request.code
    # The dedicated VM bounds memory; EvalPlus's stack limit is incompatible with HF.
    os.environ["EVALPLUS_MAX_MEMORY_BYTES"] = "-1"
    reference = cast(ReferenceAPI, importlib.import_module("evalplus.gen.util"))
    evaluator = cast(EvaluatorAPI, importlib.import_module("evalplus.eval"))
    match name:
        case "base":
            inputs = record["base_input"]
        case "plus":
            inputs = record["plus_input"]
        case _ as unreachable:
            assert_never(unreachable)
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
    match status:
        case "pass" | "fail" | "timeout" as known:
            return known
        case _:
            raise RuntimeError(f"Unexpected EvalPlus status: {status}")


def outcome(statuses: dict[PhaseName, PhaseStatus]) -> Status:
    status: PhaseStatus = min(
        statuses.values(), key=("timeout", "fail", "pass").index, default="fail"
    )
    match status:
        case "pass":
            return "passed"
        case "fail":
            return "failed"
        case "timeout":
            return "timed_out"
        case _ as unreachable:
            assert_never(unreachable)


def evaluate(payload: Payload) -> Result:
    manifest = payload["manifest"]
    record = cast(Problem, json.loads(payload["record"]))
    metadata: dict[str, object] = {"dataset": manifest, "task_id": record["task_id"]}
    try:
        code = Path("solution.py").read_text(encoding="utf-8")
        compile(code, "solution.py", "exec")
    except (SyntaxError, UnicodeError) as error:
        return Result(status="invalid_submission", detail=str(error), metadata=metadata)
    return evaluate_phases(request=Evaluation(record=record, code=code, metadata=metadata))


def evaluate_phases(request: Evaluation) -> Result:
    record, code, metadata = request.record, request.code, request.metadata
    statuses: dict[PhaseName, PhaseStatus] = {}
    metadata["phases"] = statuses
    try:
        for name in PHASES:
            statuses[name] = phase(request=Phase(record=record, name=name, code=code))
    except Exception as error:
        return Result(
            status="harness_error", detail=f"EvalPlus {name} phase: {error}", metadata=metadata
        )
    metadata.update(
        {
            "test_counts": {
                name: len({"base": record["base_input"], "plus": record["plus_input"]}[name])
                for name in statuses
            },
            "python_version": sys.version,
            "runtime": {
                name: importlib.metadata.version(name) for name in ("evalplus", "numpy", "psutil")
            },
        }
    )
    return Result(
        status=outcome(statuses=statuses),
        detail=json.dumps(statuses, sort_keys=True),
        metadata=metadata,
    )


def execute() -> Result:
    payload = cast(Payload, json.load(sys.stdin))
    with TemporaryDirectory(prefix="genius-evaluator-", dir=Path.cwd()) as destination:
        dependencies(request=Dependencies(manifest=payload["manifest"], destination=destination))
        return evaluate(payload=payload)


def main() -> None:
    try:
        if sys.argv[1:] != ["evalplus"]:
            raise ValueError("Expected verifier mode: evalplus")
        result = execute()
    except Exception as error:
        result = Result(status="harness_error", detail=str(error))
    print(
        json.dumps({"marker": os.environ["GENIUS_VERIFIER_MARKER"], **asdict(result)}), flush=True
    )


if __name__ == "__main__":
    main()
