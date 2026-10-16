"""Prepared inputs stay consistent through composition, scoring, and native logs."""
# Native boolean variants have a single positional payload.
# ruff: noqa: FBT003

import base64
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest
from inspect_ai import Task
from inspect_ai.log import EvalLog, read_eval_log
from inspect_ai.scorer import CORRECT, INCORRECT
from inspect_ai.scorer._scorer import scorer_create
from inspect_ai.solver import generate

from evals.python import commands, query
from evals.python.integrations.inspect import evaluation, profiles, scoring
from evals.python.integrations.inspect.tasks import build_task
from evals.python.tests.declarations import _copy_case, _declaration
from evals.python.tests.support import offline_run as _offline_run
from evals.python.tests.support import results as _results
from kernel import Ast

PRIVATE_SENTINEL = "PRIVATE_DATASET_SNAPSHOT_7bb284"


def instruction_snapshot_survives_source_changes(
    tmp_path: Path, *, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec = query.ExperimentSettings()
    monkeypatch.setattr(profiles, "REPO_ROOT", tmp_path)
    material = {name: f"{name}: unchanged é\n".encode() for name in profiles.REASONING_DOCUMENTS}
    material["skills/reasoning/image.bin"] = b"\x00\xff\x80"
    for name, contents in material.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents)
    snapshot = profiles.load_instructions(spec)
    (tmp_path / profiles.REASONING_DOCUMENTS[0]).write_text("changed")
    (tmp_path / profiles.REASONING_DOCUMENTS[1]).unlink()
    assert dict(snapshot) == {f"instructions/{name}": data for name, data in material.items()}


def composition_uses_supplied_bytes_without_filesystem_access() -> None:
    spec = query.ExperimentSettings()
    profile = profiles.load_profile("genius", spec=spec)
    snapshot = profiles.load_instructions(spec)
    case = query.Cases()[0]
    expected_hash = profiles.content_hash(snapshot)
    with (
        patch.object(Path, "read_bytes", side_effect=AssertionError("late byte read")),
        patch.object(Path, "read_text", side_effect=AssertionError("late text read")),
        patch.object(Path, "rglob", side_effect=AssertionError("late directory scan")),
    ):
        sample = profiles.samples(profile, cases=(case,), instructions=snapshot, delivery="inline")[
            0
        ]
        mounted = cast(Mapping[str, str], sample.files)
        skill = base64.b64decode(mounted["instructions/skills/reasoning/SKILL.md"].split(",", 1)[1])
        assert (
            skill,
            skill.decode() in str(sample.input),
            profiles.content_hash(snapshot),
        ) == (snapshot["instructions/skills/reasoning/SKILL.md"], True, expected_hash)


@pytest.mark.parametrize("deliveries", [None, ("files", "manifest")])
def evaluation_prepares_once_for_all_tasks(
    deliveries: tuple[commands.InstructionDelivery, ...] | None,
) -> None:
    spec = query.ExperimentSettings(epochs=2)
    original = query.LoadDataset()
    cohort = replace(original, cases={"clear-task": original.cases["clear-task"]})
    request = commands.EvaluationSettings(model="mockllm/model", deliveries=deliveries)
    with (
        patch.object(query, "LoadDataset", return_value=cohort) as load,
        patch.object(profiles, "load_instructions", wraps=profiles.load_instructions) as read,
        patch.object(query, "Provenance", wraps=query.Provenance) as provenance,
    ):
        tasks = evaluation.evaluation_tasks(spec, request=request)
    hashes = {cast(Mapping[str, str], task.metadata)["instructions_sha256"] for task in tasks}
    assert (
        len(tasks),
        load.call_count,
        read.call_count,
        provenance.call_count,
        len(hashes),
    ) == (4 if deliveries else 2, 1, 1, 1, 1)


@pytest.fixture
def private_tasks() -> list[Task]:
    definition = _copy_case(
        _declaration(code=False),
        instruction=Ast.instruction(
            skill="reasoning", prompt='{"choice":"B","safe":true,"reason":"clear"}'
        ),
        reference=Ast.reference(
            edits=query.Fixture.of_files([("main.py", PRIVATE_SENTINEL)]),
            completion=Ast.Plain(PRIVATE_SENTINEL),
        ),
    )
    datasets = [
        query.CompileDataset(
            cases=(
                _copy_case(
                    definition,
                    criterion=Ast.Answer(
                        Ast.answer(
                            expected=[
                                ("choice", Ast.String(choice)),
                                ("safe", Ast.Bool(True)),
                            ],
                            text_rule=Ast.text_rule(field="reason", min_words=1, max_words=5),
                        )
                    ),
                ),
            )
        )
        for choice in ("B", "A")
    ]
    spec = query.ExperimentSettings(epochs=1)
    instructions = profiles.load_instructions(spec)
    tasks = [
        build_task(
            profile=profiles.load_profile("baseline", spec=spec),
            spec=spec,
            catalog=dataset,
            instructions=instructions,
            provenance=query.Provenance(selection=dataset),
            agent="codex",
            task_name=f"private-{index}",
        )
        for index, dataset in enumerate(datasets)
    ]
    for task in tasks:
        task.solver = generate()
    return tasks


def native_logs_keep_private_snapshots_out_and_score_each_dataset(
    private_tasks: list[Task], *, tmp_path: Path
) -> None:
    with patch(
        "evals.python.datasets.kernel_sources", side_effect=AssertionError("late source read")
    ):
        logs = _offline_run(private_tasks, mode=None, directory=tmp_path)
    assert (
        [_results(read_eval_log(str(log.location))) for log in logs],
        [PRIVATE_SENTINEL in Path(str(log.location)).read_text() for log in logs],
    ) == (
        [[("external", CORRECT, CORRECT)], [("external", INCORRECT, CORRECT)]],
        [False, False],
    )


def registered_scorer_remains_reconstructible_after_binding(private_tasks: list[Task]) -> None:
    assert scorer_create("evaluation") is scoring.score_sample


def native_profiles_share_fingerprinted_codex_guidance(
    *, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dataclasses import replace  # noqa: PLC0415
    from hashlib import sha256  # noqa: PLC0415
    from unittest.mock import Mock  # noqa: PLC0415

    from inspect_ai.agent import Agent, AgentState, agent  # noqa: PLC0415
    from inspect_ai.model import ModelOutput  # noqa: PLC0415

    from evals.python.integrations.inspect.agents import AGENT_REGISTRY  # noqa: PLC0415

    seen: list[str] = []

    @agent
    def guided(*, system_prompt: str) -> Agent:
        async def execute(state: AgentState) -> AgentState:
            seen.append(system_prompt)
            state.output = ModelOutput.from_content(
                "mockllm/model", '{"choice":"B","safe":true,"reason":"clear"}'
            )
            return state

        return execute

    guidance = AGENT_REGISTRY["codex"].system_prompt
    factory = Mock(side_effect=lambda **kwargs: guided(system_prompt=kwargs["system_prompt"]))
    monkeypatch.setitem(
        AGENT_REGISTRY, "codex", replace(AGENT_REGISTRY["codex"], factory=lambda: factory)
    )
    spec = query.ExperimentSettings(epochs=1)
    dataset = query.CompileDataset(cases=(_declaration(code=False),))
    instructions = profiles.load_instructions(spec)
    tasks = [
        build_task(
            profile=profile,
            spec=spec,
            agent="codex",
            catalog=dataset,
            instructions=instructions,
            provenance=query.Provenance(selection=dataset),
        )
        for profile in spec.profiles
    ]
    logs = _offline_run(tasks, mode=None, directory=tmp_path)
    digest = sha256(guidance.encode()).hexdigest()
    assert seen == [guidance, guidance]
    assert [call.kwargs["system_prompt"] for call in factory.call_args_list] == seen
    _assert_guidance_logs(logs, digest=digest)


def _assert_guidance_logs(logs: list[EvalLog], *, digest: str) -> None:
    for log in logs:
        native = read_eval_log(str(log.location))
        assert native.eval.metadata is not None
        assert native.eval.metadata["agent_system_prompt_sha256"] == digest
        assert native.status == "success"


def unresolved_public_resource_cannot_reach_agent_files() -> None:
    spec = query.ExperimentSettings()
    case = Ast.case(
        id="unresolved",
        skill="reasoning",
        prompt="Use the supplied context",
        files=[("context.txt", Ast.Resource("private-resource"))],
    )
    with pytest.raises(ValueError, match="Unresolved resource in public case unresolved"):
        profiles.files(profiles.load_profile("baseline", spec=spec), case=case, instructions={})
