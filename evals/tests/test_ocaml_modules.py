"""Verify OCaml module boundaries through independent compilation."""

import subprocess
from pathlib import Path

from evals.cases import EVALS_ROOT


def run_modules(directory: Path, modules: list[str], probe: str) -> str:
    for name in modules:
        (directory / name).write_text((EVALS_ROOT / name).read_text())
    (directory / "probe.ml").write_text(probe)
    return subprocess.run(
        ["sh", str(EVALS_ROOT / "check.sh"), *modules, "probe.ml"],
        cwd=directory,
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    ).stdout


def test_fixture_is_independent_and_overlay_is_explicit(tmp_path: Path) -> None:
    assert (
        run_modules(
            tmp_path,
            ["fixture.mli", "fixture.ml"],
            """
let () =
  let base = Fixture.of_files ["config.ml", "initial"] in
  let override = Fixture.of_files ["config.ml", "changed"] in
  assert (Fixture.files base = ["config.ml", "initial"]);
  assert (Fixture.files (Fixture.overlay base override) = ["config.ml", "changed"]);
  assert (try ignore (Fixture.of_files ["a", "one"; "a", "two"]); false
          with Invalid_argument _ -> true)
""",
        )
        == ""
    )


def test_starting_projects_compile_without_eval_or_check_modules(tmp_path: Path) -> None:
    assert (
        run_modules(
            tmp_path,
            ["fixture.mli", "fixture.ml", "fixtures.ml"],
            """
let () =
  let project = Fixtures.Receipt.fixture ~bug:Ignore_quantity in
  assert (List.mem_assoc "receipt.ml" (Fixture.files project));
  assert (List.length (Fixture.files project) = 2)
""",
        )
        == ""
    )


def test_checks_compile_without_fixture_modules(tmp_path: Path) -> None:
    assert (
        run_modules(
            tmp_path,
            ["check.ml"],
            """
let checks = Check.Receipt.(totals [ expect ~items:[ item ~price:3.0 ~quantity:4 ] ~total:12.0 ])
let () = match checks with
  | Check.Code { sources; program } ->
      assert (sources = ["receipt.ml"]);
      assert (String.length program > 0)
  | Check.Answer _ -> assert false
""",
        )
        == ""
    )


def test_suite_is_pure_and_eval_policy_does_not_change_fixture(tmp_path: Path) -> None:
    from evals.cases import OCAML_SOURCES

    assert (
        run_modules(
            tmp_path,
            list(OCAML_SOURCES[:-1]),
            """
let () =
  let original = List.hd Suite.cases in
  let changed = { original with
    Eval.task = Task.make ~skill:"reasoning" ~prompt:"A different instruction";
    checks = Check.Receipt.(totals [ expect ~items:[] ~total:99.0 ]);
    allowed_files = [];
  } in
  assert (List.length Suite.cases = 4);
  assert (Fixture.files changed.fixture = Fixture.files original.fixture);
  assert (changed.allowed_files = []);
  assert (original.allowed_files = ["receipt.ml"])
""",
        )
        == ""
    )
