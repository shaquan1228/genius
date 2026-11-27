"""Exercise independent instruction variants through the real task builder."""

from pathlib import Path
from typing import cast

import pytest
from inspect_ai.dataset import Sample

from evals.python import evaluation
from evals.python.evaluation import EvaluationSettings, VariantSettings
from evals.python.integrations.inspect import evaluation as runner
from evals.python.integrations.inspect.profiles import inline_file


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


def reasoning_variants_change_only_the_installed_backend_flag() -> None:
    control = EvaluationSettings(
        model="mockllm/model",
        dataset="reasoning",
        variant=VariantSettings(name="control", proof_backend="markdown"),
    )
    treatment = control.model_copy(
        update={"variant": VariantSettings(name="treatment", proof_backend="bend")}
    )
    spec = evaluation.resolve_settings()
    (markdown,) = runner.evaluation_tasks(spec, request=control)
    (bend,) = runner.evaluation_tasks(spec, request=treatment)
    control_metadata = cast(dict[str, object], markdown.metadata)
    treatment_metadata = cast(dict[str, object], bend.metadata)
    assert control_metadata["cases_sha256"] == treatment_metadata["cases_sha256"]
    assert control_metadata["instructions_sha256"] != treatment_metadata["instructions_sha256"]
    for a, b in zip(markdown.dataset, bend.dataset, strict=True):
        _assert_paired_samples(a, treatment=b)


def _assert_paired_samples(control: Sample, *, treatment: Sample) -> None:
    flag = "instructions/skills/reasoning/proof-backend"
    left, right = dict(control.files or {}), dict(treatment.files or {})
    assert (left.pop(flag), right.pop(flag)) == (
        inline_file(contents=b"markdown\n"),
        inline_file(contents=b"bend\n"),
    )
    assert (control.id, control.input, left) == (treatment.id, treatment.input, right)


def backend_requires_an_installed_reasoning_skill() -> None:
    variant = VariantSettings(name="control", proof_backend="markdown", instructions=())
    with pytest.raises(ValueError, match="reasoning skill"):
        runner.evaluation_tasks(
            evaluation.resolve_settings(),
            request=EvaluationSettings(model="mockllm/model", variant=variant),
        )
