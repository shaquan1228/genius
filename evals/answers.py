"""Check decision outputs with strict schemas; explanations still need review."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, StrictBool, ValidationError, field_validator


class Answer(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    reason: str

    @field_validator("reason")
    @classmethod
    def bounded_reason(cls, value: str) -> str:
        if not 1 <= len(value.split()) <= 40:
            raise ValueError("Reason must contain 1–40 words")
        return value


class DecisionAnswer(Answer):
    choice: Literal["A", "B"]


class ReviewAnswer(Answer):
    decision_was_supported: StrictBool
    change_rule: StrictBool


ANSWER_MODELS: dict[str, type[Answer]] = {
    "choice": DecisionAnswer,
    "review": ReviewAnswer,
}


def unfence(text: str) -> str:
    answer = text.strip()
    if answer.startswith("```json\n") and answer.endswith("\n```"):
        return answer[8:-4]
    return answer


def grade_answer(kind: str, text: str, *, expected: dict[str, str | bool]) -> bool:
    try:
        answer = ANSWER_MODELS[kind].model_validate_json(unfence(text), strict=True)
    except ValidationError:
        return False
    return answer.model_dump(exclude={"reason"}) == expected
