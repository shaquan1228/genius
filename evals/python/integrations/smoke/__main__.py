import asyncio
import json
import sys
from typing import assert_never

import evals.python.query as queries
from evals.python import commands
from evals.python.datasets import smoke as declarations


def response(completion: queries.Ast.completion) -> str:
    if isinstance(completion, queries.Ast.Plain):
        return completion[0]
    if isinstance(completion, queries.Ast.Structured):
        return json.dumps({name: value[0] for name, value in completion[0]})
    assert_never(completion)


async def validate(definition: queries.Ast.case, *, dataset: queries.Dataset) -> bool:
    result = await commands.ValidateReference(case_id=definition.id, selection=dataset)
    scores: queries.Scores = {}
    if not isinstance(result.verification, queries.Ast.Harness_error):
        scores = queries.GradeCase(
            case_id=definition.id,
            response=response(definition.reference.completion),
            changed_files=tuple(
                f"workspace/{name}" for name, _ in queries.Fixture.files(definition.reference.edits)
            ),
            verification=result.verification,
            selection=dataset,
        )
    print(
        json.dumps(
            {
                "id": definition.id,
                "verification": type(result.verification).__name__.lower(),
                "scores": dict(scores),
            }
        )
    )
    return isinstance(result.verification, (queries.Ast.Passed, queries.Ast.Unchecked)) and all(
        scores.values()
    )


async def main() -> int:
    definitions = declarations.cases()
    dataset = queries.CompileDataset(cases=definitions)
    results = [await validate(definition, dataset=dataset) for definition in definitions]
    return int(not all(results))


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
