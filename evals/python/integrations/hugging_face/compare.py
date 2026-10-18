"""Compare named variants using evidence acquired through Hugging Face."""

import argparse
import os
from pathlib import Path
from uuid import uuid4

from evals.python import comparison
from evals.python.comparison import ComparisonRequest, VariantRequest
from evals.python.evaluation import VariantSettings
from evals.python.integrations.hugging_face import dispatch
from evals.python.integrations.hugging_face.job import configuration


def request_from_environment() -> ComparisonRequest:
    if os.environ.get("COMPARISON_REQUEST"):
        return ComparisonRequest.model_validate_json(os.environ["COMPARISON_REQUEST"])
    variants = tuple(
        VariantRequest(
            variant=VariantSettings(
                name=role, source_ref=os.environ.get(f"{role.upper()}_REF", "HEAD")
            ),
            result_ref=os.environ.get(f"{role.upper()}_RESULT_REF") or None,
        )
        for role in ("control", "treatment")
    )
    return ComparisonRequest(
        comparison_id=os.environ.get("COMPARISON_ID", f"comparison-{uuid4().hex}"),
        shared=configuration(os.environ),
        variants=variants,
        baseline="control",
    )


def execute(
    request: ComparisonRequest, *, output: Path, namespace: str, timeout: str = "4h"
) -> None:
    with dispatch.acquire_runs(request, output=output, namespace=namespace, timeout=timeout) as (
        resolved,
        runs,
    ):
        report = comparison.compare_runs(
            runs, baseline=resolved.baseline, measurement=resolved.measurement
        )
        dispatch.save(output / "comparison.json", value=report.model_dump(mode="json"))
        (output / "summary.md").write_text(comparison.render_report(report))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", nargs="?", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--namespace", default=os.environ.get("HF_NAMESPACE"))
    parser.add_argument("--timeout", default=os.environ.get("EVAL_JOB_TIMEOUT", "4h"))
    args = parser.parse_args()
    if not args.namespace:
        parser.error("--namespace or HF_NAMESPACE is required")
    request = (
        ComparisonRequest.model_validate_json(args.request.read_text())
        if args.request
        else request_from_environment()
    )
    execute(request, output=args.output, namespace=args.namespace, timeout=args.timeout)


if __name__ == "__main__":
    main()
