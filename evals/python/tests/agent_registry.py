"""Check that new Inspect SWE harnesses use the shared agent settings."""

import asyncio
import importlib
import inspect
from dataclasses import replace
from unittest.mock import Mock, patch

import pytest
from inspect_ai.model import ModelName
from inspect_ai.solver import TaskState
from inspect_swe import claude_code, codex_cli

from evals.python import commands, query
from evals.python.catalog import experiment
from evals.python.integrations.inspect import profiles
from evals.python.integrations.inspect.agents import (
    AGENT_REGISTRY,
    AgentKind,
    AgentSpec,
    coding_agent,
    contained_agent,
    truncated,
)
from evals.python.integrations.inspect.tasks import build_task
from evals.python.tests.scenarios import crashing as _crashing


def _run_crash(kind: AgentKind, *, message: str, monkeypatch: pytest.MonkeyPatch) -> TaskState:
    factory = Mock(return_value=_crashing(message=message))
    monkeypatch.setitem(
        AGENT_REGISTRY, kind, replace(AGENT_REGISTRY[kind], factory=lambda: factory)
    )
    state = TaskState(
        model=ModelName("mockllm/model"), sample_id="case", epoch=1, input="task", messages=[]
    )
    return asyncio.run(contained_agent(kind, version="test")(state, Mock()))


def registered_harness_uses_shared_and_custom_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = Mock(return_value=Mock())
    monkeypatch.setitem(
        AGENT_REGISTRY,
        "other",
        AgentSpec(
            default_version="1.0",
            factory=lambda: factory,
            options={"mode": "strict"},
            failure_prefix="Error executing other agent",
        ),
    )

    assert coding_agent("other", version="1.2") is factory.return_value
    factory.assert_called_once_with(cwd="workspace", version="1.2", attempts=1, mode="strict")


@pytest.mark.parametrize("kind", ["claude", "codex"])
def real_swe_bindings_accept_our_options(kind: AgentKind) -> None:
    assert callable(coding_agent(kind, version="sandbox"))
    assert callable(contained_agent(kind, version="sandbox"))


@pytest.mark.parametrize(
    ("kind", "module"),
    [
        ("claude", "inspect_swe._claude_code.claude_code"),
        ("codex", "inspect_swe._codex_cli.codex_cli"),
    ],
)
def failure_prefix_matches_inspect_swe(kind: AgentKind, *, module: str) -> None:
    source = inspect.getsource(importlib.import_module(module))
    assert f'f"{AGENT_REGISTRY[kind].failure_prefix} {{' in source


@pytest.mark.parametrize("kind", ["claude", "codex"])
def agent_crash_is_recorded_for_scoring(
    kind: AgentKind, *, monkeypatch: pytest.MonkeyPatch
) -> None:
    message = (
        f"{AGENT_REGISTRY[kind].failure_prefix} 1: tool 'apply_patch' was not in request.tools"
    )
    state = _run_crash(kind, message=message, monkeypatch=monkeypatch)
    assert state.metadata["agent_failure"] == message


@pytest.mark.parametrize(
    ("kind", "message"),
    [
        ("claude", "Error executing sandbox command x: denied"),
        ("codex", "Error executing sandbox command x: denied"),
        ("claude", "Error executing codex cli agent 1: other kind"),
        ("codex", "Error executing claude code agent 1: other kind"),
    ],
)
def other_runtime_errors_still_abort(
    kind: AgentKind, *, message: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(RuntimeError, match=message):
        _run_crash(kind, message=message, monkeypatch=monkeypatch)


def long_failure_keeps_exit_code_and_provider_error() -> None:
    message = "Error executing codex cli agent 1: " + "log line\n" * 1000 + "HTTP 400 apply_patch"
    summary = truncated(message)
    assert (summary[:35], summary[-20:], len(summary) < len(message)) == (
        "Error executing codex cli agent 1: ",
        "HTTP 400 apply_patch",
        True,
    )


def claude_options_are_fixed() -> None:
    with patch(
        "evals.python.integrations.inspect.agents.claude_code", wraps=claude_code
    ) as factory:
        coding_agent("claude", version="2.1.278")
    assert factory.call_args.kwargs == {
        "cwd": "workspace",
        "version": "2.1.278",
        "attempts": 1,
        "effort": "medium",
        "disallowed_tools": ["WebSearch", "WebFetch"],
        "retry_refusals": 0,
        "retry_uncaught_errors": 0,
    }


def codex_options_disable_network() -> None:
    with patch("evals.python.integrations.inspect.agents.codex_cli", wraps=codex_cli) as factory:
        coding_agent("codex", version="0.137.0")
    assert factory.call_args.kwargs == {
        "cwd": "workspace",
        "version": "0.137.0",
        "attempts": 1,
        "web_search": "disabled",
        "home_dir": "/root/genius-codex",
        "network_access": False,
        "system_prompt": AGENT_REGISTRY["codex"].system_prompt,
        "retry_refusals": 0,
        "config_overrides": {
            "model_reasoning_effort": '"medium"',
            "allow_login_shell": "false",
        },
    }


def explicit_agent_version_is_logged() -> None:
    task = build_task(
        profile=profiles.load_profile("genius", spec=query.ExperimentSettings()),
        spec=query.ExperimentSettings(),
        agent="codex",
        version="0.137.0",
        catalog=query.LoadDataset(selection="smoke"),
        instructions=profiles.load_instructions(query.ExperimentSettings()),
        provenance=query.Provenance(selection=query.LoadDataset(selection="smoke")),
    )
    spec = experiment()
    assert (task.epochs, task.message_limit, task.cost_limit, task.time_limit) == (
        spec.epochs,
        spec.message_limit,
        spec.cost_limit,
        spec.time_limit,
    )
    metadata = task.metadata
    assert metadata is not None
    assert (metadata["agent"], metadata["agent_version"]) == ("codex", "0.137.0")


def custom_agent_registry_stays_open_through_public_evaluation_and_tasks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        AGENT_REGISTRY, "other", replace(AGENT_REGISTRY["codex"], default_version="custom-version")
    )
    request = commands.EvaluationSettings(model="mockllm/model", agent="other")
    spec = query.ExperimentSettings()
    task = build_task(
        profile=profiles.load_profile("baseline", spec=spec),
        spec=spec,
        agent=request.agent,
        catalog=query.LoadDataset(selection="smoke"),
        instructions=profiles.load_instructions(spec),
        provenance=query.Provenance(selection=query.LoadDataset(selection="smoke")),
    )
    assert task.metadata is not None
    assert (task.metadata["agent"], task.metadata["agent_version"]) == ("other", "custom-version")


def codex_compatibility_guidance_is_conditional_and_common() -> None:
    assert AGENT_REGISTRY["codex"].system_prompt == (
        "Use only tools registered for this session. "
        "If apply_patch is not registered, edit files through exec_command with cmd "
        "as a shell command string, not an argv array. "
        "Do not call an unregistered apply_patch tool."
    )
    assert AGENT_REGISTRY["claude"].system_prompt == ""


def changed_agent_guidance_changes_task_fingerprint(monkeypatch: pytest.MonkeyPatch) -> None:
    from hashlib import sha256  # noqa: PLC0415
    from typing import cast  # noqa: PLC0415

    from evals.python.integrations.inspect.tasks import baseline  # noqa: PLC0415

    original = cast(dict[str, str], baseline(agent="codex").metadata)["agent_system_prompt_sha256"]
    spec = AGENT_REGISTRY["codex"]
    changed_prompt = spec.system_prompt + "\nAdditional shared compatibility guidance."
    monkeypatch.setitem(AGENT_REGISTRY, "codex", replace(spec, system_prompt=changed_prompt))
    changed = cast(dict[str, str], baseline(agent="codex").metadata)["agent_system_prompt_sha256"]
    assert changed == sha256(changed_prompt.encode()).hexdigest()
    assert changed != original
