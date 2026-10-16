"""Private native projections for tests that inspect trusted dataset material."""

from evals.python import datasets, queries
from kernel import Ast, Projection

__test__ = False


def verifier(case_id: str, *, selection: queries.Selection = "smoke") -> Ast.verifier | None:
    return Projection.verifier(datasets.record(case_id, selection=selection))


def reference(case_id: str, *, selection: queries.Selection = "smoke") -> Ast.reference:
    return Projection.reference(datasets.record(case_id, selection=selection))


def public_case(case_id: str, *, selection: queries.Selection = "smoke") -> Ast.case:
    return datasets.load_dataset(selection).cases[case_id]
