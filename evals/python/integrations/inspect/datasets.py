"""Inspect's typed view of JSON commands; no dataset implementation imports."""

import json
from collections.abc import Mapping
from pathlib import Path

from pydantic import TypeAdapter

from evals.python.command import command
from evals.python.contracts import (
    Case,
    ExecutableChecks,
    Experiment,
    GradeRequest,
    Reference,
    RunOverrides,
)

Selection = str | Path


def request(selection: Selection = "smoke") -> dict[str, object]:
    return {"selection": str(selection), "suite": isinstance(selection, Path)}


def load_cases(*, selection: Selection = "smoke") -> tuple[Case, ...]:
    return TypeAdapter(tuple[Case, ...]).validate_json(
        command("dataset.cases", payload=json.dumps(request(selection)))
    )


def experiment(overrides: RunOverrides | None = None) -> Experiment:
    payload = {"overrides": {} if overrides is None else overrides.model_dump()}
    return Experiment.model_validate_json(
        command("dataset.experiment", payload=json.dumps(payload))
    )


def verifier(case_id: str, *, selection: Selection = "smoke") -> ExecutableChecks | None:
    payload = {**request(selection), "case_id": case_id}
    return TypeAdapter(ExecutableChecks | None).validate_json(
        command("dataset.verifier", payload=json.dumps(payload))
    )


def reference(case_id: str, *, selection: Selection = "smoke") -> Reference:
    payload = {**request(selection), "case_id": case_id}
    return Reference.model_validate_json(command("dataset.reference", payload=json.dumps(payload)))


def grade(*, request: GradeRequest, selection: Selection = "smoke") -> Mapping[str, bool]:
    payload = {
        "selection": str(selection),
        "suite": isinstance(selection, Path),
        "request": request.model_dump(),
    }
    return TypeAdapter(dict[str, bool]).validate_json(
        command("dataset.grade", payload=json.dumps(payload))
    )


def benchmark_metadata(dataset: Selection) -> dict[str, object]:
    return (
        TypeAdapter(dict[str, object] | None).validate_json(
            command("dataset.metadata", payload=json.dumps(request(dataset)))
        )
        or {}
    )


def source_hash(dataset: Selection) -> str:
    return TypeAdapter(str).validate_json(
        command("dataset.sources_hash", payload=json.dumps(request(dataset)))
    )


def cases_hash(dataset: Selection) -> str:
    return TypeAdapter(str).validate_json(
        command("dataset.cases_hash", payload=json.dumps(request(dataset)))
    )
