"""Import benchmark definitions through the typed kernel without exposing private tests."""

import json
import subprocess
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import pytest

from evals.python import catalog, query
from evals.python._kernel import ExecutableChecks, Verification
from evals.python.catalog import (
    case as catalog_case,
)
from evals.python.catalog import (
    cases_hash,
    load_cases,
)
from evals.python.integrations.evalplus.benchmarks import (
    benchmark_info,
)
from evals.python.integrations.inspect import profiles
from evals.python.integrations.inspect.profiles import load_profile
from evals.python.integrations.inspect.tasks import baseline
from evals.python.query import GradeCase
from evals.python.tests.support import import_records, imported_reference, imported_verifier
from evals.python.transport import Sources


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
    checks = imported_verifier(raw)
    assert isinstance(checks, ExecutableChecks)
    assert json.loads(checks.stdin)["record"] == raw
    assert str(2**326 + 17) in checks.stdin


def test_imported_case_keeps_grader_private() -> None:
    case = import_records((record(),))[0]
    assert case.id == "humaneval-0"
    assert imported_reference(record()).solution["solution.py"].endswith("    return x\n")
    assert dict(case.files) == dict(case.files)
    assert (
        "canonical_solution" in case.prompt,
        "verifier.py" in case.files,
    ) == (False, False)


def test_imported_profile_public_inputs_match() -> None:
    case = import_records((record(),))[0]
    assert {
        name: profiles.files(load_profile(name="genius"), case=case)[name]
        for name in profiles.files(load_profile(name="baseline"), case=case)
    } == profiles.files(load_profile(name="baseline"), case=case)


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
    compiled = catalog.compile_records(sources=catalog.sources("humanevalplus"), records=(raw,))
    with patch("evals.python.catalog._selected", return_value=compiled):
        assert catalog_case(case.id, selection="humanevalplus") == case
        assert load_cases(selection="humanevalplus") == (case,)
        assert GradeCase(
            case_id=case.id,
            response="",
            changed_files=("workspace/solution.py",),
            verification=Verification(status="passed"),
            selection="humanevalplus",
        ) == {"correctness": True, "scope": True}
        samples = profiles.samples(
            load_profile(name="baseline"),
            cases=query.Cases(),
            dataset="humanevalplus",
        )
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
    catalog._catalog.cache_clear()
    monkeypatch.setattr("evals.python.catalog.download", lambda request: data)
    try:
        yield
    finally:
        catalog._catalog.cache_clear()


def test_dataset_index_keeps_all_cases(synthetic_dataset: None) -> None:
    cases = load_cases(selection="humanevalplus")
    assert (len(cases), len({case.id for case in cases})) == (164, 164)
    assert all(tuple(case.files) == ("solution.py",) for case in cases)


def test_import_cache_tracks_verifier_source(
    *, synthetic_dataset: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    load_cases(selection="humanevalplus")
    resources = catalog.sources().resources
    updated = tuple(
        (name, source + "\n" if name == "evalplus_verifier.py" else source)
        for name, source in resources
    )
    original = catalog.sources
    monkeypatch.setattr(
        catalog,
        "sources",
        lambda selection="smoke": Sources(modules=original(selection).modules, resources=updated),
    )
    second = load_cases(selection="humanevalplus")[0]
    checks = catalog.verifier(second.id, selection="humanevalplus")
    assert isinstance(checks, ExecutableChecks)
    assert checks.files["verifier.py"] == (dict(resources)["evalplus_verifier.py"] + "\n")


def test_dataset_count_mismatch(
    *, synthetic_dataset: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("evals.python.catalog.download", lambda request: record().encode())
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


@pytest.mark.parametrize("driver", ["ocaml_verifier.py", "evalplus_verifier.py"])
def test_case_hash_tracks_private_verifier_code(
    *, driver: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = cases_hash("smoke")
    source_before = query.Provenance(selection="smoke").source_hash
    resources = catalog.sources().resources
    updated = tuple(
        (name, source + "\n" if name == driver else source) for name, source in resources
    )
    original = catalog.sources
    monkeypatch.setattr(
        catalog,
        "sources",
        lambda selection="smoke": Sources(modules=original(selection).modules, resources=updated),
    )
    assert cases_hash("smoke") != before
    assert query.Provenance(selection="smoke").source_hash != source_before


def test_case_hash_tracks_private_records_without_changing_public_cases() -> None:
    original = catalog.compile_records(
        sources=catalog.sources("humanevalplus"), records=(record(),)
    )
    changed = catalog.compile_records(
        sources=original.sources, records=(record(plus_input=[[123]]),)
    )
    with patch.object(catalog, "_selected", return_value=original):
        before = query.Provenance(selection="humanevalplus").cases_hash
        public = query.Cases(selection="humanevalplus")
    with patch.object(catalog, "_selected", return_value=changed):
        assert query.Cases(selection="humanevalplus") == public
        assert query.Provenance(selection="humanevalplus").cases_hash != before


def test_imported_dataset_grade_uses_cached_record(synthetic_dataset: None) -> None:
    task = baseline(dataset="humanevalplus")
    assert task.metadata is not None
    assert task.metadata["benchmark"]["count"] == len(task.dataset) == 164
    assert GradeCase(
        case_id="humaneval-0",
        response="",
        changed_files=(),
        verification=Verification(status="passed"),
        selection="humanevalplus",
    ) == {"correctness": True, "scope": True}
