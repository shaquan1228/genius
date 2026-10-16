"""Serialize kernel projections at the dataset boundary; no runtime SDK values escape."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from evals.python import commands
from evals.python.integrations.datasets import catalog
from evals.python.transport import fingerprint


def selection(request: dict[str, Any]) -> str | Path:
    value = str(request.get("selection", "smoke"))
    return Path(value) if request.get("suite") else value


def experiment(request: dict[str, Any]) -> object:
    return commands.query(
        commands.ExperimentSettings.model_validate(request.get("overrides", {}))
    ).model_dump(mode="json")


def verifier(request: dict[str, Any]) -> object:
    value = catalog.verifier(request["case_id"], selection=selection(request))
    return None if value is None else value.model_dump(mode="json")


def metadata(request: dict[str, Any]) -> object:
    value = catalog.dataset_info(selection(request))
    return None if value is None else value.model_dump(mode="json")


OPERATIONS: dict[str, Callable[[dict[str, Any]], object]] = {
    "cases": lambda r: [
        case.model_dump(mode="json") for case in catalog.load_cases(selection=selection(r))
    ],
    "experiment": experiment,
    "verifier": verifier,
    "reference": lambda r: catalog.reference(r["case_id"], selection=selection(r)).model_dump(
        mode="json"
    ),
    "grade": lambda r: dict(
        commands.grade(
            request=commands.GradeCase.model_validate_json(json.dumps(r["request"])),
            selection=selection(r),
        )
    ),
    "metadata": metadata,
    "sources_hash": lambda r: fingerprint(catalog.sources(selection(r))),
    "cases_hash": lambda r: catalog.cases_hash(selection(r)),
}


def execute(operation: str, *, payload: str) -> str:
    return json.dumps(OPERATIONS[operation](json.loads(payload)))
