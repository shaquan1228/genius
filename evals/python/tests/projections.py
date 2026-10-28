"""Private native projections for tests that inspect trusted dataset material."""

from kernel import Reference, Verifier

from evals.python import datasets
from evals.python.datasets import Case, Selection

__test__ = False


def verifier(case_id: str, *, selection: Selection = "smoke") -> Verifier | None:
    return datasets.load_dataset(selection=selection).records[case_id].task.checks()


def reference(case_id: str, *, selection: Selection = "smoke") -> Reference:
    return datasets.load_dataset(selection=selection).records[case_id].task.reference


def public_case(case_id: str, *, selection: Selection = "smoke") -> Case:
    return datasets.load_dataset(selection=selection).cases[case_id]
