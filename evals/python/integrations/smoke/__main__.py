import asyncio
import json
import sys
from typing import assert_never

from evals.python import commands
from evals.python.integrations.smoke import declarations


def response(completion: commands.PlainCompletion | commands.StructuredCompletion) -> str:
    match completion:
        case commands.PlainCompletion(text=text):
            return text
        case commands.StructuredCompletion(fields=fields):
            return json.dumps(dict(fields))
        case _ as unreachable:
            assert_never(unreachable)


async def validate(definition: commands.CaseDefinition, *, dataset: commands.Dataset) -> bool:
    result = await commands.execute(
        commands.ValidateReference(case_id=definition.id, selection=dataset)
    )
    scores: commands.Scores = {}
    if result.verification.status != "harness_error":
        scores = commands.query(
            commands.GradeCase(
                case_id=definition.id,
                response=response(definition.reference.completion),
                changed_files=tuple(f"workspace/{name}" for name in definition.reference.edits),
                verification=result.verification,
                selection=dataset,
            )
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
    dataset = commands.query(commands.CompileDataset(cases=definitions))
    results = [await validate(definition, dataset=dataset) for definition in definitions]
    return int(not all(results))


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
