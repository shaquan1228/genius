"""JSON entry points for Inspect-owned execution; never return SDK instances."""

import asyncio
import json

from evals.python.integrations.inspect.benchmarks import validate_case


def execute(operation: str, *, payload: str) -> str:
    if operation != "validate_reference":
        raise ValueError(f"Unknown Inspect operation: {operation}")
    request = json.loads(payload)
    return json.dumps(asyncio.run(validate_case(request["case_id"])))
