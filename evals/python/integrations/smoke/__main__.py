import asyncio
import json
import sys
from typing import assert_never

from evals.python import commands, queries
from kernel import Ast, Fixture


def response(completion: Ast.completion) -> str:
    match completion:
        case Ast.Plain():
            return completion[0]
        case Ast.Structured():
            return json.dumps({name: value[0] for name, value in completion[0]})
        case _ as unreachable:
            assert_never(unreachable)


async def validate(case: Ast.case, *, dataset: queries.Dataset) -> bool:
    reference = queries.get_reference(case_id=case.id, selection=dataset)
    result = await commands.validate_reference(case_id=case.id, selection=dataset)
    scores: queries.Scores = {}
    if not isinstance(result.verification, Ast.Harness_error):
        scores = queries.score_case(
            case_id=case.id,
            response=response(reference.completion),
            changed_files=tuple(f"workspace/{name}" for name, _ in Fixture.files(reference.edits)),
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
    dataset = queries.load_dataset()
    results = [
        await validate(case, dataset=dataset) for case in queries.list_cases(selection=dataset)
    ]
    return int(not all(results))


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
