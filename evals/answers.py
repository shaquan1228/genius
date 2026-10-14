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
    choice: Literal["B"]


class ReviewAnswer(Answer):
    decision_was_supported: StrictBool
    change_rule: StrictBool

    @field_validator("decision_was_supported")
    @classmethod
    def require_supported(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Original decision was supported by the known odds")
        return value

    @field_validator("change_rule")
    @classmethod
    def reject_hindsight(cls, value: bool) -> bool:
        if value:
            raise ValueError("One loss alone should not change the rule")
        return value


ANSWER_MODELS: dict[str, type[Answer]] = {
    "small-decision": DecisionAnswer,
    "decision-review": ReviewAnswer,
}


def unfence(text: str) -> str:
    answer = text.strip()
    if answer.startswith("```json\n") and answer.endswith("\n```"):
        return answer[8:-4]
    return answer


def grade_answer(case_id: str, text: str) -> bool:
    try:
        ANSWER_MODELS[case_id].model_validate_json(unfence(text), strict=True)
    except ValidationError:
        return False
    return True
