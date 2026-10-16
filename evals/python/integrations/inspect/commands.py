"""JSON entry points for Inspect-owned execution; never return SDK instances."""

import asyncio
import json

from evals.python.integrations.inspect.benchmarks import validate_case
from evals.python.integrations.inspect.evaluation import EvaluationRequest, evaluate


def execute(operation: str, *, payload: str) -> str:
    match operation:
        case "evaluate":
            return json.dumps(evaluate(EvaluationRequest.model_validate_json(payload)))
        case "validate_reference":
            request = json.loads(payload)
            return json.dumps(asyncio.run(validate_case(request["case_id"])))
        case _:
            raise ValueError(f"Unknown Inspect operation: {operation}")
