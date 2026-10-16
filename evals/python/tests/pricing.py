"""Check dollar accounting without contacting a model provider."""

import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest
from inspect_ai import Task, eval_async
from inspect_ai.dataset import Sample
from inspect_ai.model import (
    ChatCompletionChoice,
    ChatMessageAssistant,
    ModelCost,
    ModelInfo,
    ModelOutput,
    ModelUsage,
    get_model,
    get_model_info,
)
from inspect_ai.model._model import model_usage_cost
from inspect_ai.solver import generate, use_tools
from inspect_ai.tool import Tool, ToolCall, tool
from pydantic import ValidationError

from evals.python import commands
from evals.python.integrations.inspect import pricing


def _rates() -> commands.ModelPricing:
    return commands.ModelPricing(input=2.0, output=8.0, input_cache_write=3.0, input_cache_read=0.2)


@pytest.mark.parametrize(
    ("info", "context"), [(None, None), (ModelInfo(context_length=32000), 32000)]
)
def explicit_prices_preserve_model_metadata_and_price_every_usage_class(
    info: ModelInfo | None, *, context: int | None
) -> None:
    model = get_model("mockllm/pricing-explicit")
    request = commands.EvaluationSettings(model=str(model), model_cost=_rates())
    with patch.object(pricing, "get_model_info", return_value=info):
        assert pricing.configure(model, request=request) == _rates().model_dump()
    actual = get_model_info(model)
    assert actual is not None
    assert actual.context_length == context
    usage = ModelUsage(
        input_tokens=1000,
        output_tokens=100,
        input_tokens_cache_write=500,
        input_tokens_cache_read=2000,
        total_tokens=3600,
    )
    assert model_usage_cost(model, usage=usage) == pytest.approx(0.0047)


def builtin_prices_are_validated_and_registered() -> None:
    model = get_model("mockllm/pricing-builtin")
    cost = ModelCost(**_rates().model_dump())
    with patch.object(pricing, "get_model_info", return_value=ModelInfo(cost=cost)):
        assert (
            pricing.configure(model, request=commands.EvaluationSettings(model=str(model)))
            == _rates().model_dump()
        )
    actual = get_model_info(model)
    assert actual is not None
    assert actual.cost == cost


@pytest.mark.parametrize(
    ("name", "info"),
    [
        ("unknown/model", None),
        ("unknown/model", ModelInfo()),
        (
            "hf-inference-providers/vendor/model:route",
            ModelInfo(cost=ModelCost(**_rates().model_dump())),
        ),
        ("genius-hf/vendor/model:route", ModelInfo(cost=ModelCost(**_rates().model_dump()))),
    ],
)
def missing_or_routed_prices_fail_before_registration(name: str, *, info: ModelInfo | None) -> None:
    model = get_model("mockllm/pricing-missing")
    with (
        patch.object(pricing, "get_model_info", return_value=info),
        patch.object(pricing, "set_model_info") as register,
        pytest.raises(ValueError, match="EVAL_MODEL_COST"),
    ):
        pricing.configure(model, request=commands.EvaluationSettings(model=name))
    register.assert_not_called()


@pytest.mark.parametrize("invalid", [-1.0, float("inf"), float("nan")])
def invalid_builtin_prices_fail_validation(invalid: float) -> None:
    model = get_model("mockllm/pricing-invalid")
    cost = ModelCost(**(_rates().model_dump() | {"input": invalid}))
    with (
        patch.object(pricing, "get_model_info", return_value=ModelInfo(cost=cost)),
        pytest.raises(ValidationError),
    ):
        pricing.configure(model, request=commands.EvaluationSettings(model=str(model)))


def explicit_routed_prices_override_vendor_defaults() -> None:
    model = get_model("mockllm/pricing-routed")
    request = commands.EvaluationSettings(
        model="hf-inference-providers/vendor/model:route", model_cost=_rates()
    )
    with patch.object(pricing, "get_model_info", return_value=ModelInfo()):
        assert pricing.configure(model, request=request) == _rates().model_dump()


@pytest.mark.parametrize("limit", [0.004, 0.01])
def native_cost_limit_records_usage_and_blocks_next_tool(limit: float, *, tmp_path: Path) -> None:
    dispatched: list[str] = []

    @tool
    def next_action() -> Tool:
        async def execute() -> str:
            """Perform the next action."""
            dispatched.append("executed")
            return "done"

        return execute

    output = ModelOutput(
        model="mockllm/pricing-limit",
        choices=[
            ChatCompletionChoice(
                message=ChatMessageAssistant(
                    content="",
                    tool_calls=[ToolCall(id="action", function="next_action", arguments={})],
                ),
                stop_reason="tool_calls",
            )
        ],
        usage=ModelUsage(
            input_tokens=1000,
            output_tokens=100,
            input_tokens_cache_write=500,
            input_tokens_cache_read=2000,
            total_tokens=3600,
        ),
    )
    done = ModelOutput.from_content(model="mockllm/pricing-limit", content="done")
    done.usage = ModelUsage()
    model = get_model("mockllm/pricing-limit", custom_outputs=[output, done])
    pricing.configure(
        model, request=commands.EvaluationSettings(model=str(model), model_cost=_rates())
    )
    task = Task(
        name="dollar-limit",
        dataset=[Sample(input="act")],
        solver=[use_tools(next_action()), generate()],
        cost_limit=limit,
    )

    async def run() -> None:
        logs = await eval_async(task, model=model, log_dir=str(tmp_path), ctl_server=False)
        assert logs[0].status == "success"
        samples = logs[0].samples
        assert samples is not None
        assert len(samples) == 1
        sample = samples[0]
        if limit < 0.0047:
            assert sample.limit is not None
            assert sample.limit.type == "cost"
        else:
            assert sample.limit is None
        assert sample.error is None
        usage = sample.model_usage[str(model)]
        assert usage.total_cost == pytest.approx(0.0047)
        assert usage.input_tokens_cache_read == 2000
        assert usage.input_tokens_cache_write == 500

    asyncio.run(run())
    assert dispatched == ([] if limit < 0.0047 else ["executed"])
