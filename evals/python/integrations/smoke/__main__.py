import asyncio
import json
import sys
from typing import assert_never

import evals.python.query as queries
from evals.python import commands
from evals.python.datasets import smoke as declarations


def response(completion: queries.PlainCompletion | queries.StructuredCompletion) -> str:
    match completion:
        case queries.PlainCompletion(text=text):
            return text
        case queries.StructuredCompletion(fields=fields):
            return json.dumps(dict(fields))
        case _ as unreachable:
            assert_never(unreachable)


async def validate(definition: queries.CaseDefinition, *, dataset: queries.Dataset) -> bool:
    result = await commands.ValidateReference(case_id=definition.id, selection=dataset)
    scores: queries.Scores = {}
    if result.verification.status != "harness_error":
        scores = queries.GradeCase(
            case_id=definition.id,
            response=response(definition.reference.completion),
            changed_files=tuple(f"workspace/{name}" for name in definition.reference.edits),
            verification=result.verification,
            selection=dataset,
        )
    print(
        json.dumps(
            {
                "id": definition.id,
                "verification": result.verification.status,
                "scores": dict(scores),
            }
        )
    )
    return result.verification.status in ("passed", "unchecked") and all(scores.values())


async def main() -> int:
    definitions = declarations.cases()
    dataset = queries.CompileDataset(cases=definitions)
    results = [await validate(definition, dataset=dataset) for definition in definitions]
    return int(not all(results))


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
