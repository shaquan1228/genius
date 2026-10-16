"""One JSON command boundary; integrations keep SDKs and implementation types private."""

import importlib
import json
from types import MappingProxyType
from typing import Protocol, cast

ENDPOINTS = MappingProxyType(
    {
        "dataset": "evals.python.integrations.datasets.commands",
        "hf": "evals.python.integrations.hugging_face.sandbox",
        "inspect": "evals.python.integrations.inspect.commands",
    }
)


class Handler(Protocol):
    def execute(self, operation: str, *, payload: str) -> str: ...


def command(name: str, *, payload: str = "{}") -> str:
    endpoint, operation = name.split(".", 1)
    json.loads(payload)
    handler = cast(Handler, importlib.import_module(ENDPOINTS[endpoint]))
    result = handler.execute(operation, payload=payload)
    json.loads(result)
    return result
