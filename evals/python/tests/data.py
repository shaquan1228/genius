"""Validate schemas and keep the comparison's inputs controlled."""

import json
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from evals.python import datasets, evaluation, evaluation_settings
from evals.python.grading import score_case
from evals.python.integrations.inspect import profiles
from evals.python.integrations.inspect.profiles import (
    REASONING_DOCUMENTS,
    content_hash,
    load_profile,
)
from evals.python.integrations.inspect.tasks import build_task
from evals.python.paths import REPO_ROOT
from evals.python.tests.declarations import _copy_case, _files, _reference_files, _reference_text
from evals.python.tests.projections import public_case, reference, verifier
from evals.python.tests.support import (
    choice_case as _choice_case,
)
from evals.python.tests.support import (
    timeout_case as _timeout_case,
)
from kernel import (
    Case,
    Completion,
    Content,
    Criterion,
    Experiment,
    Instruction,
    InvalidArgument,
    Outcome,
    Profile,
    Reference,
    Task,
    Verification,
    Verifier,
)
from kernel._operations import fixture as fixture_ops
from kernel._operations import grader as grader_ops


def public_projection_uses_native_types() -> None:
    assert all(isinstance(case, Case) for case in datasets.list_cases())


def native_dataset_paths_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "suite.ml"
    path.write_text("let cases = []")
    operation = cast(Callable[..., datasets.Dataset], datasets.load_dataset)
    with pytest.raises(ValidationError):
        operation(selection=path)


@pytest.mark.parametrize("path", ["../outside.ml", "/outside.ml"])
def generated_paths_are_validated(path: str) -> None:
    declaration = _choice_case(case_id="paths", a=1, b=2)
    invalid = _copy_case(declaration, fixture=fixture_ops.of_files([(path, "bad")]))
    with pytest.raises(InvalidArgument):
        datasets.compile_dataset(cases=(invalid,))


def _grade(case_id: str, *, text: str) -> bool:
    return score_case(
        case_id=case_id,
        response=text,
        changed_files=(),
        verification=Verification.Unchecked(),
        selection="smoke",
    )["correctness"]


def profiles_share_fixture_files() -> None:
    spec = evaluation.resolve_settings()
    assert load_profile("genius", spec=spec).name == spec.profiles[1].name
    case = datasets.list_cases()[0]
    baseline = profiles.files(
        load_profile(name="baseline", spec=evaluation.resolve_settings()),
        case=case,
        instructions=profiles.load_instructions(evaluation.resolve_settings()),
    )
    genius = profiles.files(
        load_profile(name="genius", spec=evaluation.resolve_settings()),
        case=case,
        instructions=profiles.load_instructions(evaluation.resolve_settings()),
    )
    assert {key: genius[key] for key in baseline} == baseline


def only_genius_receives_instructions() -> None:
    case = datasets.list_cases()[0]
    assert (
        any(
            key.startswith("instructions/")
            for key in profiles.files(
                load_profile(name="baseline", spec=evaluation.resolve_settings()),
                case=case,
                instructions=profiles.load_instructions(evaluation.resolve_settings()),
            )
        ),
        any(
            key.startswith("instructions/")
            for key in profiles.files(
                load_profile(name="genius", spec=evaluation.resolve_settings()),
                case=case,
                instructions=profiles.load_instructions(evaluation.resolve_settings()),
            )
        ),
    ) == (False, True)


def profile_prompts() -> None:
    case = datasets.list_cases()[0]
    assert (
        profiles.prompt(
            load_profile(name="baseline", spec=evaluation.resolve_settings()),
            case=case,
            instructions=profiles.load_instructions(evaluation.resolve_settings()),
        )
        == case.prompt,
        "../instructions/skills/reasoning/SKILL.md"
        in profiles.prompt(
            load_profile(name="genius", spec=evaluation.resolve_settings()),
            case=case,
            instructions=profiles.load_instructions(evaluation.resolve_settings()),
        ),
    ) == (True, True)


def samples_keep_task_ids_and_metadata() -> None:
    assert [
        sample.id
        for sample in profiles.samples(
            load_profile(name="genius", spec=evaluation.resolve_settings()),
            cases=datasets.list_cases(),
            instructions=profiles.load_instructions(evaluation.resolve_settings()),
        )
    ] == [case.id for case in datasets.list_cases()]


def hash_tracks_contents_and_ignores_mapping_order() -> None:
    before = content_hash({"a": b"before", "b": b"before"})
    assert content_hash({"b": b"before", "a": b"before"}) == before
    assert content_hash({"a": b"after", "b": b"before"}) != before


@pytest.mark.parametrize(
    "text",
    ['  {"choice":"B","reason":"Cheap"}  ', '```json\n{"choice":"B","reason":"Cheap"}\n```'],
)
def json_fences(text: str) -> None:
    assert _grade("small-decision", text=text)


def cases_200_cases_are_python_values() -> None:
    dataset = datasets.compile_dataset(
        cases=tuple(
            _timeout_case(case_id=f"timeout-{i}", initial=15, requested=30 + i) for i in range(200)
        )
    )
    cases = datasets.list_cases(selection=dataset)
    assert len(cases) == 200
    assert (
        _reference_files(reference(cases[199].id, selection=dataset))["config.py"]
        == "timeout_seconds = 229\n"
    )


def generated_artifacts_stay_out_of_sample_metadata() -> None:
    for sample in profiles.samples(
        load_profile(name="baseline", spec=evaluation.resolve_settings()),
        cases=datasets.list_cases(),
        instructions=profiles.load_instructions(evaluation.resolve_settings()),
    ):
        assert sample.metadata == {
            "case_id": sample.id,
            "profile": "baseline",
            "dataset": "smoke",
        }
        assert not any("heldout" in path for path in sample.files or {})


def duplicate_case_ids_are_rejected() -> None:
    definition = _choice_case(case_id="duplicate", a=10, b=8)
    with pytest.raises(ValueError, match="unique"):
        datasets.compile_dataset(cases=(definition, definition))


def native_projection_preserves_strings() -> None:
    text = 'quote" slash\\ newline\n tab\t return\r zero\x00 é'
    definition = _copy_case(
        _choice_case(case_id="escaped", a=10, b=8),
        instruction=Instruction(skill="reasoning", prompt=text),
    )
    dataset = datasets.compile_dataset(cases=(definition,))
    assert datasets.list_cases(selection=dataset)[0].prompt == text


def cases_are_immutable() -> None:
    case = public_case("clear-task")
    with pytest.raises((AttributeError, TypeError)):
        case.id = "changed"  # type: ignore[misc]
    with pytest.raises(TypeError):
        case.files[0] = ("receipt.py", Content.Inline("changed"))  # type: ignore[index]
    with pytest.raises(TypeError):
        fixture_ops.files(reference(case.id).edits)[0] = ("receipt.py", "changed")  # type: ignore[index]
    checks = verifier(case.id)
    assert checks is not None
    with pytest.raises((AttributeError, TypeError)):
        checks.stdin = "changed"  # type: ignore[misc]
    assert tuple(checks.inputs) == ("receipt.py",)
    assert public_case("clear-task") is case


def compilation_cache_invalidates_when_declarations_change() -> None:
    definition = _choice_case(case_id="cache", a=10, b=8)
    first = datasets.compile_dataset(cases=(definition,))
    with patch(
        "subprocess.run",
        side_effect=AssertionError("Declarations must not compile code"),
    ) as compiler:
        assert datasets.compile_dataset(cases=(definition,)) is first
        assert compiler.call_count == 0
        changed = datasets.compile_dataset(cases=(_choice_case(case_id="cache", a=4, b=8),))
        assert json.loads(_reference_text(reference("cache", selection=changed)))["choice"] == "A"
        assert compiler.call_count == 0


def generic_python_case_exports_without_language_restriction() -> None:
    definition = Task(
        id="python-case",
        fixture=fixture_ops.of_files([("solution.py", "print(42)")]),
        instruction=Instruction(skill="reasoning", prompt="Return 42"),
        criterion=Criterion.Code(
            Verifier(
                inputs=("solution.py",),
                files=[("grader.py", Content.Inline("trusted"))],
                tools=[],
                command=("python3", "grader.py"),
                stdin="private",
                timeout_seconds=5,
            )
        ),
        allowed_files=("solution.py",),
        reference=Reference(edits=fixture_ops.empty, completion=Completion.Plain("done")),
    )
    dataset = datasets.compile_dataset(cases=(definition,))
    case = datasets.list_cases(selection=dataset)[0]
    checks = verifier(case.id, selection=dataset)
    assert checks is not None
    assert (tuple(checks.inputs), tuple(checks.tools), tuple(checks.command)) == (
        ("solution.py",),
        (),
        ("python3", "grader.py"),
    )
    assert _files(checks.files) == {"grader.py": "trusted"}
    assert (checks.stdin, checks.timeout_seconds) == ("private", 5)


def experiment_configuration_reaches_tasks_and_profiles() -> None:
    before = evaluation.resolve_settings()
    spec = Experiment(
        profiles=[
            Profile(
                name=item.name,
                preamble=item.preamble.replace("Apply that", "Follow that"),
                instructions=item.instructions,
            )
            for item in before.profiles
        ],
        epochs=7,
        message_limit=before.message_limit,
        cost_limit=before.cost_limit,
        time_limit=before.time_limit,
        cache=before.cache,
    )
    task = build_task(
        profile=profiles.load_profile("genius", spec=spec),
        spec=spec,
        agent="codex",
        catalog=datasets.load_dataset(selection="smoke"),
        instructions=profiles.load_instructions(spec),
        provenance=datasets.get_provenance(selection=datasets.load_dataset(selection="smoke")),
    )
    assert (
        spec.epochs,
        task.epochs,
        "Follow that" in str(task.dataset[0].input),
        "Follow that" in profiles.load_profile("genius", spec=spec).preamble,
    ) == (7, 7, True, True)
    assert evaluation.resolve_settings().epochs == before.epochs


@pytest.mark.parametrize("grade_only", [False, True])
def record_updates_cannot_bypass_kernel_validation(*, grade_only: bool) -> None:
    definition = _timeout_case(case_id="updated", initial=15, requested=30)
    invalid = _copy_case(definition, fixture=fixture_ops.empty)
    records = (invalid,)
    operation: Callable[[], object]
    if grade_only:
        operation = partial(
            grader_ops.grade,
            records[0],
            response=None,
            outcome=Outcome(changed_files=(), verification=Verification.Unchecked()),
        )
    else:
        operation = partial(datasets.compile_dataset, cases=records)
    with pytest.raises(InvalidArgument, match="criteria read files missing from the fixture"):
        operation()


@pytest.mark.parametrize("delivery", ["manifest", "inline"])
@pytest.mark.parametrize("name", REASONING_DOCUMENTS)
def delivery_preserves_instruction_bytes_and_baseline(delivery: str, *, name: str) -> None:
    mode = cast(evaluation_settings.InstructionDelivery, delivery)
    case = datasets.list_cases()[0]
    root = "/eval/instructions"
    profile = load_profile(name="genius", spec=evaluation.resolve_settings())
    before = profiles.files(
        profile, case=case, instructions=profiles.load_instructions(evaluation.resolve_settings())
    )
    prompt = profiles.prompt(
        profile,
        case=case,
        delivery=mode,
        instruction_root=root,
        instructions=profiles.load_instructions(evaluation.resolve_settings()),
    )
    assert (
        prompt.endswith(case.prompt),
        profiles.files(
            profile,
            case=case,
            instructions=profiles.load_instructions(evaluation.resolve_settings()),
        ),
        profiles.prompt(
            load_profile(name="baseline", spec=evaluation.resolve_settings()),
            case=case,
            delivery=mode,
            instructions=profiles.load_instructions(evaluation.resolve_settings()),
        ),
    ) == (True, before, case.prompt)
    assert f"{root}/{name}" in prompt
    assert ((REPO_ROOT / name).read_text() in prompt) == (delivery == "inline")


def delivery_rejects_unimplemented_skill_instead_of_silently_changing_it() -> None:
    with pytest.raises(ValueError, match="reasoning only"):
        profiles.prompt(
            load_profile(name="genius", spec=evaluation.resolve_settings()),
            case=datasets.list_cases()[1],
            delivery="inline",
            instructions=profiles.load_instructions(evaluation.resolve_settings()),
        )
