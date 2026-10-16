"""Resolve exact provider prices before starting any evaluation samples."""

from inspect_ai.model import Model, ModelCost, ModelInfo, get_model_info, set_model_info

from evals.python import commands


def configure(model: Model, *, request: commands.EvaluationSettings) -> dict[str, float]:
    info = get_model_info(model)
    prices = request.model_cost
    if prices is None:
        prices = known_prices(info, request=request)
    rates = prices.model_dump()
    cost = ModelCost(**rates)
    updated = info.model_copy(update={"cost": cost}) if info else ModelInfo(cost=cost)
    set_model_info(str(model), updated)
    return rates


def known_prices(
    info: ModelInfo | None, *, request: commands.EvaluationSettings
) -> commands.ModelPricing:
    routed = request.model.startswith(("hf-inference-providers/", "genius-hf/"))
    if routed or info is None or info.cost is None:
        raise ValueError(
            "Set EVAL_MODEL_COST with exact provider USD prices per million tokens "
            "for input, output, input_cache_write, and input_cache_read"
        )
    return commands.ModelPricing.model_validate(info.cost.model_dump())
