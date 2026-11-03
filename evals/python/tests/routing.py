"""Grade routing choices from recorded tool calls, and install skills where agents find them."""

import asyncio
import posixpath
import re
from typing import Any

import pytest
from inspect_ai import Task
from inspect_ai._util.registry import registry_info
from inspect_ai.log import EvalSample
from inspect_ai.model import ChatMessageAssistant, ModelName
from inspect_ai.scorer import Score, Target
from inspect_ai.scorer._scorer import scorer_metrics
from inspect_ai.solver import TaskState
from inspect_ai.tool import ToolCall
from pydantic import JsonValue, ValidationError

from evals.python import GENIUS, ROUTING, Declaration, Experiment, datasets, routing
from evals.python.integrations.inspect import profiles, results, scoring
from evals.python.integrations.inspect.agents import AGENT_REGISTRY
from evals.python.integrations.inspect.tasks import build_task

LINK = re.compile(r"`((?:\.\./)+[^`\s]+)`")


def _call(name: str, **arguments: JsonValue) -> routing.Call:
    return {"name": name, "arguments": arguments}


def _declaration(case_id: str) -> Declaration:
    return datasets.load_dataset(selection="smoke").records[case_id]


@pytest.mark.parametrize(
    ("call", "skill"),
    [
        (_call("Skill", skill="bayesian"), "bayesian"),
        (_call("Skill", skill="genius:preflight", args="task"), "preflight"),
        (_call("Read", file_path="/w/workspace/.claude/skills/tcrei/SKILL.md"), "tcrei"),
        (_call("exec_command", cmd="sed -n 1,80p /root/x/skills/reasoning/SKILL.md"), "reasoning"),
        (_call("shell", command=["cat", "skills/preflight/SKILL.md"]), "preflight"),
        (_call("Read", file_path="../instructions/skills/bayesian/SKILL.md"), "bayesian"),
    ],
)
def skill_is_read_from_tool_or_skill_file(call: routing.Call, *, skill: str) -> None:
    assert routing.invoked_skill(call) == skill


@pytest.mark.parametrize(
    "call",
    [
        _call("Read", file_path="skills/bayesian/references/bounds.md"),
        _call("Read", file_path="docs/identity.md"),
        _call("exec_command", cmd="ls .claude/skills"),
        _call("exec_command", cmd="cat myskills/reasoning/SKILL.md"),
        _call("Skill", skill=3),
        {"name": "Bash"},
    ],
)
def other_calls_load_no_skill(call: routing.Call) -> None:
    assert routing.invoked_skill(call) is None


def first_loaded_skill_is_the_choice() -> None:
    trace = [
        _call("Bash", command="ls"),
        _call("Skill", skill="preflight"),
        _call("Skill", skill="reasoning"),
    ]
    assert routing.first_skill(trace) == "preflight"
    assert routing.first_skill(trace[:1]) is None


def declared_skill_is_the_default_accepted_route() -> None:
    (route,) = routing.assess(
        [_call("Skill", skill="bayesian")], declaration=_declaration("small-decision")
    )
    assert (route.kind, route.observed, route.accepted, route.passed) == (
        "skill",
        "bayesian",
        ("bayesian",),
        True,
    )
    (missed,) = routing.assess([], declaration=_declaration("small-decision"))
    assert missed.details() == {"observed": None, "accepted": ["bayesian"], "passed": False}


def declared_overrides_accept_choosing_nothing() -> None:
    declaration = _declaration("clear-task")
    assert declaration.routes == {"skill": ("reasoning", None)}
    for trace in ([], [_call("Skill", skill="reasoning")]):
        assert all(route.passed for route in routing.assess(trace, declaration=declaration))
    (wrong,) = routing.assess([_call("Skill", skill="preflight")], declaration=declaration)
    assert not wrong.passed


@pytest.mark.parametrize("routes", [{"skill": ()}, {"skill": ("Not-A-Skill",)}])
def route_overrides_are_validated(routes: dict[str, Any]) -> None:
    task = _declaration("small-decision").task
    with pytest.raises(ValidationError):
        Declaration(skill="bayesian", task=task, routes=routes)


def _installed(agent: str) -> dict[str, bytes]:
    documents = profiles.load_documents(Experiment(profiles=(ROUTING,)))
    root = AGENT_REGISTRY[agent].skills_root
    return profiles.installed_files(ROUTING, documents=documents, skills_root=root)


def _links(installed: dict[str, bytes]) -> list[tuple[str, str]]:
    """Every relative link in an installed document, resolved from its containing file."""
    return [
        (path, posixpath.normpath(posixpath.join(posixpath.dirname(path), link)))
        for path, contents in installed.items()
        if path.endswith(".md")
        for link in LINK.findall(contents.decode())
    ]


@pytest.mark.parametrize("agent", sorted(AGENT_REGISTRY))
def discoverable_skills_install_under_the_agent_root(agent: str) -> None:
    root = AGENT_REGISTRY[agent].skills_root
    assert {path for path in _installed(agent) if path.endswith("/SKILL.md")} == {
        f"{root}/skills/{name}/SKILL.md" for name in ("bayesian", "preflight", "reasoning", "tcrei")
    }


@pytest.mark.parametrize("agent", sorted(AGENT_REGISTRY))
def discoverable_skill_links_resolve_to_installed_files(agent: str) -> None:
    installed = _installed(agent)
    folders = {posixpath.dirname(path) for path in installed}
    links = _links(installed)
    assert links
    assert [
        (path, target) for path, target in links if not {target} & (installed.keys() | folders)
    ] == []


def instruction_placement_is_unchanged() -> None:
    documents = profiles.load_documents(Experiment(profiles=(GENIUS,)))
    installed = profiles.installed_files(GENIUS, documents=documents, skills_root="ignored")
    assert installed == profiles.document_files(GENIUS, documents=documents)


def routing_prompt_names_no_skill() -> None:
    case = _declaration("known-preflight").project()
    documents = profiles.load_documents(Experiment(profiles=(ROUTING,)))
    assert profiles.prompt(ROUTING, case=case, documents=documents) == case.prompt
    with pytest.raises(ValueError, match="only as files"):
        profiles.prompt(ROUTING, case=case, documents=documents, delivery="manifest")


def routes_become_trial_metrics() -> None:
    routes = {"skill": {"observed": None, "accepted": ["bayesian"], "passed": False}}
    sample = EvalSample(
        id="small-decision",
        epoch=1,
        input="",
        target="",
        total_time=1.0,
        scores={
            "evaluation": Score(value={"correctness": "C", "scope": "C"}, metadata={}),
            "routes": Score(value={"skill": "I"}, metadata={"routes": routes}),
        },
    )
    assert results.trial(sample)["route.skill"] == 0.0
    del sample.scores["routes"]  # type: ignore[union-attr]
    assert "route.skill" not in results.trial(sample)


def _state(case_id: str, *calls: tuple[str, dict[str, JsonValue]]) -> TaskState:
    message = ChatMessageAssistant(
        content="",
        tool_calls=[
            ToolCall(id=str(index), function=name, arguments=arguments)
            for index, (name, arguments) in enumerate(calls)
        ],
    )
    return TaskState(
        model=ModelName("mockllm/model"),
        sample_id=case_id,
        epoch=1,
        input="",
        messages=[message],
        metadata={"case_id": case_id, "dataset": "smoke"},
    )


@pytest.mark.parametrize(
    ("calls", "value"),
    [
        ((("Bash", {"command": "ls"}), ("Skill", {"skill": "bayesian"})), "C"),
        ((("Skill", {"skill": "preflight"}),), "I"),
        ((), "I"),
    ],
)
def route_scorer_grades_the_recorded_trace(
    calls: tuple[tuple[str, dict[str, JsonValue]], ...], *, value: str
) -> None:
    score = asyncio.run(scoring.score_routes(_state("small-decision", *calls), Target("")))
    assert score.value == {"skill": value}
    assert score.metadata is not None
    assert score.metadata["routes"]["skill"]["accepted"] == ["bayesian"]
    assert scorer_metrics(scoring.routes()).keys() == {"skill"}  # type: ignore[union-attr]


def _routing_task() -> Task:
    spec = Experiment(profiles=(ROUTING,))
    return build_task(
        profile=ROUTING,
        spec=spec,
        agent="claude",
        catalog=datasets.load_dataset(selection="smoke"),
        documents=profiles.load_documents(spec),
    )


def routing_task_records_its_placement() -> None:
    assert (_routing_task().metadata or {})["instruction_placement"] == "discoverable"


def routing_task_installs_only_discoverable_skills() -> None:
    files = set(_routing_task().dataset[0].files or {})
    assert {name.split("/")[0] for name in files} == {"workspace"}
    assert "workspace/.claude/skills/bayesian/SKILL.md" in files


def routing_task_scores_correctness_and_routes() -> None:
    names = [registry_info(scorer).name for scorer in _routing_task().scorer or []]
    assert names == ["evaluation", "routes"]
