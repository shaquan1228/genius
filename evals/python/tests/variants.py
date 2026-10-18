"""Exercise independent instruction variants through the real task builder."""

from pathlib import Path

import pytest

from evals.python import evaluation
from evals.python.evaluation import EvaluationSettings, VariantSettings
from evals.python.integrations.inspect import evaluation as runner


def selected_variant_uses_its_own_snapshot(tmp_path: Path) -> None:
    document = tmp_path / "skills/reasoning/SKILL.md"
    document.parent.mkdir(parents=True)
    document.write_text("The edited instructions")
    variant = VariantSettings(name="treatment", source_dir=str(tmp_path), instructions=("skills",))
    tasks = runner.evaluation_tasks(
        evaluation.resolve_settings(epochs=2),
        request=EvaluationSettings(model="mockllm/model", variant=variant),
    )
    assert [task.name for task in tasks] == ["treatment"]
    assert tasks[0].metadata is not None
    assert tasks[0].metadata["profile"] == "treatment"
    assert any(
        "instructions/skills/reasoning/SKILL.md" in (s.files or {}) for s in tasks[0].dataset
    )


def skillless_variant_does_not_load_instructions(tmp_path: Path) -> None:
    tasks = runner.evaluation_tasks(
        evaluation.resolve_settings(),
        request=EvaluationSettings(
            model="mockllm/model",
            variant=VariantSettings(
                name="control", instructions=(), preamble="", source_dir=str(tmp_path)
            ),
        ),
    )
    assert len(tasks) == 1
    assert all(
        not name.startswith("instructions/") for s in tasks[0].dataset for name in (s.files or {})
    )


@pytest.mark.parametrize("path", ["../skills", "/skills", ".", "skills/../docs"])
def variant_rejects_escaping_instruction_paths(path: str) -> None:
    with pytest.raises(ValueError, match="Instruction paths"):
        VariantSettings(name="edited", instructions=(path,))


def variant_rejects_missing_instruction_source(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="instruction"):
        runner.evaluation_tasks(
            evaluation.resolve_settings(),
            request=EvaluationSettings(
                model="mockllm/model",
                variant=VariantSettings(name="edited", source_dir=str(tmp_path)),
            ),
        )


def variant_and_delivery_diagnostics_are_exclusive() -> None:
    request = EvaluationSettings(
        model="mockllm/model",
        deliveries=("files", "inline"),
        variant=VariantSettings(name="edited", instructions=(), preamble=""),
    )
    with pytest.raises(ValueError, match="variant or delivery"):
        runner.evaluation_tasks(evaluation.resolve_settings(), request=request)


def variant_rejects_linked_sources(tmp_path: Path) -> None:
    target = tmp_path / "real"
    target.mkdir()
    (target / "SKILL.md").write_text("content")
    (tmp_path / "skills").symlink_to(target)
    request = EvaluationSettings(
        model="mockllm/model",
        variant=VariantSettings(name="edited", instructions=("skills",), source_dir=str(tmp_path)),
    )
    with pytest.raises(ValueError, match="must not contain links"):
        runner.evaluation_tasks(evaluation.resolve_settings(), request=request)
