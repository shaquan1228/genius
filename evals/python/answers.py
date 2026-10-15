"""Check JSON replies against expected fields; explanations still need review."""

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator


class Reply(BaseModel):
    """A bounded reason plus the answer fields, kept as extras for exact comparison."""

    model_config = ConfigDict(strict=True, extra="allow")
    reason: str

    @field_validator("reason")
    @classmethod
    def bounded_reason(cls, value: str) -> str:
        if not 1 <= len(value.split()) <= 40:
            raise ValueError("Reason must contain 1–40 words")
        return value


def unfence(text: str) -> str:
    answer = text.strip()
    if answer.startswith("```json\n") and answer.endswith("\n```"):
        return answer[8:-4]
    return answer


def typed(fields: Mapping[str, object]) -> dict[str, tuple[type, object]]:
    """Pair each value with its type, so `1` never matches `true`."""
    return {name: (type(value), value) for name, value in fields.items()}


def grade_answer(text: str, *, expected: Mapping[str, str | bool]) -> bool:
    try:
        reply = Reply.model_validate_json(unfence(text))
    except ValidationError:
        return False
    return typed(reply.model_extra or {}) == typed(expected)
