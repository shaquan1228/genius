import asyncio
import json
import sys
from typing import assert_never

import evals.python.query as queries
from evals.python import commands
from kernel import Ast


def response(completion: Ast.completion) -> str:
    match completion:
        case Ast.Plain():
            return completion[0]
        case Ast.Structured():
            return json.dumps({name: value[0] for name, value in completion[0]})
        case _ as unreachable:
            assert_never(unreachable)


async def validate(case: Ast.case, *, dataset: queries.Dataset) -> bool:
    reference = queries.Reference(case_id=case.id, selection=dataset)
    result = await commands.ValidateReference(case_id=case.id, selection=dataset)
    scores: queries.Scores = {}
    if not isinstance(result.verification, Ast.Harness_error):
        scores = queries.GradeCase(
            case_id=case.id,
            response=response(reference.completion),
            changed_files=tuple(
                f"workspace/{name}" for name, _ in queries.Fixture.files(reference.edits)
            ),
            verification=result.verification,
            selection=dataset,
        )
    print(
        json.dumps(
            {
                "id": case.id,
                "verification": type(result.verification).__name__.lower(),
                "scores": dict(scores),
            }
        )
    )
    return isinstance(result.verification, (Ast.Passed, Ast.Unchecked)) and all(scores.values())


async def main() -> int:
    dataset = queries.LoadDataset()
    results = [await validate(case, dataset=dataset) for case in queries.Cases(selection=dataset)]
    return int(not all(results))


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
