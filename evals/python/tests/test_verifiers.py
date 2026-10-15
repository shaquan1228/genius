"""Compile real OCaml fixtures and reject seeds, partial fixes, and invalid code."""

import asyncio
import subprocess
from collections.abc import Mapping
from pathlib import Path

import pytest
from inspect_ai.util._sandbox.local import LocalSandboxEnvironment

from evals.python.contracts import Case, CaseQuery, ExecutableChecks, Selection
from evals.python.integrations.datasets.catalog import RUNNER, load_cases, reference, verifier
from evals.python.integrations.inspect.verification import Verifier
from evals.python.tests.support import ocaml_timeout_case

CASES = {case.id: case for case in load_cases()}


def snapshot(directory: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in directory.iterdir()}


def verify(case: Case, *, directory: Path, selection: Selection = "smoke") -> bool:
    checks = verifier(query=CaseQuery(case_id=case.id, selection=selection))
    assert isinstance(checks, ExecutableChecks)

    async def execute() -> bool:
        agent = LocalSandboxEnvironment()
        try:
            await agent.exec(["mkdir", "workspace"])
            for name, data in snapshot(directory).items():
                await agent.write_file(f"workspace/{name}", data)
            result, _ = await Verifier(checks=checks, agent=agent).verify()
            return result.status == "passed"
        finally:
            await LocalSandboxEnvironment.sample_cleanup(
                "test", None, {"default": agent}, interrupted=False
            )

    return asyncio.run(execute())


def write_files(directory: Path, *, files: Mapping[str, str]) -> None:
    for name, text in files.items():
        (directory / name).write_text(text)


def seed(case_id: str, *, directory: Path) -> Case:
    case = CASES[case_id]
    write_files(directory, files=case.files)
    (directory / "check.sh").write_text(RUNNER.read_text())
    return case


@pytest.mark.parametrize("case_id", ["clear-task", "known-preflight"])
def test_seeds_fail_and_solutions_pass(*, case_id: str, tmp_path: Path) -> None:
    case = seed(case_id, directory=tmp_path)
    assert not verify(case, directory=tmp_path)
    write_files(tmp_path, files=reference(query=CaseQuery(case_id=case.id)).solution)
    before = snapshot(tmp_path)
    assert verify(case, directory=tmp_path)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("term", ["price", "price *. float_of_int (max quantity 1)"])
def test_receipt_partial_fixes_fail(*, term: str, tmp_path: Path) -> None:
    case = seed("clear-task", directory=tmp_path)
    (tmp_path / "receipt.ml").write_text(
        f"let total items = List.fold_left (fun sum (price, quantity) -> sum +. {term}) 0. items\n"
    )
    assert not verify(case, directory=tmp_path)


@pytest.mark.parametrize(
    ("config", "client", "override", "rejection"),
    [
        (30, 30, "value", True),
        (15, 30, "value", True),
        (30, 15, "value", True),
        (30, 30, "30", True),
        (30, 30, "value", False),
    ],
)
def test_preflight_defaults_overrides_and_validation(
    *,
    config: int,
    client: int,
    override: str,
    rejection: bool,
    tmp_path: Path,
) -> None:
    case = seed("known-preflight", directory=tmp_path)
    (tmp_path / "config.ml").write_text(f"let timeout_seconds = {config}\n")
    source = (
        reference(query=CaseQuery(case_id=case.id))
        .solution["client.ml"]
        .replace("= 30", f"= {client}")
        .replace("      value\n", f"      {override}\n")
    )
    if not rejection:
        source = source.replace(
            '      if value <= 0 then invalid_arg "timeout must be positive";\n', ""
        )
    (tmp_path / "client.ml").write_text(source)
    assert (verify(case, directory=tmp_path)) == (
        config == 30 and client == 30 and override == "value" and rejection
    )


@pytest.mark.parametrize(
    "source",
    ["this is not OCaml", 'let total _ = failwith "broken"', "let () = exit 0\nlet total _ = 0."],
)
def test_compile_and_runtime_errors_fail(*, source: str, tmp_path: Path) -> None:
    case = seed("clear-task", directory=tmp_path)
    (tmp_path / "receipt.ml").write_text(source)
    assert not verify(case, directory=tmp_path)


@pytest.mark.parametrize(
    ("case_id", "modules"),
    [
        ("clear-task", ["receipt.ml", "test_receipt.ml"]),
        ("known-preflight", ["config.ml", "client.ml", "test_client.ml"]),
    ],
)
def test_visible_check_command_leaves_no_build_files(
    *,
    case_id: str,
    modules: list[str],
    tmp_path: Path,
) -> None:
    seed(case_id, directory=tmp_path)
    before = snapshot(tmp_path)
    result = subprocess.run(
        ["sh", "check.sh", *modules],
        check=False,
        cwd=tmp_path,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize(
    ("expression", "filename", "fragment"),
    [
        (
            ocaml_timeout_case(id_expression='"variant"', initial="7", requested="17"),
            "config.ml",
            "let timeout_seconds = 7",
        ),
        (
            ocaml_timeout_case(id_expression='"variant"', initial="30", requested="229"),
            "config.ml",
            "let timeout_seconds = 30",
        ),
        (
            """Case.make ~id:"variant"
  ~fixture:(Fixtures.Receipt.fixture ~bug:Clamp_quantity) ~instruction:Scenarios.Receipt.fix_total
  ~criterion:Scenarios.Receipt.(totals [
    expect ~items:[ item ~price:3.0 ~quantity:0 ] ~total:0.0;
    expect ~items:[ item ~price:3.0 ~quantity:4 ] ~total:12.0;
  ])
  ~allowed_files:["receipt.ml"] ~reference:Scenarios.Receipt.reference""",
            "receipt.ml",
            "max quantity 1",
        ),
    ],
)
def test_family_variants_generate_working_seeds_and_solutions(
    *,
    expression: str,
    filename: str,
    fragment: str,
    tmp_path: Path,
) -> None:
    suite = tmp_path / "suite.ml"
    suite.write_text(f"let cases = [{expression}]\n")
    case = load_cases(selection=suite)[0]
    assert fragment in case.files[filename]
    work = tmp_path / "workspace"
    work.mkdir()
    write_files(work, files=case.files)
    assert not verify(case, directory=work, selection=suite)
    write_files(work, files=reference(query=CaseQuery(case_id=case.id, selection=suite)).solution)
    assert verify(case, directory=work, selection=suite)
