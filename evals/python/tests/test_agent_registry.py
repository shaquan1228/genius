"""Check that new Inspect SWE harnesses use the shared agent settings."""

from unittest.mock import Mock, patch

import pytest
from inspect_swe import claude_code, codex_cli

from evals.python.agents import AGENT_REGISTRY, AgentKind, AgentSpec, coding_agent
from evals.python.tasks import TaskRequest, build_task
from evals.python.transport import experiment


def test_registered_harness_uses_shared_and_custom_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = Mock(return_value=Mock())
    monkeypatch.setitem(
        AGENT_REGISTRY,
        "other",
        AgentSpec(default_version="1.0", factory=lambda: factory, options={"mode": "strict"}),
    )

    assert coding_agent("other", version="1.2") is factory.return_value
    factory.assert_called_once_with(cwd="workspace", version="1.2", attempts=1, mode="strict")


@pytest.mark.parametrize("kind", ["claude", "codex"])
def test_real_swe_bindings_accept_our_options(kind: AgentKind) -> None:
    assert callable(coding_agent(kind, version="sandbox"))


def test_claude_options_are_fixed() -> None:
    with patch("evals.python.agents.claude_code", wraps=claude_code) as factory:
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


def test_codex_options_disable_network() -> None:
    with patch("evals.python.agents.codex_cli", wraps=codex_cli) as factory:
        coding_agent("codex", version="0.137.0")
    assert factory.call_args.kwargs == {
        "cwd": "workspace",
        "version": "0.137.0",
        "attempts": 1,
        "web_search": "disabled",
        "home_dir": "/root/genius-codex",
        "network_access": False,
        "retry_refusals": 0,
        "config_overrides": {
            "model_reasoning_effort": '"medium"',
            "allow_login_shell": "false",
        },
    }


def test_explicit_agent_version_is_logged() -> None:
    task = build_task(request=TaskRequest(profile="genius", agent="codex", version="0.137.0"))
    spec = experiment()
    assert (task.epochs, task.message_limit, task.token_limit, task.time_limit) == (
        spec.epochs,
        spec.message_limit,
        spec.token_limit,
        spec.time_limit,
    )
    metadata = task.metadata
    assert metadata is not None
    assert (metadata["agent"], metadata["agent_version"]) == ("codex", "0.137.0")
