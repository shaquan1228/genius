"""Private native projections for tests that inspect trusted dataset material."""

from evals.python import datasets
from evals.python.datasets import Selection
from kernel import Case, Reference, Task, Verifier

__test__ = False


def verifier(case_id: str, *, selection: Selection = "smoke") -> Verifier | None:
    return Task.checks(task=datasets.load_dataset(selection=selection).records[case_id])


def reference(case_id: str, *, selection: Selection = "smoke") -> Reference:
    return (datasets.load_dataset(selection=selection).records[case_id]).reference


def public_case(case_id: str, *, selection: Selection = "smoke") -> Case:
    return datasets.load_dataset(selection=selection).cases[case_id]
