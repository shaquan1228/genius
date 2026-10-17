"""Private native projections for tests that inspect trusted dataset material."""

from evals.python import datasets
from evals.python.datasets import Selection
from kernel import Case, Reference, Verifier
from kernel._operations import projection as projection_ops

__test__ = False


def verifier(case_id: str, *, selection: Selection = "smoke") -> Verifier | None:
    return projection_ops.verifier(datasets.record(case_id, selection=selection))


def reference(case_id: str, *, selection: Selection = "smoke") -> Reference:
    return projection_ops.reference(datasets.record(case_id, selection=selection))


def public_case(case_id: str, *, selection: Selection = "smoke") -> Case:
    return datasets.load_dataset(selection=selection).cases[case_id]
