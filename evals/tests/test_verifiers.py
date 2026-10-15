"""Compile real OCaml fixtures and reject seeds, partial fixes, and invalid code."""

import subprocess
from pathlib import Path

import pytest

from evals.cases import EVALS_ROOT, Case, load_cases
from evals.scoring import heldout_check
from evals.tests.support import ocaml_timeout_case

CASES = {case.id: case for case in load_cases()}
RUNNER = EVALS_ROOT / "check.sh"


def snapshot(directory: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in directory.iterdir()}


def verify(case: Case, directory: Path) -> bool:
    command, script, marker = heldout_check(case)
    result = subprocess.run(
        command,
        input=script,
        cwd=directory,
        text=True,
        capture_output=True,
        timeout=30,
    )
    return result.returncode == 0 and marker in result.stdout.splitlines()


def write_files(directory: Path, files: dict[str, str]) -> None:
    for name, text in files.items():
        (directory / name).write_text(text)


def seed(case_id: str, directory: Path) -> Case:
    case = CASES[case_id]
    write_files(directory, case.files)
    (directory / "check.sh").write_text(RUNNER.read_text())
    return case


@pytest.mark.parametrize("case_id", ["clear-task", "known-preflight"])
def test_seeds_fail_and_solutions_pass(case_id: str, tmp_path: Path) -> None:
    case = seed(case_id, tmp_path)
    assert not verify(case, tmp_path)
    for name in case.allowed_files:
        (tmp_path / name).write_text(case.solution[name])
    before = snapshot(tmp_path)
    assert verify(case, tmp_path)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("term", ["price", "price *. float_of_int (max quantity 1)"])
def test_receipt_partial_fixes_fail(term: str, tmp_path: Path) -> None:
    case = seed("clear-task", tmp_path)
    (tmp_path / "receipt.ml").write_text(
        f"let total items = List.fold_left (fun sum (price, quantity) -> sum +. {term}) 0. items\n"
    )
    assert not verify(case, tmp_path)


@pytest.mark.parametrize(
    "config,client,override,rejection",
    [
        (30, 30, "value", True),
        (15, 30, "value", True),
        (30, 15, "value", True),
        (30, 30, "30", True),
        (30, 30, "value", False),
    ],
)
def test_preflight_defaults_overrides_and_validation(
    config: int,
    client: int,
    override: str,
    rejection: bool,
    tmp_path: Path,
) -> None:
    case = seed("known-preflight", tmp_path)
    (tmp_path / "config.ml").write_text(f"let timeout_seconds = {config}\n")
    source = (
        case.solution["client.ml"]
        .replace("= 30", f"= {client}")
        .replace("      value\n", f"      {override}\n")
    )
    if not rejection:
        source = source.replace(
            '      if value <= 0 then invalid_arg "timeout must be positive";\n', ""
        )
    (tmp_path / "client.ml").write_text(source)
    assert (verify(case, tmp_path)) == (
        config == 30 and client == 30 and override == "value" and rejection
    )


@pytest.mark.parametrize(
    "source",
    ["this is not OCaml", 'let total _ = failwith "broken"', "let () = exit 0\nlet total _ = 0."],
)
def test_compile_and_runtime_errors_fail(source: str, tmp_path: Path) -> None:
    case = seed("clear-task", tmp_path)
    (tmp_path / "receipt.ml").write_text(source)
    assert not verify(case, tmp_path)


@pytest.mark.parametrize(
    "case_id,modules",
    [
        ("clear-task", ["receipt.ml", "test_receipt.ml"]),
        ("known-preflight", ["config.ml", "client.ml", "test_client.ml"]),
    ],
)
def test_visible_check_command_leaves_no_build_files(
    case_id: str,
    modules: list[str],
    tmp_path: Path,
) -> None:
    seed(case_id, tmp_path)
    before = snapshot(tmp_path)
    result = subprocess.run(
        ["sh", "check.sh", *modules],
        cwd=tmp_path,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize(
    "expression,filename,fragment",
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
            """Eval.case ~id:"variant"
  ~fixture:(Fixtures.Receipt.fixture ~bug:Clamp_quantity) ~task:Task.Receipt.fix_total
  ~checks:(Check.Receipt.total [ ([(3., 0)], 0.); ([(3., 4)], 12.) ])
  ~allowed_files:["receipt.ml"] ~reference:Reference.receipt""",
            "receipt.ml",
            "max quantity 1",
        ),
    ],
)
def test_family_variants_generate_working_seeds_and_solutions(
    expression: str,
    filename: str,
    fragment: str,
    tmp_path: Path,
) -> None:
    suite = tmp_path / "suite.ml"
    suite.write_text(f"let cases = [{expression}]\n")
    case = load_cases(suite)[0]
    assert fragment in case.files[filename]
    work = tmp_path / "workspace"
    work.mkdir()
    write_files(work, case.files)
    assert not verify(case, work)
    write_files(work, case.solution)
    assert verify(case, work)
