"""Import benchmark definitions through the typed kernel without exposing private tests."""

import json
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from evals.python import datasets, query
from evals.python.datasets import cases_hash, humanevalplus
from evals.python.integrations import evalplus
from evals.python.integrations.evalplus.benchmarks import (
    benchmark_info,
)
from evals.python.integrations.inspect import profiles
from evals.python.integrations.inspect.profiles import load_profile
from evals.python.integrations.inspect.tasks import baseline
from evals.python.query import GradeCase
from evals.python.tests.declarations import _files, _public_snapshot, _reference_files
from evals.python.tests.projections import public_case, verifier
from evals.python.tests.support import import_dataset as _import_dataset
from evals.python.tests.support import (
    import_records as _import_records,
)
from evals.python.tests.support import (
    imported_reference as _imported_reference,
)
from evals.python.tests.support import (
from kernel import Ast
    imported_verifier as _imported_verifier,
)


def _record(**updates: object) -> str:
    return json.dumps(
        {
            "task_id": "HumanEval/0",
            "prompt": 'def identity(x):\n    """Return x."""\n',
            "entry_point": "identity",
            "canonical_solution": "    return x\n",
            "base_input": [[2**326 + 17]],
            "plus_input": [[2**120 + 3]],
            "atol": 0,
            **updates,
        }
    )


def import_preserves_original_private_json() -> None:
    raw = _record()
    checks = _imported_verifier(raw)
    assert isinstance(checks, Ast.verifier)
    assert json.loads(checks.stdin)["record"] == raw
    assert str(2**326 + 17) in checks.stdin


def imported_case_keeps_grader_private() -> None:
    case = _import_records((_record(),))[0]
    assert case.id == "humaneval-0"
    assert _reference_files(_imported_reference(_record()))["solution.py"].endswith(
        "    return x\n"
    )
    assert _files(case.files) == {"solution.py": json.loads(_record())["prompt"]}
    assert (
        "canonical_solution" in case.prompt,
        "verifier.py" in dict(case.files),
    ) == (False, False)


def imported_profile_public_inputs_match() -> None:
    case = _import_records((_record(),))[0]
    assert {
        name: profiles.files(
            load_profile(name="genius", spec=query.ExperimentSettings()),
            case=case,
            instructions=profiles.load_instructions(query.ExperimentSettings()),
        )[name]
        for name in profiles.files(
            load_profile(name="baseline", spec=query.ExperimentSettings()),
            case=case,
            instructions=profiles.load_instructions(query.ExperimentSettings()),
        )
    } == profiles.files(
        load_profile(name="baseline", spec=query.ExperimentSettings()),
        case=case,
        instructions=profiles.load_instructions(query.ExperimentSettings()),
    )


@pytest.mark.parametrize(
    "records",
    [
        (_record(), _record()),
        (_record(task_id="HumanEval/../outside"),),
        (_record(task_id="HumanEval/-1"),),
        (_record(task_id="HumanEval/00"),),
        (_record(entry_point=""),),
        (_record(prompt=1),),
        ("[]",),
    ],
)
def malformed_import_rejected(records: tuple[str, ...]) -> None:
    with pytest.raises((ValueError, ValidationError)):
        _import_records(records)


def dataset_selector_grades_one_trusted_record() -> None:
    raw = _record()
    case = _import_records((raw,))[0]
    compiled = _import_dataset((raw,))
    with patch("evals.python.datasets.load_dataset", return_value=compiled):
        assert public_case(case.id, selection="humanevalplus") == case
        assert query.Cases(selection="humanevalplus") == (case,)
        assert GradeCase(
            case_id=case.id,
            response="",
            changed_files=("workspace/solution.py",),
            verification=Ast.Passed(),
            selection="humanevalplus",
        ) == {"correctness": True, "scope": True}
        samples = profiles.samples(
            load_profile(name="baseline", spec=query.ExperimentSettings()),
            cases=query.Cases(),
            dataset="humanevalplus",
            instructions=profiles.load_instructions(query.ExperimentSettings()),
        )
    assert samples[0].metadata == {
        "case_id": case.id,
        "profile": "baseline",
        "dataset": "humanevalplus",
    }


def pinned_manifest() -> None:
    info = benchmark_info()
    assert info.count == 164
    assert info.revision == "v0.1.10"
    assert len(info.sha256) == 64
    assert len(info.evaluator_commit) == 40


@pytest.fixture
def synthetic_dataset(monkeypatch: pytest.MonkeyPatch) -> None:
    data = "\n".join(_record(task_id=f"HumanEval/{i}") for i in range(164)).encode()
    monkeypatch.setattr(humanevalplus, "download", lambda request: data)


def dataset_index_keeps_all_cases(synthetic_dataset: None) -> None:
    cases = query.Cases(selection="humanevalplus")
    assert (len(cases), len({case.id for case in cases})) == (164, 164)
    assert all(tuple(dict(case.files)) == ("solution.py",) for case in cases)


def import_cache_tracks_verifier_source(
    *, synthetic_dataset: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    first = query.LoadDataset(selection="humanevalplus")
    before = cast(Ast.verifier, verifier("humaneval-0", selection=first))
    script = tmp_path / "evalplus_verifier.py"
    script.write_text(_files(before.files)["verifier.py"] + "\n")
    monkeypatch.setattr(evalplus, "__file__", str(tmp_path / "__init__.py"))
    second = query.LoadDataset(selection="humanevalplus")
    checks = cast(Ast.verifier, verifier("humaneval-0", selection=second))
    assert _files(checks.files)["verifier.py"] == _files(before.files)["verifier.py"] + "\n"
    assert _public_snapshot(query.Cases(selection=first)) == _public_snapshot(
        query.Cases(selection=second)
    )
    assert cases_hash(first) != cases_hash(second)
    original_checks = verifier("humaneval-0", selection=first)
    assert original_checks is not None
    assert _files(original_checks.files) == _files(before.files)
    assert original_checks.stdin == before.stdin


def dataset_count_mismatch(*, synthetic_dataset: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(humanevalplus, "download", lambda request: _record().encode())
    with pytest.raises(ValueError, match="count"):
        query.Cases(selection="humanevalplus")


def duplicate_ids_across_import_batches() -> None:
    records = (*(_record(task_id=f"HumanEval/{i}") for i in range(16)), _record())
    with pytest.raises(ValueError, match="unique"):
        _import_records(records)


def unrelated_evaluator_does_not_change_smoke_provenance(
    *, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    before = query.Provenance(selection="smoke")
    monkeypatch.setattr(evalplus, "__file__", str(tmp_path / "missing.py"))
    assert query.Provenance(selection="smoke") == before


def case_hash_tracks_private_records_without_changing_public_cases() -> None:
    original = _import_dataset((_record(),))
    changed = _import_dataset((_record(plus_input=[[123]]),))
    with patch.object(datasets, "load_dataset", return_value=original):
        before = query.Provenance(selection="humanevalplus").cases_hash
        public = query.Cases(selection="humanevalplus")
    with patch.object(datasets, "load_dataset", return_value=changed):
        assert _public_snapshot(query.Cases(selection="humanevalplus")) == _public_snapshot(public)
        assert query.Provenance(selection="humanevalplus").cases_hash != before


def imported_dataset_grade_uses_cached_record(synthetic_dataset: None) -> None:
    task = baseline(dataset="humanevalplus")
    assert task.metadata is not None
    assert task.metadata["benchmark"]["count"] == len(task.dataset) == 164
    assert GradeCase(
        case_id="humaneval-0",
        response="",
        changed_files=(),
        verification=Ast.Passed(),
        selection="humanevalplus",
    ) == {"correctness": True, "scope": True}
