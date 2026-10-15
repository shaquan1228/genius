"""Import benchmark definitions through the typed kernel without exposing private tests."""

import json
import subprocess
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import pytest

from evals.python import transport
from evals.python.profiles import BASELINE, GENIUS
from evals.python.tasks import baseline, cases_hash
from evals.python.transport import (
    CaseQuery,
    ExecutableChecks,
    GradeRequest,
    Verification,
    benchmark_info,
    case_by_id,
    grade,
    import_records,
    load_cases,
    workspace_files,
)


def record(**updates: object) -> str:
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


def test_import_preserves_original_private_json() -> None:
    raw = record()
    case = import_records((raw,))[0]
    assert isinstance(case.checks, ExecutableChecks)
    assert json.loads(case.checks.stdin)["record"] == raw
    assert str(2**326 + 17) in case.checks.stdin


def test_imported_case_keeps_grader_private() -> None:
    case = import_records((record(),))[0]
    assert case.id == "humaneval-0"
    assert case.solution["solution.py"].endswith("    return x\n")
    assert dict(workspace_files(case)) == dict(case.files)
    assert (
        "canonical_solution" in case.prompt,
        "verifier.py" in workspace_files(case),
    ) == (False, False)


def test_imported_profile_public_inputs_match() -> None:
    case = import_records((record(),))[0]
    assert {name: GENIUS.files(case)[name] for name in BASELINE.files(case)} == BASELINE.files(case)


@pytest.mark.parametrize(
    "records",
    [
        (record(), record()),
        (record(task_id="HumanEval/../outside"),),
        (record(task_id="HumanEval/-1"),),
        (record(task_id="HumanEval/00"),),
        (record(entry_point=""),),
        (record(prompt=1),),
        ("[]",),
    ],
)
def test_malformed_import_rejected(records: tuple[str, ...]) -> None:
    with pytest.raises(subprocess.CalledProcessError):
        import_records(records)


def test_dataset_selector_grades_one_trusted_record() -> None:
    raw = record()
    case = import_records((raw,))[0]
    catalog = transport.Catalog(cases={case.id: case}, records={case.id: raw})
    with patch("evals.python.transport._selected", return_value=catalog):
        assert case_by_id(query=CaseQuery(case_id=case.id, selection="humanevalplus")) == case
        assert load_cases(selection="humanevalplus") == (case,)
        assert grade(
            request=GradeRequest(
                case_id=case.id,
                selection="humanevalplus",
                response="",
                changed_files=("workspace/solution.py",),
                verification=Verification(status="passed"),
            )
        ) == {"correctness": True, "scope": True}
        samples = BASELINE.samples(dataset="humanevalplus")
    assert samples[0].metadata == {
        "case_id": case.id,
        "profile": "baseline",
        "dataset": "humanevalplus",
    }


def test_pinned_manifest() -> None:
    info = benchmark_info()
    assert info.count == 164
    assert info.revision == "v0.1.10"
    assert len(info.sha256) == 64
    assert len(info.evaluator_commit) == 40


@pytest.fixture
def synthetic_dataset(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    data = "\n".join(record(task_id=f"HumanEval/{i}") for i in range(164)).encode()
    transport._catalog.cache_clear()
    monkeypatch.setattr("evals.python.transport.download", lambda request: data)
    try:
        yield
    finally:
        transport._catalog.cache_clear()


def test_dataset_index_keeps_all_cases(synthetic_dataset: None) -> None:
    cases = load_cases(selection="humanevalplus")
    assert (len(cases), len({case.id for case in cases})) == (164, 164)
    assert all(tuple(case.files) == ("solution.py",) for case in cases)


def test_import_cache_tracks_verifier_source(
    *, synthetic_dataset: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    load_cases(selection="humanevalplus")
    resources = transport._resources()
    updated = tuple(
        (name, source + "\n" if name == "verifier.py" else source) for name, source in resources
    )
    monkeypatch.setattr("evals.python.transport._resources", lambda: updated)
    second = load_cases(selection="humanevalplus")[0]
    assert isinstance(second.checks, ExecutableChecks)
    assert second.checks.files["verifier.py"] == (dict(resources)["verifier.py"] + "\n")


def test_dataset_count_mismatch(
    *, synthetic_dataset: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("evals.python.transport.download", lambda request: record().encode())
    with pytest.raises(ValueError, match="count"):
        load_cases(selection="humanevalplus")


def test_duplicate_ids_across_import_batches() -> None:
    records = (*(record(task_id=f"HumanEval/{i}") for i in range(16)), record())
    with pytest.raises(ValueError, match="unique"):
        import_records(records)


def test_custom_smoke_suite_still_supported(tmp_path: Path) -> None:
    suite = tmp_path / "suite.ml"
    suite.write_text("let cases = []")
    assert load_cases(selection=suite) == ()


def test_case_hash_tracks_private_verifier_code(monkeypatch: pytest.MonkeyPatch) -> None:
    before = cases_hash("smoke")
    resources = transport._resources()
    updated = tuple(
        (name, source + "\n" if name == "verifier.py" else source) for name, source in resources
    )
    monkeypatch.setattr("evals.python.transport._resources", lambda: updated)
    assert cases_hash("smoke") != before


def test_imported_dataset_grade_uses_cached_record(synthetic_dataset: None) -> None:
    task = baseline(dataset="humanevalplus")
    assert task.metadata is not None
    assert task.metadata["benchmark"]["count"] == len(task.dataset) == 164
    assert grade(
        request=GradeRequest(
            case_id="humaneval-0",
            selection="humanevalplus",
            response="",
            changed_files=(),
            verification=Verification(status="passed"),
        )
    ) == {"correctness": True, "scope": True}
